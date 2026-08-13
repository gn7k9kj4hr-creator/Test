"""Paper-trading support agents.

These agents may revise research parameters and request another simulation run,
but they cannot place orders, connect to a broker, or access brokerage credentials.
"""
from copy import deepcopy

ALLOWED_CHANGES = {
    'threshold': (-20, 20),
    'fast': (-5, 5),
    'slow': (-10, 10),
    'momentum': (-10, 10),
}

def review_and_adjust(strategy, candidates):
    """Return a bounded research-only adjustment based on analyst disagreement."""
    s = deepcopy(strategy)
    if not candidates:
        return s, {'action': 'NO_CHANGE', 'reason': 'no_candidates'}
    scores = [float(c.get('score', 0)) for c in candidates if c.get('score') is not None]
    if not scores:
        return s, {'action': 'NO_CHANGE', 'reason': 'no_scores'}
    avg = sum(scores) / len(scores)
    # Analysts can make small, bounded research adjustments only.
    if avg < 35:
        s['threshold'] = min(s.get('threshold', 50) + 5, 90)
        action = 'RAISE_THRESHOLD'
    elif avg > 65:
        s['threshold'] = max(s.get('threshold', 50) - 3, 20)
        action = 'LOWER_THRESHOLD'
    else:
        action = 'NO_CHANGE'
    return s, {'action': action, 'average_score': round(avg, 2), 'rerun': action != 'NO_CHANGE'}


def validate_paper_trade(selection, virtual_cash):
    """Final safety gate for the simulation; never creates a real order."""
    if not selection:
        return False, 'no_selection'
    price = float(selection.get('price', 0))
    if price <= 0:
        return False, 'invalid_price'
    if price > virtual_cash:
        return False, 'insufficient_virtual_cash_for_whole_share'
    if selection.get('decision') != 'BUY_SIM':
        return False, 'agent_did_not_approve'
    return True, 'paper_trade_allowed'
