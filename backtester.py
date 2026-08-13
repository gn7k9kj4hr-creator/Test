import backtrader as bt
import yfinance as yf
from datetime import datetime, timedelta

class PennyStockStrategy(bt.Strategy):
    params = dict(strategy_config=None)

    def __init__(self):
        self.config = self.p.strategy_config or {}
        self.order = None
        self.entry_price = None
        self.trades_count = 0
        self.winning_trades = 0

    def next(self):
        if self.order:
            return
        if not self.position:
            if self._check_entry():
                self.entry_price = float(self.data.close[0])
                self.order = self.buy()
        else:
            pnl_pct = (float(self.data.close[0]) - self.entry_price) / self.entry_price
            if pnl_pct > 0.04 or pnl_pct < -0.02:
                self.order = self.sell()

    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None
        if order.status == order.Completed and order.isclosed:
            self.trades_count += 1
            if order.executed.pnl > 0:
                self.winning_trades += 1

    def _check_entry(self):
        return len(self.data) > 50

class StrategyBacktester:
    def __init__(self):
        self.results_history = []

    def backtest_strategy(self, strategy_config, ticker='SPY', days=252):
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)
            if data.empty:
                return None
            cerebro = bt.Cerebro()
            cerebro.broker.setcash(10000)
            cerebro.broker.setcommission(commission=0.001)
            cerebro.adddata(bt.feeds.PandasData(dataname=data))
            cerebro.addstrategy(PennyStockStrategy, strategy_config=strategy_config)
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            results = cerebro.run()
            strat = results[0]
            final_value = cerebro.broker.getvalue()
            return_pct = ((final_value - 10000) / 10000) * 100
            sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0) or 0
            result = {
                'strategy_name': strategy_config.get('name', 'Unknown'),
                'ticker': ticker, 'final_value': final_value, 'return_pct': return_pct,
                'sharpe_ratio': sharpe, 'num_trades': strat.trades_count,
                'winning_trades': strat.winning_trades,
                'win_rate': (strat.winning_trades / strat.trades_count * 100) if strat.trades_count else 0,
            }
            self.results_history.append(result)
            return result
        except Exception as e:
            print(f'Backtest failed: {e}')
            return None

    def is_strategy_profitable(self, results, min_return=5, min_sharpe=0.5, min_win_rate=50):
        if results is None:
            return False
        return (results['return_pct'] > min_return and results['sharpe_ratio'] > min_sharpe
                and results['win_rate'] > min_win_rate and results['num_trades'] > 10)

    def get_best_strategies(self, top_n=3):
        return sorted(self.results_history, key=lambda x: x['sharpe_ratio'], reverse=True)[:top_n]
