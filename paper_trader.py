"""Local paper broker. No API keys, broker account, or real orders required."""
from datetime import datetime

class PaperTrader:
    def __init__(self, starting_cash=10000):
        self.cash=float(starting_cash); self.positions={}; self.trades_log=[]

    def execute_trade(self,ticker,quantity,side='buy',strategy_name='Unknown',price=None):
        if side not in ('buy','sell') or quantity<=0 or price is None: return None
        cost=float(price)*float(quantity)
        if side=='buy':
            if cost>self.cash: return None
            self.cash-=cost; p=self.positions.setdefault(ticker,{'qty':0,'avg_price':0.0})
            total=p['qty']+quantity; p['avg_price']=((p['qty']*p['avg_price'])+cost)/total; p['qty']=total
        else:
            p=self.positions.get(ticker)
            if not p or p['qty']<quantity: return None
            self.cash+=cost; p['qty']-=quantity
            if p['qty']==0: del self.positions[ticker]
        rec={'timestamp':datetime.now().isoformat(),'ticker':ticker,'quantity':quantity,'side':side,'price':float(price),'strategy':strategy_name}
        self.trades_log.append(rec); return rec

    def get_account_value(self,prices=None):
        prices=prices or {}; market=sum(p['qty']*float(prices.get(s,p['avg_price'])) for s,p in self.positions.items())
        return {'portfolio_value':self.cash+market,'cash':self.cash,'buying_power':self.cash}

    def get_positions(self,prices=None):
        prices=prices or {}; return {s:{'qty':p['qty'],'entry_price':p['avg_price'],'current_price':float(prices.get(s,p['avg_price'])),'pnl':p['qty']*(float(prices.get(s,p['avg_price']))-p['avg_price'])} for s,p in self.positions.items()}
