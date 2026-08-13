from engine.gates import consistency_gate

def test_gate_needs_three_windows():
    assert consistency_gate([])["pass"] is False
