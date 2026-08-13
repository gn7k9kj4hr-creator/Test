def vote(r):
    votes={"risk":"PASS" if r["max_drawdown"]>-0.15 else "FAIL","edge":"PASS" if r["profit_factor"]>=1.10 else "FAIL","sample":"PASS" if r["trades"]>=10 else "FAIL","return":"PASS" if r["return"]>0 else "FAIL"}
    n=sum(v=="PASS" for v in votes.values()); return {"votes":votes,"decision":"PASS" if n==4 else ("REVIEW" if n>=3 else "FAIL")}
