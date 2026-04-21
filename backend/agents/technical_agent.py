import pandas_ta as ta
import pandas as pd

class TechnicalAgent:
    @staticmethod
    def analyze(df: pd.DataFrame) -> dict:
        """
        Performs technical analysis using RSI, MACD, and Bollinger Bands.
        """
        # Ensure enough data
        if len(df) < 30:
            return {"signal": "Neutral", "reason": "Insufficient data"}

        # Calculate Indicators
        df.ta.rsi(append=True)
        df.ta.macd(append=True)
        df.ta.bbands(append=True)

        latest = df.iloc[-1]
        rsi = latest['RSI_14']
        macd = latest['MACD_12_26_9']
        macds = latest['MACDs_12_26_9']
        
        signal = "Neutral"
        reasons = []

        # RSI conditions
        if rsi < 30:
            reasons.append("Oversold (RSI < 30)")
            signal = "Buy"
        elif rsi > 70:
            reasons.append("Overbought (RSI > 70)")
            signal = "Sell"

        # MACD conditions
        if macd > macds:
            reasons.append("MACD Bullish Crossover")
            if signal != "Sell": signal = "Buy"
        else:
            reasons.append("MACD Bearish Crossover")
            if signal != "Buy": signal = "Sell"

        return {
            "signal": signal,
            "rsi": round(rsi, 2),
            "reasons": reasons,
            "latest_close": round(latest['Close'], 2)
        }

if __name__ == "__main__":
    # Test
    sample_df = pd.DataFrame({
        "Close": [100 + i for i in range(50)],
        "High": [105 + i for i in range(50)],
        "Low": [95 + i for i in range(50)],
        "Volume": [1000 for _ in range(50)]
    })
    analysis = TechnicalAgent.analyze(sample_df)
    print(analysis)
