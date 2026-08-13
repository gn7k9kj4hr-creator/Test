from strategy_generator import StrategyGenerator
from backtester import StrategyBacktester
from paper_trader import PaperTrader
import time
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class AITradingAgent:
    """AI research -> backtest -> Alpaca PAPER trading pipeline."""
    def __init__(self):
        self.generator = StrategyGenerator()
        self.backtester = StrategyBacktester()
        self.trader = PaperTrader(api_key=os.getenv('ALPACA_API_KEY'), secret_key=os.getenv('ALPACA_SECRET_KEY'))
        self.iteration = 0

    def run_cycle(self, num_strategies=5, ticker='SPY'):
        self.iteration += 1
        print(f"\n{'='*60}\nCYCLE {self.iteration} - {datetime.now():%Y-%m-%d %H:%M:%S}\n{'='*60}")

        generated = []
        print('\n📊 GENERATING STRATEGIES...')
        for i in range(num_strategies):
            strategy = self.generator.generate_strategy(iteration=self.iteration)
            if strategy:
                generated.append(strategy)
                print(f"  ✓ {strategy.get('name', f'Strategy_{i}')}")
            time.sleep(1)

        validated = []
        print('\n🔬 BACKTESTING...')
        for strategy in generated:
            results = self.backtester.backtest_strategy(strategy, ticker=ticker)
            if not results:
                continue
            print(f"  {strategy.get('name')}: {results['return_pct']:.2f}% | Sharpe: {results['sharpe_ratio']:.2f} | Win: {results['win_rate']:.1f}%")
            if self.backtester.is_strategy_profitable(results):
                validated.append((strategy, results))
                print('    ✓ APPROVED FOR PAPER TRADING')
            else:
                print('    ✗ Rejected')

        print('\n🚀 PAPER TRADING ONLY...')
        for strategy, _ in validated[:2]:
            self.trader.execute_trade(ticker=ticker, quantity=1, side='buy', strategy_name=strategy.get('name', 'Unknown'))

        print('\n📈 PAPER ACCOUNT STATUS:')
        account = self.trader.get_account_value()
        print(f"  Portfolio Value: ${account['portfolio_value']:.2f}")
        print(f"  Cash: ${account['cash']:.2f}")
        positions = self.trader.get_positions()
        for symbol, pos in positions.items():
            print(f"  {symbol}: {pos['qty']} | P&L: ${pos['pnl']:.2f}")
        print(f'\n✓ Cycle {self.iteration} complete')

if __name__ == '__main__':
    agent = AITradingAgent()
    agent.run_cycle(num_strategies=5)
    # For scheduled paper runs, call run_cycle from your scheduler.
