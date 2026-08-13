from strategy_generator import StrategyGenerator
from backtester import StrategyBacktester
from paper_trader import PaperTrader
import json
from datetime import datetime

class AITradingAgent:
    def __init__(self):
        self.generator=StrategyGenerator(); self.backtester=StrategyBacktester(); self.trader=PaperTrader(); self.iteration=0
    def run_cycle(self,num_strategies=5,ticker='SPY'):
        self.iteration+=1; generated=[self.generator.generate_strategy(self.iteration+i) for i in range(num_strategies)]
        validated=[]
        for s in generated:
            r=self.backtester.backtest_strategy(s,ticker=ticker)
            if r and self.backtester.is_strategy_profitable(r): validated.append((s,r))
        report={'generated_at':datetime.now().isoformat(),'mode':'DRY_RUN','ticker':ticker,'strategies':[]}
        for s,r in [(s,r) for s,r in validated[:2]]:
            report['strategies'].append({'strategy':s,'backtest':r})
        return report

if __name__=='__main__':
    print(json.dumps(AITradingAgent().run_cycle(),indent=2))
