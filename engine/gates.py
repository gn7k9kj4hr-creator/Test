def consistency_gate(windows):
    if len(windows)<3:return {"pass":False,"reason":"need_30_60_90_day_windows"}
    if any(x["trades"]<3 for x in windows):return {"pass":False,"reason":"insufficient_trades"}
    if any(x["max_drawdown"]<=-.15 for x in windows):return {"pass":False,"reason":"drawdown_breach"}
    if sum(x["return"]>0 for x in windows)<2:return {"pass":False,"reason":"inconsistent_returns"}
    if sum(x["profit_factor"]>=1.1 for x in windows)<2:return {"pass":False,"reason":"weak_profit_factor"}
    return {"pass":True,"reason":"consistency_pass"}

def champion_challenger(champion,challengers):
    ranked=sorted(challengers.items(),key=lambda kv:(kv[1]["return"],kv[1]["profit_factor"]),reverse=True)
    if not ranked:return {"decision":"KEEP_CHAMPION"}
    name,best=ranked[0]
    if best["return"]>champion["return"] and best["max_drawdown"]>=champion["max_drawdown"]-.03:return {"decision":"PROMOTE_CHALLENGER","winner":name}
    return {"decision":"KEEP_CHAMPION","best_challenger":name}
