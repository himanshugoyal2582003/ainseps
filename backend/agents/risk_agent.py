class RiskManagerAgent:
    @staticmethod
    def calculate_risk(
        ticker: str,
        current_price: float,
        volatility: float,
        tech_signal: str,
        sent_signal: str,
        sentiment_score: float = 0.0,   # NEW: numeric score from SentimentAgent [-1, +1]
    ) -> dict:
        """
        Calculates risk score and provides stop-loss / take-profit levels.

        Risk score: 1 (Low risk, high confidence) → 10 (High risk, avoid trade)

        Sentiment score influence:
          score > +0.3  → strong bullish news  → lower risk by 2
          score > +0.1  → mild bullish          → lower risk by 1
          score < -0.3  → strong bearish news   → raise risk by 2
          score < -0.1  → mild bearish           → raise risk by 1
          signals agree → high confidence        → lower risk by 1
          signals conflict, both non-neutral     → raise risk by 2
        """
        risk_score = 5  # baseline

        # ── Numeric sentiment influence ──────────────────────────────────────
        if sentiment_score > 0.3:
            risk_score -= 2
        elif sentiment_score > 0.1:
            risk_score -= 1
        elif sentiment_score < -0.3:
            risk_score += 2
        elif sentiment_score < -0.1:
            risk_score += 1

        # ── Signal agreement / conflict ──────────────────────────────────────
        # Normalize sent_signal to Buy / Sell vocabulary for comparison
        _sent = "Buy" if sent_signal == "Bullish" else ("Sell" if sent_signal == "Bearish" else "Neutral")
        if tech_signal == _sent and tech_signal != "Neutral":
            risk_score -= 1   # strong agreement → lower risk
        elif tech_signal != "Neutral" and _sent != "Neutral" and tech_signal != _sent:
            risk_score += 2   # conflicting → increase risk

        # Clamp to valid range
        risk_score = max(1, min(10, risk_score))

        # ── Price levels ─────────────────────────────────────────────────────
        # Stop loss: 2% below; tighten to 1.5% on high-risk, loosen to 2.5% on low
        sl_pct = 0.015 if risk_score >= 8 else (0.025 if risk_score <= 3 else 0.02)
        stop_loss   = round(current_price * (1 - sl_pct), 2)
        take_profit = round(current_price * 1.05, 2)

        # ── Assessment ───────────────────────────────────────────────────────
        if risk_score <= 3:
            assessment = "Low"
            recommendation = "STRONG BUY" if tech_signal == "Buy" else "BUY"
        elif risk_score <= 6:
            assessment = "Moderate"
            recommendation = "HOLD / WATCH"
        else:
            assessment = "High"
            recommendation = "AVOID / SELL"

        return {
            "ticker":         ticker,
            "risk_score":     risk_score,
            "assessment":     assessment,
            "stop_loss":      stop_loss,
            "take_profit":    take_profit,
            "recommendation": recommendation,
            "sentiment_influence": round(sentiment_score, 4),
        }


if __name__ == "__main__":
    result = RiskManagerAgent.calculate_risk(
        "RELIANCE", 2500.0, 0.05, "Buy", "Bullish", sentiment_score=0.45
    )
    print(result)
