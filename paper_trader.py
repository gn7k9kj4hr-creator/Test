import alpaca_trade_api as tradeapi
from datetime import datetime

class PaperTrader:
    def __init__(self, api_key, secret_key):
        self.api = tradeapi.REST(api_key=api_key, secret_key=secret_key, base_url='https://paper-api.alpaca.markets')
        self.trades_log = []

    def execute_trade(self, ticker, quantity, side='buy', strategy_name='Unknown'):
        if side not in ('buy', 'sell'):
            raise ValueError('side must be buy or sell')
        try:
            order = self.api.submit_order(symbol=ticker, qty=quantity, side=side, type='market', time_in_force='day')
            record = {'timestamp': datetime.now().isoformat(), 'ticker': ticker, 'quantity': quantity,
                      'side': side, 'strategy': strategy_name, 'order_id': order.id}
            self.trades_log.append(record)
            print(f'✓ {side.upper()} {quantity} {ticker} via {strategy_name}')
            return order
        except Exception as e:
            print(f'✗ Paper trade failed: {e}')
            return None

    def get_account_value(self):
        account = self.api.get_account()
        return {'portfolio_value': float(account.portfolio_value), 'cash': float(account.cash),
                'buying_power': float(account.buying_power)}

    def get_positions(self):
        positions = self.api.list_positions()
        return {p.symbol: {'qty': float(p.qty), 'entry_price': float(p.avg_fill_price),
                           'current_price': float(p.current_price), 'pnl': float(p.unrealized_pl)} for p in positions}
