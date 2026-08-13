import json
from pathlib import Path
from datetime import datetime, timezone
from .arena import run
ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'config/arena.json').read_text())
STATE=ROOT/'reports/arena_state.json'

def evaluate_and_adjust(report):
    decisions=[]
    for a in report.get('agents',[]):
        s=a.get('selection')
        if not s:
            decisions.append({'agent':a['agent'],'action':'NO_TRADE','reason':'No candidate passed both analyst checks'})
            continue
        if not (CFG['universe_rules']['min_price'] <= s['price'] <= CFG['universe_rules']['max_price']):
            decisions.append({'agent':a['agent'],'action':'REJECT','reason':'Outside paper universe price band'})
        else:
            decisions.append({'agent':a['agent'],'action':'PAPER_TRADE_ELIGIBLE','symbol':s['symbol'],'reason':'Passed two analyst reviews and universe rules'})
    return decisions

def main():
    report=run()
    report['controls']=CFG
    report['controller']={'evaluated_at':datetime.now(timezone.utc).isoformat(),'decisions':evaluate_and_adjust(report),'reruns_used':0}
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(report,indent=2))
    return report
if __name__=='__main__': print(json.dumps(main(),indent=2))
