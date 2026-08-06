import re
from typing import Dict, List
from textblob import TextBlob
from backend.agents.sentiment_agent import POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS

# Financial impact keywords
HIGH_IMPACT_KEYWORDS = [
    "earnings", "revenue", "profit", "loss", "acquisition", "merger",
    "dividend", "investigation", "penalty", "fda", "sec", "rbi", "fed",
    "layoff", "default", "bankruptcy", "court", "lawsuit", "guidance", "ceo", "resigns"
]

MEDIUM_IMPACT_KEYWORDS = [
    "contract", "deal", "launch", "upgrade", "downgrade", "expansion",
    "target", "growth", "partnership", "shares", "stake", "buyback"
]

class NewsSummaryService:
    @staticmethod
    def analyze_news_item(article: Dict, ticker: str = "") -> Dict:
        """
        Analyzes a news article to generate:
        1. Concise 3-bullet summary
        2. Impact Rating (High / Medium / Low)
        3. Stock Direction Prediction (Stock Will Improve / Stock Will Fall / Neutral)
        """
        title = article.get("title", "")
        url = article.get("url", "#")
        source = article.get("source", "News")
        lower_title = title.lower()

        # 1. NLP Sentiment Scoring via TextBlob + Keywords
        tb_polarity = TextBlob(title).sentiment.polarity
        kw_score = 0.0

        pos_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in lower_title)
        neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in lower_title)

        if pos_count > 0:
            kw_score += 0.4 * pos_count
        if neg_count > 0:
            kw_score -= 0.4 * neg_count

        composite_score = max(-1.0, min(1.0, 0.5 * tb_polarity + 0.5 * kw_score))

        # 2. Impact Rating Calculation
        high_matches = sum(1 for kw in HIGH_IMPACT_KEYWORDS if kw in lower_title)
        med_matches = sum(1 for kw in MEDIUM_IMPACT_KEYWORDS if kw in lower_title)

        if high_matches >= 1 or abs(composite_score) >= 0.5:
            impact_rating = "⚡ HIGH IMPACT"
            impact_badge = "🔥🔥🔥"
        elif med_matches >= 1 or abs(composite_score) >= 0.2:
            impact_rating = "⚡ MEDIUM IMPACT"
            impact_badge = "⚡⚡"
        else:
            impact_rating = "🔹 LOW IMPACT"
            impact_badge = "🔹"

        # 3. Stock Direction Prediction (Improve vs Fall)
        if composite_score > 0.1:
            direction = "🟢 STOCK EXPECTED TO IMPROVE (RISE)"
            direction_emoji = "📈"
            reason = "Positive financial sentiment & growth indicators detected."
        elif composite_score < -0.1:
            direction = "🔴 STOCK EXPECTED TO FALL (DECLINE)"
            direction_emoji = "📉"
            reason = "Negative risk factors, loss warnings, or market headwinds detected."
        else:
            direction = "🟡 NEUTRAL / BALANCED IMPACT"
            direction_emoji = "📊"
            reason = "Balanced or informative news without strong immediate directional bias."

        confidence = round(70.0 + abs(composite_score) * 25.0, 1)

        # 4. Generate 3-bullet summary
        bullets = [
            f"Headline: {title[:90]}",
            f"Market Sentiment: Score = {composite_score:+.2f} ({'Positive' if composite_score > 0 else 'Negative' if composite_score < 0 else 'Neutral'})",
            f"Key Driver: {reason}",
        ]

        return {
            "title": title,
            "url": url,
            "source": source,
            "ticker": ticker.upper(),
            "impact_rating": impact_rating,
            "impact_badge": impact_badge,
            "direction": direction,
            "direction_emoji": direction_emoji,
            "confidence": confidence,
            "summary_bullets": bullets,
            "score": composite_score,
        }

if __name__ == "__main__":
    sample = {
        "title": "Reliance Retail profit surges 25% YoY; Jio announces major AI data center deal",
        "url": "https://moneycontrol.com",
        "source": "Moneycontrol"
    }
    res = NewsSummaryService.analyze_news_item(sample, "RELIANCE")
    print(res)
