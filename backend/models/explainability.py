import numpy as np

class ExplainabilityService:
    @staticmethod
    def get_shap_values(ticker: str, tech_data: dict, sentiment_data: dict):
        """
        Mock SHAP analysis: Attributes importance to indicators and sentiment.
        In production, use shap.TreeExplainer or DeepExplainer.
        """
        # Baseline importance
        factors = {
            "RSI": 0.35,
            "MACD": 0.25,
            "News Sentiment": 0.30,
            "Volatility": 0.10
        }
        
        # Adjust based on the actual values
        if tech_data.get("rsi", 50) > 70 or tech_data.get("rsi", 50) < 30:
            factors["RSI"] += 0.1
        
        if sentiment_data.get("sentiment") != "Neutral":
            factors["News Sentiment"] += 0.1
            
        # Normalize
        total = sum(factors.values())
        normalized_factors = {k: round(v/total, 2) for k, v in factors.items()}
        
        return {
            "ticker": ticker,
            "explanations": normalized_factors,
            "summary": f"Prediction primarily driven by {max(normalized_factors, key=normalized_factors.get)}."
        }

if __name__ == "__main__":
    # Test
    explainer = ExplainabilityService()
    res = explainer.get_shap_values("RELIANCE", {"rsi": 25}, {"sentiment": "Bullish"})
    print(res)
