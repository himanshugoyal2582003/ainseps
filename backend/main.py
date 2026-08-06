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

from .telegram_bot import TelegramBot, bot_instance

app = FastAPI(title="AI Stock Prediction System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

predictor_graph = StockPredictorGraph()
telegram_task = None


@app.on_event("startup")
async def startup_event():
    """Launches the Telegram Bot long-polling loop when FastAPI starts."""
    global telegram_task
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token:
        print("[FastAPI] Launching Telegram Bot in background...")
        telegram_task = asyncio.create_task(bot_instance.start())
    else:
        print("[FastAPI] TELEGRAM_BOT_TOKEN not found, skipping Telegram Bot startup.")


@app.on_event("shutdown")
async def shutdown_event():
    """Stops the Telegram Bot on FastAPI shutdown."""
    if bot_instance:
        await bot_instance.stop()


@app.get("/")
def read_root():
    return {
        "message": "AI Stock Prediction System Backend Running",
        "telegram_bot": "t.me/ainsep_bot",
        "telegram_status": "online" if bot_instance.running else "offline",
    }


from fastapi.responses import FileResponse
from pydantic import BaseModel
from .services.pdf_generator import PDFReportGenerator
from .services.db_service import db_service


class TelegramLinkRequest(BaseModel):
    phone_or_account: str
    chat_id: int = 0
    stocks: list = []


@app.get("/download-pdf/{ticker}")
async def download_stock_pdf(ticker: str):
    """
    Generates and downloads a dedicated stock-wise executive PDF summary
    for RELIANCE, HDFCBANK, INFY, TATASTEEL, or any equity symbol.
    """
    clean_t = ticker.upper().replace(".NS", "").replace(".BO", "")
    pdf_filepath = await asyncio.to_thread(PDFReportGenerator.generate_single_stock_pdf, clean_t)
    return FileResponse(
        path=pdf_filepath,
        filename=f"AINSEPS_{clean_t}_Summary.pdf",
        media_type="application/pdf"
    )


@app.post("/telegram/link-account")
async def link_telegram_account(req: TelegramLinkRequest):
    """
    Links a user's Telegram phone number or account ID from the Web App frontend to MongoDB.
    """
    phone = req.phone_or_account.strip()
    chat_id = req.chat_id or hash(phone) % 100000000
    user_doc = db_service.get_or_create_user(chat_id, username=phone, full_name=f"User ({phone})")
    
    if req.stocks:
        for st in req.stocks:
            db_service.add_to_watchlist(chat_id, st)

    # If active bot instance, notify
    if bot_instance and bot_instance.running and req.chat_id:
        asyncio.create_task(
            bot_instance.send_message(
                req.chat_id,
                f"✅ <b>Telegram Account Linked Successfully!</b>\nPhone/Account: <b>{phone}</b>\nYour website portfolio and alerts are now synced!"
            )
        )

    return {
        "status": "linked",
        "phone_or_account": phone,
        "chat_id": chat_id,
        "message": "Telegram account linked successfully to AINSEPS system."
    }




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
