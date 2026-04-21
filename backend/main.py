import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from .agents.graph import StockPredictorGraph
from .services.data_fetcher import DataFetcher
from .services.news_scraper import NewsScraper
from .services.predictor_service import get_predictor
from .agents.sentiment_agent import SentimentAgent
import json
import asyncio

app = FastAPI(title="AI Stock Prediction System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

predictor_graph = StockPredictorGraph()


@app.get("/")
def read_root():
    return {"message": "AI Stock Prediction System Backend Running"}


@app.get("/predict/{ticker}")
async def get_prediction(ticker: str):
    """Triggers the full multi-agent prediction flow."""
    result = predictor_graph.run(ticker)
    return result["final_output"]


@app.get("/history/{ticker}")
async def get_history(ticker: str):
    """Fetches historical price data for charting."""
    df = DataFetcher.get_stock_data(ticker)
    history = []
    for date, row in df.iterrows():
        history.append({
            "date":  date.strftime("%Y-%m-%d"),
            "price": round(float(row["Close"]), 2),
            "type":  "historical",
        })
    return history


@app.get("/news/{ticker}")
async def get_news(ticker: str):
    """
    Scrapes live news and returns articles with per-article sentiment labels.
    """
    articles = NewsScraper.fetch(ticker)
    analysed = SentimentAgent.analyze_sentiment(articles)
    return {
        "ticker":    ticker.upper().replace(".NS", "").replace(".BO", ""),
        "sentiment": analysed["sentiment"],
        "score":     analysed["score"],
        "articles":  analysed["articles"],
    }


@app.get("/forecast/{ticker}")
async def get_forecast(ticker: str, days: int = 30):
    """
    Trains the XGBoost model on 2 years of data, back-tests for accuracy,
    then returns:
      - series   : combined historical + predicted price points
      - accuracy : back-test metrics (MAPE, price accuracy, direction accuracy)
      - split_date : date where historical ends and prediction begins
    Query param `days` controls how many future days to predict (default 30).
    """
    svc    = get_predictor(ticker)
    result = svc.get_full_series(ticker, future_days=min(days, 90))
    return result


@app.get("/retrain/{ticker}")
async def retrain(ticker: str):
    """
    Forces a fresh model retrain for the given ticker (clears cache).
    Useful for live retraining on latest data.
    """
    from .services.predictor_service import _predictor_cache
    from .services import predictor_service as ps
    clean = ticker.upper().replace(".NS", "").replace(".BO", "")
    if clean in ps._predictor_cache:
        del ps._predictor_cache[clean]
    svc    = get_predictor(clean)
    result = svc.get_full_series(clean, future_days=30)
    return {"status": "retrained", "accuracy": result["accuracy"]}


@app.websocket("/ws/analyze/{ticker}")
async def websocket_endpoint(websocket: WebSocket, ticker: str):
    await websocket.accept()
    try:
        # Step 1: Technical Analysis
        await websocket.send_text(json.dumps({"status": "Technical Analysis started..."}))
        await asyncio.sleep(1)
        df = DataFetcher.get_stock_data(ticker)
        from .agents.technical_agent import TechnicalAgent
        tech_res = TechnicalAgent.analyze(df)
        await websocket.send_text(json.dumps({"agent": "Technical Analyst", "result": tech_res}))

        # Step 2: Sentiment Analysis (real scraper)
        await websocket.send_text(json.dumps({"status": "Scraping & analysing live news..."}))
        await asyncio.sleep(1)
        articles = SentimentAgent.fetch_news(ticker)
        sent_res = SentimentAgent.analyze_sentiment(articles)
        await websocket.send_text(json.dumps({"agent": "Sentiment Analyst", "result": sent_res}))

        # Step 3: Risk Assessment
        await websocket.send_text(json.dumps({"status": "Risk Assessment started..."}))
        await asyncio.sleep(1)
        from .agents.risk_agent import RiskManagerAgent
        risk_res = RiskManagerAgent.calculate_risk(
            ticker,
            tech_res.get("latest_close", 0),
            0.05,
            tech_res.get("signal", "Neutral"),
            sent_res.get("sentiment", "Neutral"),
            sentiment_score=sent_res.get("score", 0.0),
        )
        await websocket.send_text(json.dumps({"agent": "Risk Manager", "result": risk_res}))

        # Final Summary
        await websocket.send_text(json.dumps({
            "status": "Analysis Complete",
            "final": {
                "recommendation": risk_res["recommendation"],
                "ticker":         ticker,
            },
        }))

    except WebSocketDisconnect:
        print(f"Client disconnected for ticker: {ticker}")
    except Exception as e:
        await websocket.send_text(json.dumps({"error": str(e)}))
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
