import json
from pathlib import Path
import pandas as pd
import yfinance as yf
from .features import features,score
ROOT=Path(__file__).resolve().parents[1]; CFG=json.loads((ROOT/"config/config.json").read_text())
class Portfolio:
    def __init__(self): self.cash=float(CFG["initial_cash"]); self.start=self.cash; self.peak=self.cash; self.positions={}; self.trades=[]; self.curve=[]; self.day_start=self.cash; self.week_start=self.cash; self.current_day=None; self.current_week=None; self.halted=False
    def equity(self,prices): return self.cash+sum(p["qty"]*prices.get(s,p["entry"]) for s,p in self.positions.items())
    def mark(self,price,symbol,date):
        day=pd.Timestamp(date).date(); week=pd.Timestamp(date).to_period("W").start_time.date()
        if self.current_day!=day:self.current_day,self.day_start=day,self.equity({symbol:price})
        if self.current_week!=week:self.current_week,self.week_start=week,self.equity({symbol:price})
        value=self.equity({symbol:price}); self.peak=max(self.peak,value); dd=value/self.peak-1; self.curve.append({"date":str(date),"equity":value,"drawdown":dd}); daily=value/self.day_start-1 if self.day_start else 0; weekly=value/self.week_start-1 if self.week_start else 0
        if dd<=-CFG["hard_drawdown"] or daily<=-CFG["daily_stop"] or weekly<=-CFG["weekly_stop"]: self.halted=True
        return value
    def buy(self,symbol,price,atr,date,sc):
        if self.halted or symbol in self.positions or atr<=0:return
        eq=self.curve[-1]["equity"]; stop=price-2*atr; risk=eq*CFG["risk_per_trade"]; qty=min(risk/max(price-stop,.01),(eq*CFG["max_position_pct"])/price,self.cash/price)
        if qty<=0:return
        fill=price*(1+CFG["slippage_bps"]/10000); self.cash-=qty*fill; self.positions[symbol]={"qty":qty,"entry":fill,"stop":stop,"date":date,"score":sc}
    def sell(self,symbol,price,date,reason):
        p=self.positions.pop(symbol); fill=price*(1-CFG["slippage_bps"]/10000); pnl=(fill-p["entry"])*p["qty"]; self.cash+=fill*p["qty"]; self.trades.append({"symbol":symbol,"entry":str(p["date"]),"exit":str(date),"entry_price":p["entry"],"exit_price":fill,"qty":p["qty"],"pnl":pnl,"reason":reason,"entry_score":p["score"]})
    def report(self):
        t=pd.DataFrame(self.trades); e=pd.DataFrame(self.curve); wins=t.loc[t.pnl>0,"pnl"].sum() if not t.empty else 0; losses=abs(t.loc[t.pnl<0,"pnl"].sum()) if not t.empty else 0
        return {"start":self.start,"end":float(e.iloc[-1].equity) if len(e) else self.start,"return":float(e.iloc[-1].equity/self.start-1) if len(e) else 0,"max_drawdown":float(e.drawdown.min()) if len(e) else 0,"trades":len(t),"trade_log":self.trades,"profit_factor":float(wins/losses) if losses else 0,"win_rate":float((t.pnl>0).mean()) if not t.empty else 0,"halted":self.halted}
    def run(self,df,symbol,strategy):
        x=features(df,strategy["fast"],strategy["slow"],strategy["momentum"])
        for date,r in x.iterrows():
            price,sc=float(r.close),score(r); self.mark(price,symbol,date)
            if symbol in self.positions:
                p=self.positions[symbol]
                if price<=p["stop"] or sc<CFG["exit_score"] or self.halted:self.sell(symbol,price,date,"stop" if price<=p["stop"] else ("risk_halt" if self.halted else "score_exit"))
            elif not self.halted and sc>=strategy["threshold"]:self.buy(symbol,price,float(r.atr),date,sc)
        if symbol in self.positions:self.sell(symbol,float(x.iloc[-1].close),x.index[-1],"end")
        return self.report()
def run_symbol(symbol,strategy):
    df=yf.download(symbol,period=CFG.get("period","5y"),auto_adjust=True,progress=False)
    if df.empty:raise ValueError(f"No market data returned for {symbol}")
    result=Portfolio().run(df,symbol,strategy)
    x=features(df,strategy["fast"],strategy["slow"],strategy["momentum"]); latest=x.iloc[-1]; latest_score=score(latest); threshold=strategy["threshold"]
    if latest_score>=threshold: signal="LONG"
    elif latest_score<CFG["exit_score"]: signal="EXIT/CASH"
    else: signal="HOLD"
    result["current_signal"]={"signal":signal,"score":latest_score,"threshold":threshold,"price":float(latest.close),"as_of":str(x.index[-1]),"confidence":round(min(1.0,latest_score/75),2),"note":"Directional model signal, not a guaranteed forecast."}
    return result
