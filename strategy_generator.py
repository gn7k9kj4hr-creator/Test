"""Keyless strategy generator.

Uses deterministic, transparent technical rules instead of an LLM API key.
"""
class StrategyGenerator:
    def generate_strategy(self, iteration=1, previous_results="None"):
        variants = [
            ("Momentum Breakout", "Close above 20-day average with rising volume", "+4% target / -2% stop", "2:1", "25%", ["SMA20", "volume"]),
            ("Trend Pullback", "Close above SMA50 after a pullback", "+5% target / -2.5% stop", "2:1", "20%", ["SMA50", "RSI"]),
            ("Volume Surge", "Volume above 20-day average and positive momentum", "+4% target / -2% stop", "2:1", "20%", ["volume", "ROC"]),
            ("Mean Reversion", "RSI recovers from oversold while price stabilizes", "+3% target / -1.5% stop", "2:1", "15%", ["RSI", "SMA20"]),
            ("Conservative Trend", "SMA20 above SMA50 with positive 20-day return", "+6% target / -3% stop", "2:1", "15%", ["SMA20", "SMA50", "ROC"]),
        ]
        name, entry, exit_, rr, size, indicators = variants[(iteration-1) % len(variants)]
        return {"name":name,"entry_condition":entry,"exit_condition":exit_,"risk_reward":rr,"position_size":size,"market_conditions":"liquid, non-leveraged equities; paper trading only","indicator_list":indicators}
