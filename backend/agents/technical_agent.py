import pandas as pd
import ta

class TechnicalAgent:
    @staticmethod
    def analyze(df: pd.DataFrame) -> dict:
        """
        Performs technical analysis using RSI, MACD, and Bollinger Bands.
        """
        # Ensure enough data
        if len(df) < 30:
            return {"signal": "Neutral", "reason": "Insufficient data"}

        # Indicators
        df["rsi"] = ta.momentum.RSIIndicator(close=df["Close"], window=14).rsi()

        macd = ta.trend.MACD(close=df["Close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()

        bb = ta.volatility.BollingerBands(close=df["Close"])
        df["bb_high"] = bb.bollinger_hband()
        df["bb_low"] = bb.bollinger_lband()

        latest = df.iloc[-1]

        rsi = latest["rsi"]
        macd_val = latest["macd"]
        macds = latest["macd_signal"]

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
        if macd_val > macds:
            reasons.append("MACD Bullish Crossover")
            if signal != "Sell":
                signal = "Buy"
        else:
            reasons.append("MACD Bearish Crossover")
            if signal != "Buy":
                signal = "Sell"

        return {
            "signal": signal,
            "rsi": round(float(rsi), 2),
            "reasons": reasons,
            "latest_close": round(float(latest["Close"]), 2)
        }


if __name__ == "__main__":
    sample_df = pd.DataFrame({
        "Close": [100 + i for i in range(50)],
        "High": [105 + i for i in range(50)],
        "Low": [95 + i for i in range(50)],
        "Volume": [1000 for _ in range(50)]
    })

    analysis = TechnicalAgent.analyze(sample_df)
    print(analysis)