import json
from datetime import datetime,timezone
from pathlib import Path
from .simulator import run_symbol,CFG
from .agents import vote
from .gates import champion_challenger
ROOT=Path(__file__).resolve().parents[1]
def main():
    result={"generated_at":datetime.now(timezone.utc).isoformat(),"mode":"DRY_RUN","strategies":{}}; summary={}
    for name,strategy in CFG["strategies"].items():
        rows=[]
        for symbol in CFG["symbols"]:
            r=run_symbol(symbol,strategy); r["symbol"]=symbol; r["agent_vote"]=vote(r); rows.append(r)
        summary[name]={"avg_return":sum(r["return"] for r in rows)/len(rows),"worst_drawdown":min(r["max_drawdown"] for r in rows),"avg_profit_factor":sum(r["profit_factor"] for r in rows)/len(rows),"total_trades":sum(r["trades"] for r in rows),"agent_passes":sum(r["agent_vote"]["decision"]=="PASS" for r in rows),"symbols":rows}
    result["strategies"]=summary; champion=summary["champion"]; result["champion_decision"]=champion_challenger(champion,{k:v for k,v in summary.items() if k!="champion"}); out=ROOT/"reports/latest.json"; out.parent.mkdir(exist_ok=True); out.write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
if __name__=="__main__":main()
