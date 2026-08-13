import numpy as np
import pandas as pd

def features(df, fast, slow, momentum):
    x=df.copy()
    if isinstance(x.columns,pd.MultiIndex): x.columns=[str(c[0]).lower() for c in x.columns]
    else: x.columns=[str(c).lower() for c in x.columns]
    required={"open","high","low","close","volume"}; missing=required-set(x.columns)
    if missing: raise ValueError(f"Missing columns: {sorted(missing)}")
    x=x[~x.index.duplicated(keep="last")].sort_index()
    x["fast"]=x.close.rolling(fast).mean(); x["slow"]=x.close.rolling(slow).mean()
    x["ret5"]=x.close.pct_change(5); x["retm"]=x.close.pct_change(momentum)
    d=x.close.diff(); g=d.clip(lower=0).rolling(14).mean(); l=(-d.clip(upper=0)).rolling(14).mean(); rs=g/l.replace(0,np.nan)
    x["rsi"]=100-100/(1+rs)
    tr=pd.concat([x.high-x.low,(x.high-x.close.shift()).abs(),(x.low-x.close.shift()).abs()],axis=1).max(axis=1)
    x["atr"]=tr.rolling(14).mean(); x["vol"]=x.close.pct_change().rolling(20).std()*np.sqrt(252)
    return x.replace([np.inf,-np.inf],np.nan).dropna()

def score(r):
    s=0; s+=10 if r.close>r.fast else 0; s+=10 if r.close>r.slow else 0; s+=10 if r.fast>r.slow else 0; s+=10 if r.ret5>0 else 0; s+=15 if r.retm>0 else 0; s+=10 if 50<=r.rsi<=70 else (5 if 45<=r.rsi<50 else 0); s+=10 if r.vol<.25 else (5 if r.vol<.40 else 0); return int(s)
