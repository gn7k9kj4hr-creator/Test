import json
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'reports/predictions.json'

def record_predictions(result):
    old=[]
    if PATH.exists():
        try: old=json.loads(PATH.read_text())
        except Exception: old=[]
    for strategy,summary in result.get('strategies',{}).items():
        for row in summary.get('symbols',[]):
            sig=row.get('current_signal')
            if not sig: continue
            old.append({'created_at':datetime.now(timezone.utc).isoformat(),'strategy':strategy,'symbol':row['symbol'],'signal':sig['signal'],'score':sig['score'],'price':sig['price'],'as_of':sig['as_of'],'confidence':sig['confidence']})
    # Keep a bounded journal so the public Pages site stays small.
    PATH.parent.mkdir(exist_ok=True); PATH.write_text(json.dumps(old[-5000:],indent=2))
    return old[-5000:]

def accuracy_stats(predictions, current_prices):
    stats={}
    for p in predictions:
        if p.get('signal') not in ('LONG','EXIT/CASH'): continue
        # Current price comparison is supplied by the caller; this is an audit metric, not a guarantee.
        now=current_prices.get(p['symbol'])
        if now is None: continue
        move=(now/p['price'])-1
        correct=(move>0) if p['signal']=='LONG' else (move<=0)
        key=p['strategy']; stats.setdefault(key,{'evaluated':0,'correct':0})
        stats[key]['evaluated']+=1; stats[key]['correct']+=int(correct)
    for s in stats.values(): s['accuracy']=s['correct']/s['evaluated'] if s['evaluated'] else 0
    return stats
