from typing import List, Dict
from textblob import TextBlob
from ..services.news_scraper import NewsScraper

# Financial domain keyword boosts (overrides generic TextBlob polarity)
POSITIVE_KEYWORDS = [
    "profit", "growth", "record", "win", "expand", "boost", "upgrade",
    "guidance", "surge", "buy", "outperform", "deal", "contract", "strong",
    "beat", "rally", "gain", "dividend", "acquisition", "launch",
]
NEGATIVE_KEYWORDS = [
    "loss", "decline", "headwind", "slowdown", "warn", "drop", "cut",
    "downgrade", "miss", "risk", "fall", "bearish", "concern", "weak",
    "layoff", "selloff", "penalty", "fraud", "investigation", "debt",
]


class SentimentAgent:

    @staticmethod
    def fetch_news(ticker: str) -> List[Dict]:
        """
        Fetches live news articles for the given ticker via the NewsScraper.
        Each article is a dict: {title, url, source, time}
        """
        return NewsScraper.fetch(ticker)

    @staticmethod
    def _score_article(title: str) -> float:
        """
        Returns a composite sentiment score in [-1.0, +1.0].
        Blends TextBlob polarity (60%) with keyword heuristic (40%).
        """
        lower = title.lower()

        # TextBlob polarity: -1.0 (negative) to +1.0 (positive)
        tb_score = TextBlob(title).sentiment.polarity

        # Keyword heuristic
        kw_score = 0.0
        for kw in POSITIVE_KEYWORDS:
            if kw in lower:
                kw_score += 0.3
        for kw in NEGATIVE_KEYWORDS:
            if kw in lower:
                kw_score -= 0.3
        # Clamp keyword score to [-1, 1]
        kw_score = max(-1.0, min(1.0, kw_score))

        return round(0.6 * tb_score + 0.4 * kw_score, 4)

    @staticmethod
    def analyze_sentiment(articles: List[Dict]) -> Dict:
        """
        Runs NLP sentiment on each article. Returns:
          - sentiment   : "Bullish" | "Bearish" | "Neutral"
          - score       : float in [-1.0, +1.0]  (used by RiskAgent)
          - articles    : full list with per-article label & score
          - reasons     : top 3 human-readable findings
        """
        if not articles:
            return {
                "sentiment": "Neutral",
                "score": 0.0,
                "articles": [],
                "reasons": ["No news articles found for this ticker."],
            }

        scored_articles = []
        for art in articles:
            s = SentimentAgent._score_article(art["title"])
            label = "Positive" if s > 0.05 else ("Negative" if s < -0.05 else "Neutral")
            scored_articles.append({**art, "score": s, "label": label})

        # Aggregate: simple mean of all article scores
        total_score = sum(a["score"] for a in scored_articles) / len(scored_articles)
        total_score = round(max(-1.0, min(1.0, total_score)), 4)

        # Overall label
        if total_score > 0.1:
            sentiment = "Bullish"
        elif total_score < -0.1:
            sentiment = "Bearish"
        else:
            sentiment = "Neutral"

        # Build human-readable reasons from top positive / negative articles
        positive_arts = sorted(
            [a for a in scored_articles if a["label"] == "Positive"],
            key=lambda x: x["score"], reverse=True
        )
        negative_arts = sorted(
            [a for a in scored_articles if a["label"] == "Negative"],
            key=lambda x: x["score"]
        )

        reasons = []
        for art in positive_arts[:2]:
            reasons.append(f"✅ Positive: {art['title'][:60]}...")
        for art in negative_arts[:1]:
            reasons.append(f"⚠️ Negative: {art['title'][:60]}...")
        if not reasons:
            reasons.append(f"Sentiment score: {total_score:.2f} — market appears {sentiment.lower()}.")

        return {
            "sentiment": sentiment,
            "score": total_score,
            "articles": scored_articles,
            "reasons": reasons[:3],
        }


if __name__ == "__main__":
    tickers = ["RELIANCE", "HDFCBANK", "INFY", "TATASTEEL"]
    for t in tickers:
        print(f"\n{'='*50}  {t}")
        news = SentimentAgent.fetch_news(t)
        result = SentimentAgent.analyze_sentiment(news)
        print(f"  Sentiment : {result['sentiment']}  (score={result['score']})")
        print(f"  Articles  : {len(result['articles'])}")
        for r in result["reasons"]:
            print(f"  • {r}")
