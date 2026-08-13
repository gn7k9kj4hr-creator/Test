import json
from pathlib import Path
from datetime import datetime, timezone
import yfinance as yf
from .features import features, score
ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'config/config.json').read_text())
ARENA=ROOT/'config/arena.json'

# Real market-data universe for research only. Agents may select from this list after screening.
# This is deliberately not connected to a broker or order-entry system.
def universe():
    return CFG.get('penny_stock_universe', [
        'SNDL','SOFI','PLUG','OPEN','CLOV','NOK','BB','MARA','RIOT','DNA',
        'JOBY','LCID','IONQ','BBAI','SIRI','GRAB','GPRO','WKHS','ATER','AMC'
    ])

def snapshot(symbol):
    df=yf.download(symbol, period='6mo', interval='1d', auto_adjust=True, progress=False)
    if df.empty or len(df)<60: return None
    x=features(df,10,30,20).dropna()
    if x.empty: return None
    r=x.iloc[-1]
    return {'symbol':symbol,'price':float(r.close),'score':float(score(r)),'volume':float(r.volume),'as_of':str(x.index[-1]),'return_20d':float(r.close/x.iloc[-21].close-1) if len(x)>21 else 0}

def analyst(view, style):
    if style=='momentum': return view['score']>=45 and view['return_20d']>0
    if style=='volume': return view['score']>=40 and view['volume']>0
    return view['score']>=50

def run():
    cfg=json.loads(ARENA.read_text()) if ARENA.exists() else {'agents':4,'starting_cash':25}
    views=[v for s in universe() if (v:=snapshot(s))]
    views=sorted(views,key=lambda x:x['score'],reverse=True)
    out={'generated_at':datetime.now(timezone.utc).isoformat(),'mode':'DRY_RUN','starting_cash':cfg.get('starting_cash',25),'universe_size':len(views),'agents':[]}
    styles=['momentum','volume','balanced','contrarian']
    for i in range(4):
        candidates=views[:max(1,min(10,len(views)))]
        if styles[i]=='contrarian': candidates=sorted(views,key=lambda x:x['score'])[:5] or views
        ranked=[]
        for v in candidates:
            a=analyst(v,'momentum' if i==0 else 'volume')
            b=analyst(v,'balanced')
            final=a and b
            ranked.append({**v,'analyst_a':a,'analyst_b':b,'decision':'BUY_SIM' if final else 'PASS'})
        chosen=next((x for x in ranked if x['decision']=='BUY_SIM'),None)
        out['agents'].append({'agent':i+1,'virtual_cash':cfg.get('starting_cash',25),'style':styles[i],'selection':chosen,'candidates':ranked[:10]})
    return out

if __name__=='__main__':
    report=run(); (ROOT/'reports').mkdir(exist_ok=True); (ROOT/'reports/arena.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
