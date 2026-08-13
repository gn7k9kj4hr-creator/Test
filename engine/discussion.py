import json
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/ai_discussion.json'
def build(report):
    messages=[]
    for a in report.get('agents',[]):
        s=a.get('selection') or {}; sym=s.get('symbol','none')
        messages += [
          {'agent':f'Agent {a["agent"]}','role':'Lead','text':f'Candidate: {sym}. Score: {s.get("score","—")}. Final paper decision: {s.get("decision","PASS")}.'},
          {'agent':f'Agent {a["agent"]}','role':'Analyst A','text':f'{sym}: {"PASS" if s.get("analyst_a") else "REVIEW"}. Risk controls remain in force.'},
          {'agent':f'Agent {a["agent"]}','role':'Analyst B','text':f'{sym}: {"PASS" if s.get("analyst_b") else "REVIEW"}. Final decision stays within arena rules.'}
        ]
    result={'generated_at':datetime.now(timezone.utc).isoformat(),'mode':'DRY_RUN','messages':messages}
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(result,indent=2)); return result
if __name__=='__main__': build(json.loads((ROOT/'reports/arena_state.json').read_text()))
