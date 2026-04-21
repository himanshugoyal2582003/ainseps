import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from typing import List, Dict
import time
import re

# ── Ticker → search slug / company name mapping ─────────────────────────────
TICKER_META = {
    "RELIANCE": {
        "company":    "Reliance Industries",
        "mc_slug":    "reliance-industries",
        "et_slug":    "reliance-industries",
        "google_q":   "Reliance Industries NSE stock",
    },
    "HDFCBANK": {
        "company":    "HDFC Bank",
        "mc_slug":    "hdfc-bank",
        "et_slug":    "hdfc-bank",
        "google_q":   "HDFC Bank NSE stock",
    },
    "INFY": {
        "company":    "Infosys",
        "mc_slug":    "infosys",
        "et_slug":    "infosys",
        "google_q":   "Infosys NSE stock",
    },
    "TATASTEEL": {
        "company":    "Tata Steel",
        "mc_slug":    "tata-steel",
        "et_slug":    "tata-steel",
        "google_q":   "Tata Steel NSE stock",
    },
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class NewsScraper:
    """Scrapes live financial news from multiple sources for NSE/BSE tickers."""

    MAX_PER_SOURCE = 5

    @staticmethod
    def _clean_ticker(ticker: str) -> str:
        return ticker.replace(".NS", "").replace(".BO", "").upper()

    # ── Google News RSS ──────────────────────────────────────────────────────
    @staticmethod
    def _fetch_google_rss(query: str) -> List[Dict]:
        articles = []
        try:
            url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
            resp = requests.get(url, headers=HEADERS, timeout=8)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:NewsScraper.MAX_PER_SOURCE]
            for item in items:
                title = item.findtext("title", "").strip()
                link  = item.findtext("link",  "").strip()
                pub   = item.findtext("pubDate", "").strip()
                # Strip source suffix Google adds: " - Source Name"
                title = re.sub(r"\s*-\s*[^-]+$", "", title).strip()
                if title:
                    articles.append({
                        "title":  title,
                        "url":    link,
                        "source": "Google News",
                        "time":   pub[:16] if pub else "Recent",
                    })
        except Exception as e:
            print(f"[NewsScraper] Google RSS error: {e}")
        return articles

    # ── Moneycontrol ─────────────────────────────────────────────────────────
    @staticmethod
    def _fetch_moneycontrol(slug: str) -> List[Dict]:
        articles = []
        try:
            url = f"https://www.moneycontrol.com/news/tags/{slug}/"
            resp = requests.get(url, headers=HEADERS, timeout=8)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            # MC uses <li class="clearfix"> for news items
            items = soup.select("ul.list_detail li")[:NewsScraper.MAX_PER_SOURCE]
            for item in items:
                a_tag = item.find("a")
                if not a_tag:
                    continue
                title = a_tag.get_text(strip=True)
                href  = a_tag.get("href", "")
                time_tag = item.find("span", class_="articletime")
                pub = time_tag.get_text(strip=True) if time_tag else "Recent"
                if title and href:
                    articles.append({
                        "title":  title,
                        "url":    href,
                        "source": "Moneycontrol",
                        "time":   pub,
                    })
        except Exception as e:
            print(f"[NewsScraper] Moneycontrol error for '{slug}': {e}")
        return articles

    # ── Economic Times ───────────────────────────────────────────────────────
    @staticmethod
    def _fetch_economic_times(slug: str) -> List[Dict]:
        articles = []
        try:
            url = f"https://economictimes.indiatimes.com/topic/{slug}"
            resp = requests.get(url, headers=HEADERS, timeout=8)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            # ET topic page story divs
            items = soup.select("div.eachStory")[:NewsScraper.MAX_PER_SOURCE]
            for item in items:
                a_tag = item.find("a")
                if not a_tag:
                    continue
                title = a_tag.get_text(strip=True)
                href  = a_tag.get("href", "")
                if href and not href.startswith("http"):
                    href = "https://economictimes.indiatimes.com" + href
                time_tag = item.find("time")
                pub = time_tag.get_text(strip=True) if time_tag else "Recent"
                if title and href:
                    articles.append({
                        "title":  title,
                        "url":    href,
                        "source": "Economic Times",
                        "time":   pub,
                    })
        except Exception as e:
            print(f"[NewsScraper] Economic Times error for '{slug}': {e}")
        return articles

    # ── Public entry-point ───────────────────────────────────────────────────
    @classmethod
    def fetch(cls, ticker: str) -> List[Dict]:
        """
        Fetch news articles for a given NSE ticker from multiple sources.
        Returns a list of article dicts with keys:
          title, url, source, time
        Falls back gracefully if any source fails.
        """
        clean = cls._clean_ticker(ticker)
        meta  = TICKER_META.get(clean)

        if not meta:
            # Generic Google News fallback for unknown tickers
            return cls._fetch_google_rss(f"{clean} NSE stock India")

        articles = []

        # Primary: Google News RSS (most reliable, no CAPTCHA)
        articles += cls._fetch_google_rss(meta["google_q"])

        # Secondary: Moneycontrol
        articles += cls._fetch_moneycontrol(meta["mc_slug"])

        # Tertiary: Economic Times
        articles += cls._fetch_economic_times(meta["et_slug"])

        # Deduplicate by title similarity
        seen_titles = set()
        unique = []
        for art in articles:
            key = art["title"][:50].lower().strip()
            if key not in seen_titles:
                seen_titles.add(key)
                unique.append(art)

        return unique  # up to ~15 articles


if __name__ == "__main__":
    scraper = NewsScraper()
    for sym in ["RELIANCE", "HDFCBANK", "INFY", "TATASTEEL"]:
        print(f"\n{'='*50}")
        print(f"  {sym}")
        print(f"{'='*50}")
        news = scraper.fetch(sym)
        for n in news:
            print(f"  [{n['source']}] {n['title'][:70]}")
