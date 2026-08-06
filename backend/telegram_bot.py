import os
import json
import asyncio
import logging
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from backend.agents.graph import StockPredictorGraph
from backend.agents.sentiment_agent import SentimentAgent
from backend.services.data_fetcher import DataFetcher
from backend.services.news_scraper import NewsScraper
from backend.services.predictor_service import get_predictor
from backend.services.db_service import db_service
from backend.services.news_summary_service import NewsSummaryService
from backend.services.pdf_generator import PDFReportGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TelegramBot")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8561210253:AAGKMYF8JAepMsD47j3OdY3bYmoGQhNZwhs")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

# Path for persisting price warning alerts
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ALERTS_FILE = os.path.join(DATA_DIR, "alerts.json")

os.makedirs(DATA_DIR, exist_ok=True)

# Ticker shortcuts for keyboard — ONLY these 4 stocks are allowed
POPULAR_STOCKS = ["RELIANCE", "HDFCBANK", "INFY", "TATASTEEL"]
ALLOWED_STOCKS = set(POPULAR_STOCKS)

def _is_allowed(ticker: str) -> bool:
    """Returns True if the ticker is one of the 4 allowed stocks."""
    return ticker.upper().replace(".NS", "").replace(".BO", "") in ALLOWED_STOCKS

INVALID_STOCK_MSG = (
    "❌ <b>Stock not supported.</b>\n\n"
    "This bot only supports the following stocks:\n"
    "• 🇮🇳 <b>RELIANCE</b> — Reliance Industries\n"
    "• 🇮🇳 <b>HDFCBANK</b> — HDFC Bank\n"
    "• 🇮🇳 <b>INFY</b> — Infosys Ltd\n"
    "• 🇮🇳 <b>TATASTEEL</b> — Tata Steel\n\n"
    "Please select one of these stocks."
)

# User session state to remember current ticker per chat
USER_TICKERS: Dict[int, str] = {}
# Scraped news cache for article summary clicks
ARTICLE_CACHE: Dict[str, List[Dict]] = {}


# ── Alert Persistence Helper Functions ──────────────────────────────────────
def load_alerts() -> List[Dict]:
    """Loads saved price alerts from JSON file."""
    if not os.path.exists(ALERTS_FILE):
        return []
    try:
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading alerts.json: {e}")
        return []

def save_alerts(alerts: List[Dict]):
    """Saves price alerts to JSON file."""
    try:
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(alerts, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing to alerts.json: {e}")

def add_alert(chat_id: int, ticker: str, target_price: float) -> Dict:
    """Adds or updates a price fall alert threshold for a user."""
    alerts = load_alerts()
    ticker_clean = ticker.upper().replace(".NS", "").replace(".BO", "")
    
    alerts = [a for a in alerts if not (a["chat_id"] == chat_id and a["ticker"] == ticker_clean)]
    
    alert_item = {
        "chat_id": chat_id,
        "ticker": ticker_clean,
        "target_price": round(target_price, 2),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "triggered": False,
        "last_notified_price": None,
    }
    alerts.append(alert_item)
    save_alerts(alerts)
    return alert_item

def remove_alert(chat_id: int, ticker: str) -> bool:
    """Removes an alert for a specific user and ticker."""
    alerts = load_alerts()
    ticker_clean = ticker.upper().replace(".NS", "").replace(".BO", "")
    initial_count = len(alerts)
    alerts = [a for a in alerts if not (a["chat_id"] == chat_id and a["ticker"] == ticker_clean)]
    if len(alerts) < initial_count:
        save_alerts(alerts)
        return True
    return False

def get_user_alerts(chat_id: int) -> List[Dict]:
    """Gets all active alerts set by a user."""
    alerts = load_alerts()
    return [a for a in alerts if a["chat_id"] == chat_id]


class TelegramBot:
    def __init__(self, token: str = TOKEN):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.client: Optional[httpx.AsyncClient] = None
        self.running = False
        self.graph = StockPredictorGraph()
        self.monitor_task: Optional[asyncio.Task] = None
        self.pdf_task: Optional[asyncio.Task] = None

    async def start(self):
        """Starts the bot polling loop, price alert monitor, and daily PDF dispatcher."""
        self.client = httpx.AsyncClient(timeout=30.0)
        self.running = True

        # Verify token
        bot_info = await self._call_api("getMe")
        if not bot_info or not bot_info.get("ok"):
            logger.error(f"Failed to connect to Telegram API with token {self.token}")
            return
        
        bot_user = bot_info.get("result", {})
        logger.info(f"Bot connected successfully as @{bot_user.get('username')} ({bot_user.get('first_name')})")

        # Set default bot commands in Telegram UI
        commands = [
            {"command": "start", "description": "Welcome & Main Menu"},
            {"command": "help", "description": "Guide & Bot commands"},
            {"command": "portfolio", "description": "View & manage your stock watchlist"},
            {"command": "watch", "description": "Add stock to portfolio (<ticker>)"},
            {"command": "unwatch", "description": "Remove stock from portfolio (<ticker>)"},
            {"command": "pdf", "description": "Generate & download Daily PDF Stock Report"},
            {"command": "agent", "description": "Run AI Multi-Agent analysis (<ticker>)"},
            {"command": "alert", "description": "Set price drop warning (<ticker> <limit>)"},
            {"command": "alerts", "description": "View & manage active price alerts"},
            {"command": "news", "description": "News summary, Impact Rating & Direction"},
            {"command": "forecast", "description": "30-Day XGBoost price forecast (<ticker>)"},
            {"command": "stock", "description": "Live stock quote (<ticker>)"},
        ]
        await self._call_api("setMyCommands", json={"commands": commands})

        # Start background tasks
        self.monitor_task = asyncio.create_task(self._run_alert_monitor())
        self.pdf_task = asyncio.create_task(self._run_daily_pdf_dispatcher())

        offset = 0
        logger.info("Starting long polling loop...")
        while self.running:
            try:
                updates_resp = await self._call_api("getUpdates", json={"offset": offset, "timeout": 20})
                if updates_resp and updates_resp.get("ok"):
                    for update in updates_resp.get("result", []):
                        offset = max(offset, update["update_id"] + 1)
                        asyncio.create_task(self.handle_update(update))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(3)

    async def stop(self):
        """Stops the bot polling loop and monitor tasks."""
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
        if self.pdf_task:
            self.pdf_task.cancel()
        if self.client:
            await self.client.aclose()

    async def _call_api(self, method: str, json: dict = None) -> dict:
        """Helper to call Telegram API."""
        try:
            resp = await self.client.post(f"{self.api_url}/{method}", json=json)
            return resp.json()
        except Exception as e:
            logger.error(f"Telegram API call error ({method}): {e}")
            return {}

    async def send_typing(self, chat_id: int):
        """Sends 'typing' chat action to Telegram."""
        await self._call_api("sendChatAction", json={"chat_id": chat_id, "action": "typing"})

    async def send_message(self, chat_id: int, text: str, reply_markup: dict = None):
        """Sends HTML formatted message to Telegram."""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self._call_api("sendMessage", json=payload)

    async def send_document(self, chat_id: int, filepath: str, caption: str = ""):
        """Sends a PDF file document to Telegram chat."""
        try:
            filename = os.path.basename(filepath)
            with open(filepath, "rb") as f:
                files = {"document": (filename, f, "application/pdf")}
                data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
                resp = await self.client.post(f"{self.api_url}/sendDocument", data=data, files=files)
                return resp.json()
        except Exception as e:
            logger.error(f"Error sending PDF document to Telegram: {e}")
            return {}

    def _get_main_keyboard(self, selected_ticker: str = None) -> dict:
        """Builds main inline keyboard menu."""
        ticker = selected_ticker or "RELIANCE"
        keyboard = [
            [
                {"text": f"🇮🇳 RELIANCE", "callback_data": "select:RELIANCE"},
                {"text": f"🇮🇳 HDFCBANK", "callback_data": "select:HDFCBANK"},
            ],
            [
                {"text": f"🇮🇳 INFY", "callback_data": "select:INFY"},
                {"text": f"🇮🇳 TATASTEEL", "callback_data": "select:TATASTEEL"},
            ],
            [
                {"text": f"🤖 Run Agent ({ticker})", "callback_data": f"agent:{ticker}"},
                {"text": f"📰 News & Impact ({ticker})", "callback_data": f"news:{ticker}"},
            ],
            [
                {"text": f"📈 30d Forecast ({ticker})", "callback_data": f"forecast:{ticker}"},
                {"text": f"📊 Quote ({ticker})", "callback_data": f"stock:{ticker}"},
            ],
            [
                {"text": "💼 Portfolio / Watchlist", "callback_data": "portfolio"},
                {"text": "📄 Download Daily PDF", "callback_data": "generate_pdf"},
            ],
            [
                {"text": f"⚠️ Set Alert ({ticker})", "callback_data": f"setalert_prompt:{ticker}"},
                {"text": "📋 My Price Alerts", "callback_data": "myalerts"},
            ],
        ]
        return {"inline_keyboard": keyboard}

    def _get_action_keyboard(self, ticker: str) -> dict:
        """Builds action keyboard for a specific stock."""
        keyboard = [
            [
                {"text": "🤖 Run AI Agent", "callback_data": f"agent:{ticker}"},
                {"text": "📰 News & Impact", "callback_data": f"news:{ticker}"},
            ],
            [
                {"text": "📈 30-Day Forecast", "callback_data": f"forecast:{ticker}"},
                {"text": "📊 Live Quote", "callback_data": f"stock:{ticker}"},
            ],
            [
                {"text": f"➕ Add {ticker} to Portfolio", "callback_data": f"addwatch:{ticker}"},
                {"text": "💼 My Portfolio", "callback_data": "portfolio"},
            ],
            [
                {"text": f"⚠️ Set Price Alert", "callback_data": f"setalert_prompt:{ticker}"},
                {"text": "📄 Daily PDF Report", "callback_data": "generate_pdf"},
            ],
            [
                {"text": "🔙 Main Menu", "callback_data": "menu"},
            ],
        ]
        return {"inline_keyboard": keyboard}

    async def handle_update(self, update: dict):
        """Dispatches incoming Telegram updates."""
        if "message" in update:
            await self.handle_message(update["message"])
        elif "callback_query" in update:
            await self.handle_callback(update["callback_query"])

    async def handle_message(self, message: dict):
        chat_id = message["chat"]["id"]
        from_user = message.get("from", {})
        username = from_user.get("username", "")
        full_name = f"{from_user.get('first_name', '')} {from_user.get('last_name', '')}".strip()

        # Save user account to MongoDB Atlas
        await asyncio.to_thread(db_service.get_or_create_user, chat_id, username, full_name)

        text = message.get("text", "").strip()
        if not text:
            return

        if text.startswith("/start") or text.startswith("/menu") or text.startswith("/help"):
            current = USER_TICKERS.get(chat_id, "RELIANCE")
            welcome_msg = (
                "🚀 <b>Welcome to AINSEPS AI Stock Bot!</b>\n\n"
                "I am your multi-agent AI stock research, forecasting, news impact & PDF report assistant.\n\n"
                "<b>📌 Available Commands:</b>\n"
                "• 💼 <code>/portfolio</code> - View & Manage Stock Watchlist\n"
                "• 📄 <code>/pdf</code> - Generate & Download Daily PDF Report\n"
                "• 🤖 <code>/agent &lt;ticker&gt;</code> - Run Multi-Agent AI Analysis\n"
                "• ⚠️ <code>/alert &lt;ticker&gt; &lt;limit_price&gt;</code> - Set Price Warning Alert\n"
                "• 📰 <code>/news &lt;ticker&gt;</code> - Scraped News with Impact Rating & Direction\n"
                "• 📈 <code>/forecast &lt;ticker&gt;</code> - 30-Day XGBoost Forecast\n"
                "• 📊 <code>/stock &lt;ticker&gt;</code> - Real-time Stock Quote\n\n"
                "<b>Supported Stocks:</b> RELIANCE, HDFCBANK, INFY, TATASTEEL\n"
                "👇 <b>Select a stock below:</b>"
            )
            await self.send_message(chat_id, welcome_msg, self._get_main_keyboard(current))
            return

        parts = text.split(maxsplit=2)
        cmd = parts[0].lower()

        # Watchlist commands: /watch <ticker>, /unwatch <ticker>, /portfolio
        if cmd in ["/watch", "/addwatch", "/addstock"]:
            ticker = parts[1].upper() if len(parts) > 1 else USER_TICKERS.get(chat_id, "RELIANCE")
            if not _is_allowed(ticker):
                await self.send_message(chat_id, INVALID_STOCK_MSG, self._get_main_keyboard())
                return
            watchlist = await asyncio.to_thread(db_service.add_to_watchlist, chat_id, ticker)
            await self.send_message(
                chat_id,
                f"✅ Added <b>{ticker.upper()}</b> to your MongoDB account portfolio!\n\n"
                f"💼 <b>Your Current Watchlist ({len(watchlist)} stocks):</b> {', '.join(watchlist)}"
            )
            await self.show_portfolio(chat_id)
            return

        if cmd in ["/unwatch", "/delstock", "/removewatch"]:
            ticker = parts[1].upper() if len(parts) > 1 else USER_TICKERS.get(chat_id)
            if ticker:
                watchlist = await asyncio.to_thread(db_service.remove_from_watchlist, chat_id, ticker)
                await self.send_message(
                    chat_id,
                    f"🗑️ Removed <b>{ticker.upper()}</b> from your account portfolio.\n\n"
                    f"💼 <b>Your Current Watchlist ({len(watchlist)} stocks):</b> {', '.join(watchlist) if watchlist else 'Empty'}"
                )
            else:
                await self.send_message(chat_id, "Usage: <code>/unwatch INFY</code>")
            return

        if cmd in ["/portfolio", "/watchlist", "/myportfolio", "/mywatchlist"]:
            await self.show_portfolio(chat_id)
            return

        # Daily PDF command: /pdf, /report
        if cmd in ["/pdf", "/report", "/dailyreport", "/pdfreport"]:
            await self.run_pdf_command(chat_id)
            return

        # Alert commands
        if cmd in ["/alert", "/setalert", "/warn"]:
            if len(parts) == 3:
                ticker = parts[1].upper()
                if not _is_allowed(ticker):
                    await self.send_message(chat_id, INVALID_STOCK_MSG, self._get_main_keyboard())
                    return
                try:
                    price_val = float(parts[2].replace("₹", "").replace("$", "").replace(",", ""))
                    await self.set_alert_command(chat_id, ticker, price_val)
                    return
                except ValueError:
                    await self.send_message(chat_id, "❌ Invalid price threshold. Usage: <code>/alert RELIANCE 2850</code>")
                    return
            elif len(parts) == 2:
                ticker = USER_TICKERS.get(chat_id, "RELIANCE")
                try:
                    price_val = float(parts[1].replace("₹", "").replace("$", "").replace(",", ""))
                    await self.set_alert_command(chat_id, ticker, price_val)
                    return
                except ValueError:
                    ticker = parts[1].upper()
                    await self.send_message(
                        chat_id,
                        f"⚠️ To set price alert for <b>{ticker}</b>, enter the threshold price:\nUsage: <code>/alert {ticker} 2850</code>"
                    )
                    return
            else:
                ticker = USER_TICKERS.get(chat_id, "RELIANCE")
                await self.send_message(
                    chat_id,
                    f"⚠️ <b>Set Price Fall Warning Alert</b>\n\nUsage: <code>/alert {ticker} 2850</code>\n\n"
                    f"If <b>{ticker}</b> falls below your limit, you will get an instant Telegram warning notification!"
                )
                return

        if cmd in ["/alerts", "/myalerts", "/listalerts"]:
            await self.show_user_alerts(chat_id)
            return

        if cmd in ["/delalert", "/removealert", "/deletealert"]:
            ticker = parts[1].upper() if len(parts) > 1 else USER_TICKERS.get(chat_id)
            if ticker:
                removed = remove_alert(chat_id, ticker)
                if removed:
                    await self.send_message(chat_id, f"✅ Alert for <b>{ticker}</b> removed successfully.")
                else:
                    await self.send_message(chat_id, f"ℹ️ No active alert found for <b>{ticker}</b>.")
            else:
                await self.send_message(chat_id, "Usage: <code>/delalert RELIANCE</code>")
            return

        if cmd in ["/agent", "/predict"]:
            ticker = parts[1].strip().upper() if len(parts) > 1 else USER_TICKERS.get(chat_id, "RELIANCE")
            if not _is_allowed(ticker):
                await self.send_message(chat_id, INVALID_STOCK_MSG, self._get_main_keyboard())
                return
            await self.run_agent_command(chat_id, ticker)
            return

        if cmd == "/news":
            ticker = parts[1].strip().upper() if len(parts) > 1 else USER_TICKERS.get(chat_id, "RELIANCE")
            if not _is_allowed(ticker):
                await self.send_message(chat_id, INVALID_STOCK_MSG, self._get_main_keyboard())
                return
            await self.run_news_command(chat_id, ticker)
            return

        if cmd in ["/forecast", "/predict_price"]:
            ticker = parts[1].strip().upper() if len(parts) > 1 else USER_TICKERS.get(chat_id, "RELIANCE")
            if not _is_allowed(ticker):
                await self.send_message(chat_id, INVALID_STOCK_MSG, self._get_main_keyboard())
                return
            await self.run_forecast_command(chat_id, ticker)
            return

        if cmd in ["/stock", "/quote", "/price"]:
            ticker = parts[1].strip().upper() if len(parts) > 1 else USER_TICKERS.get(chat_id, "RELIANCE")
            if not _is_allowed(ticker):
                await self.send_message(chat_id, INVALID_STOCK_MSG, self._get_main_keyboard())
                return
            await self.run_stock_command(chat_id, ticker)
            return

        # Plain stock symbol typed by user — only allow supported stocks
        clean_text = text.upper().replace(".NS", "").replace(".BO", "")
        if len(clean_text) <= 12 and clean_text.isalnum():
            if not _is_allowed(clean_text):
                await self.send_message(chat_id, INVALID_STOCK_MSG, self._get_main_keyboard())
                return
            USER_TICKERS[chat_id] = clean_text
            msg = (
                f"📈 <b>Stock Selected: {clean_text}</b>\n\n"
                f"What analysis, news summary, or alert would you like for <b>{clean_text}</b>?"
            )
            await self.send_message(chat_id, msg, self._get_action_keyboard(clean_text))
            return

        # Default fallback
        await self.send_message(
            chat_id,
            "❓ Unrecognized command. Type <b>/start</b> for menu or <b>/portfolio</b> to manage your stock watchlist."
        )

    async def handle_callback(self, callback: dict):
        chat_id = callback["message"]["chat"]["id"]
        cb_id = callback["id"]
        data = callback.get("data", "")

        await self._call_api("answerCallbackQuery", json={"callback_query_id": cb_id})

        if data == "menu":
            current = USER_TICKERS.get(chat_id, "RELIANCE")
            await self.send_message(
                chat_id,
                "📊 <b>Main Menu - Select Stock or Action:</b>",
                self._get_main_keyboard(current)
            )
            return

        if data == "portfolio":
            await self.show_portfolio(chat_id)
            return

        if data == "generate_pdf":
            await self.run_pdf_command(chat_id)
            return

        if data.startswith("addwatch:"):
            _, ticker = data.split(":", 1)
            watchlist = await asyncio.to_thread(db_service.add_to_watchlist, chat_id, ticker)
            await self.send_message(chat_id, f"✅ Added <b>{ticker}</b> to your MongoDB account portfolio!")
            await self.show_portfolio(chat_id)
            return

        if data.startswith("delwatch:"):
            _, ticker = data.split(":", 1)
            watchlist = await asyncio.to_thread(db_service.remove_from_watchlist, chat_id, ticker)
            await self.send_message(chat_id, f"🗑️ Removed <b>{ticker}</b> from portfolio.")
            await self.show_portfolio(chat_id)
            return

        if data.startswith("sum:"):
            # Deep summary click for news article: format sum:TICKER:INDEX
            parts = data.split(":")
            if len(parts) == 3:
                tk = parts[1]
                idx = int(parts[2])
                articles = ARTICLE_CACHE.get(f"{chat_id}_{tk}", [])
                if 0 <= idx < len(articles):
                    art = articles[idx]
                    analysis = NewsSummaryService.analyze_news_item(art, tk)

                    summary_txt = (
                        f"📰 <b>Executive News Summary: {tk.upper()}</b>\n\n"
                        f"<b>Title:</b> {analysis['title']}\n"
                        f"<b>Source:</b> {analysis['source']}\n\n"
                        f"⚡ <b>Impact Rating:</b> {analysis['impact_badge']} <b>{analysis['impact_rating']}</b>\n"
                        f"{analysis['direction_emoji']} <b>Stock Trend Prediction:</b> <b>{analysis['direction']}</b>\n"
                        f"🎯 <b>AI Confidence Score:</b> {analysis['confidence']}%\n\n"
                        f"<b>💡 Key Driver Analysis:</b>\n"
                        f"• {analysis['summary_bullets'][0]}\n"
                        f"• {analysis['summary_bullets'][1]}\n"
                        f"• {analysis['summary_bullets'][2]}\n\n"
                        f"🔗 <a href='{analysis['url']}'>Read Full Article Source</a>"
                    )
                    await self.send_message(chat_id, summary_txt, self._get_action_keyboard(tk))
                    return

        if data == "myalerts":
            await self.show_user_alerts(chat_id)
            return

        if data.startswith("delalert:"):
            _, ticker = data.split(":", 1)
            remove_alert(chat_id, ticker)
            await self.send_message(chat_id, f"🗑️ Alert for <b>{ticker}</b> has been deleted.")
            await self.show_user_alerts(chat_id)
            return

        if data.startswith("setalert_prompt:"):
            _, ticker = data.split(":", 1)
            USER_TICKERS[chat_id] = ticker
            price = await asyncio.to_thread(DataFetcher.get_realtime_price, ticker)
            suggested = round(price * 0.95, 2) if price > 0 else 1000.0
            msg = (
                f"⚠️ <b>Set Price Fall Warning for {ticker}</b>\n\n"
                f"Current Price: <b>₹{price:,.2f}</b>\n\n"
                f"To set a price warning alert, reply with the limit price command:\n"
                f"<code>/alert {ticker} {suggested:.0f}</code>"
            )
            await self.send_message(chat_id, msg)
            return

        if ":" in data:
            action, ticker = data.split(":", 1)
            ticker = ticker.upper()
            USER_TICKERS[chat_id] = ticker

            if action == "select":
                msg = (
                    f"🎯 <b>Selected Ticker: {ticker}</b>\n\n"
                    f"Choose an action below for <b>{ticker}</b>:"
                )
                await self.send_message(chat_id, msg, self._get_action_keyboard(ticker))
            elif action == "agent":
                await self.run_agent_command(chat_id, ticker)
            elif action == "news":
                await self.run_news_command(chat_id, ticker)
            elif action == "forecast":
                await self.run_forecast_command(chat_id, ticker)
            elif action == "stock":
                await self.run_stock_command(chat_id, ticker)

    # ── Portfolio & Watchlist Commands ──────────────────────────────────────
    async def show_portfolio(self, chat_id: int):
        """Displays user's stock watchlist stored in MongoDB."""
        watchlist = await asyncio.to_thread(db_service.get_user_watchlist, chat_id)
        if not watchlist:
            msg = (
                "💼 <b>Your Stock Portfolio & Watchlist</b>\n\n"
                "<i>Your watchlist is currently empty.</i>\n\n"
                "Add stocks to your portfolio using: <code>/watch RELIANCE</code> or click below:"
            )
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "🇮🇳 Add RELIANCE", "callback_data": "addwatch:RELIANCE"},
                        {"text": "🇮🇳 Add HDFCBANK", "callback_data": "addwatch:HDFCBANK"},
                    ],
                    [
                        {"text": "🇮🇳 Add INFY", "callback_data": "addwatch:INFY"},
                        {"text": "🇮🇳 Add TATASTEEL", "callback_data": "addwatch:TATASTEEL"},
                    ],
                    [{"text": "🔙 Main Menu", "callback_data": "menu"}],
                ]
            }
            await self.send_message(chat_id, msg, keyboard)
            return

        lines = [f"💼 <b>Your Account Portfolio & Watchlist ({len(watchlist)} Stocks):</b>\n"]
        buttons = []

        for ticker in watchlist:
            price = await asyncio.to_thread(DataFetcher.get_realtime_price, ticker)
            lines.append(f"• <b>{ticker}</b>: ₹{price:,.2f}")
            buttons.append([
                {"text": f"🤖 Agent ({ticker})", "callback_data": f"agent:{ticker}"},
                {"text": f"📰 News ({ticker})", "callback_data": f"news:{ticker}"},
                {"text": f"❌ Remove", "callback_data": f"delwatch:{ticker}"},
            ])

        buttons.append([{"text": "📄 Download Daily PDF Report", "callback_data": "generate_pdf"}])
        buttons.append([{"text": "🔙 Main Menu", "callback_data": "menu"}])

        lines.append("\n<i>These stocks are tracked for your Daily PDF Report dispatch!</i>")
        text = "\n".join(lines)
        await self.send_message(chat_id, text, {"inline_keyboard": buttons})

    # ── Daily PDF Report Generation ─────────────────────────────────────────
    async def run_pdf_command(self, chat_id: int):
        """Generates and sends the daily PDF report for user's portfolio."""
        await self.send_typing(chat_id)
        watchlist = await asyncio.to_thread(db_service.get_user_watchlist, chat_id)
        user_doc = await asyncio.to_thread(db_service.get_or_create_user, chat_id)
        user_name = user_doc.get("full_name") or user_doc.get("username") or "Valued Investor"

        status_msg = await self.send_message(
            chat_id,
            f"📄 <b>Generating Daily Stock Intelligence PDF Report for your portfolio ({', '.join(watchlist)})...</b>\n"
            f"<i>Compiling AI multi-agent recommendations, ML 30-day forecasts, and news impact ratings...</i>"
        )

        try:
            pdf_path = await asyncio.to_thread(
                PDFReportGenerator.generate_daily_pdf, chat_id, user_name, watchlist
            )

            caption = (
                f"📊 <b>AINSEPS Daily Stock Intelligence Report</b>\n\n"
                f"👤 <b>Account:</b> {user_name}\n"
                f"📅 <b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}\n"
                f"📈 <b>Portfolio Stocks:</b> {', '.join(watchlist)}\n\n"
                f"<i>Here is your formatted PDF report containing AI predictions, agent signals, and news impact analysis!</i>"
            )

            await self.send_document(chat_id, pdf_path, caption)
        except Exception as e:
            logger.error(f"Error generating PDF report for {chat_id}: {e}")
            await self.send_message(chat_id, f"❌ Failed to generate PDF report. Error: {e}")

    async def _run_daily_pdf_dispatcher(self):
        """
        Background loop to automatically dispatch updated daily PDF reports
        to every registered MongoDB account every morning.
        """
        logger.info("Daily PDF Dispatcher scheduler running...")
        while self.running:
            try:
                # Runs once every 24 hours (86400s)
                await asyncio.sleep(86400)
                users = await asyncio.to_thread(db_service.get_all_users)
                for u in users:
                    c_id = u.get("chat_id")
                    u_name = u.get("full_name") or u.get("username") or "Investor"
                    w_list = u.get("watchlist", ["RELIANCE", "INFY"])

                    if c_id:
                        try:
                            pdf_p = await asyncio.to_thread(PDFReportGenerator.generate_daily_pdf, c_id, u_name, w_list)
                            cap = f"🌅 <b>Good Morning! Here is your Daily Stock Intelligence PDF Report for {datetime.now().strftime('%Y-%m-%d')}</b>"
                            await self.send_document(c_id, pdf_p, cap)
                        except Exception as ex:
                            logger.error(f"Failed to dispatch daily PDF to {c_id}: {ex}")
            except Exception as e:
                logger.error(f"Error in daily PDF dispatcher loop: {e}")
                await asyncio.sleep(3600)

    # ── Alert Commands & Background Monitoring Engine ────────────────────────
    async def set_alert_command(self, chat_id: int, ticker: str, target_price: float):
        """Sets a price fall alert for user."""
        USER_TICKERS[chat_id] = ticker
        item = add_alert(chat_id, ticker, target_price)

        current_price = await asyncio.to_thread(DataFetcher.get_realtime_price, ticker)

        msg = (
            f"✅ <b>Price Fall Alert Set for {ticker.upper()}!</b>\n\n"
            f"💰 <b>Current Market Price:</b> ₹{current_price:,.2f}\n"
            f"⚠️ <b>Warning Threshold Limit:</b> ₹{target_price:,.2f}\n\n"
            f"📢 If <b>{ticker.upper()}</b> drops to or below ₹{target_price:,.2f}, I will send you an instant warning alert message on Telegram!\n\n"
            f"<i>Type /alerts anytime to view or remove your active alerts.</i>"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "📋 My Active Alerts", "callback_data": "myalerts"}],
                [{"text": f"🗑️ Remove Alert for {ticker}", "callback_data": f"delalert:{ticker}"}],
                [{"text": "🔙 Main Menu", "callback_data": "menu"}],
            ]
        }
        await self.send_message(chat_id, msg, keyboard)

    async def show_user_alerts(self, chat_id: int):
        """Displays user's active price fall warning alerts."""
        alerts = get_user_alerts(chat_id)
        if not alerts:
            msg = (
                "📋 <b>Your Price Alerts</b>\n\n"
                "<i>You currently have no active price fall warning alerts.</i>\n\n"
                "To set a new warning alert, use: <code>/alert RELIANCE 2850</code>"
            )
            await self.send_message(chat_id, msg, self._get_main_keyboard())
            return

        lines = ["📋 <b>Your Active Price Fall Warning Alerts:</b>\n"]
        buttons = []
        for a in alerts:
            ticker = a["ticker"]
            limit = a["target_price"]
            status = "🚨 TRIGGERED" if a.get("triggered") else "🟢 ACTIVE MONITORING"

            lines.append(f"• <b>{ticker}</b>: Below ₹{limit:,.2f} ({status})")
            buttons.append([{"text": f"🗑️ Delete {ticker} (₹{limit:,.2f})", "callback_data": f"delalert:{ticker}"}])

        buttons.append([{"text": "🔙 Main Menu", "callback_data": "menu"}])
        text = "\n".join(lines)
        await self.send_message(chat_id, text, {"inline_keyboard": buttons})

    async def _run_alert_monitor(self):
        """
        Background monitoring task:
        Checks market prices for active alerts and sends automated warning notifications.
        """
        logger.info("Price Warning Alert Monitor loop started.")
        while self.running:
            try:
                alerts = load_alerts()
                if alerts:
                    updated = False
                    for alert in alerts:
                        chat_id = alert["chat_id"]
                        ticker = alert["ticker"]
                        target_price = alert["target_price"]
                        triggered = alert.get("triggered", False)

                        curr_price = await asyncio.to_thread(DataFetcher.get_realtime_price, ticker)
                        if curr_price <= 0:
                            continue

                        if curr_price <= target_price and not triggered:
                            fall_amount = target_price - curr_price
                            fall_pct = (fall_amount / target_price * 100) if target_price > 0 else 0.0

                            pred_note = ""
                            try:
                                svc = get_predictor(ticker)
                                res = await asyncio.to_thread(svc.get_full_series, ticker, 15)
                                predicted_series = [p for p in res.get("series", []) if p.get("type") == "predicted"]
                                if predicted_series:
                                    fut_price = predicted_series[-1]["price"]
                                    fut_chg = ((fut_price - curr_price) / curr_price) * 100
                                    pred_note = f"\n🤖 <b>30-Day ML Prediction:</b> Projected price ₹{fut_price:,.2f} ({fut_chg:+.2f}%)"
                            except Exception:
                                pass

                            warning_text = (
                                f"🚨 <b>WARNING: STOCK PRICE FALL ALERT!</b> 🚨\n\n"
                                f"📈 <b>Stock Ticker:</b> {ticker.upper()}\n"
                                f"⚠️ <b>Set Alert Limit:</b> ₹{target_price:,.2f}\n"
                                f"💰 <b>Current Market Price:</b> ₹{curr_price:,.2f}\n"
                                f"📉 <b>Fall Amount:</b> ₹{fall_amount:,.2f} ({fall_pct:.2f}% below threshold){pred_note}\n\n"
                                f"⚡ <b>WARNING:</b> The stock has fallen below your set limit! Inspect AI risk metrics or run an AI Agent report now."
                            )

                            keyboard = {
                                "inline_keyboard": [
                                    [
                                        {"text": f"🤖 Run AI Agent ({ticker})", "callback_data": f"agent:{ticker}"},
                                        {"text": f"📊 Live Quote ({ticker})", "callback_data": f"stock:{ticker}"},
                                    ],
                                    [
                                        {"text": f"🗑️ Remove Alert", "callback_data": f"delalert:{ticker}"},
                                        {"text": "📋 My Alerts", "callback_data": "myalerts"},
                                    ],
                                ]
                            }

                            logger.info(f"Triggering price alert for chat_id={chat_id}, ticker={ticker}, price={curr_price}")
                            await self.send_message(chat_id, warning_text, keyboard)

                            alert["triggered"] = True
                            alert["last_notified_price"] = curr_price
                            updated = True

                    if updated:
                        save_alerts(alerts)

            except Exception as e:
                logger.error(f"Error in price alert monitor: {e}")

            await asyncio.sleep(120)

    # ── Command Implementations ──────────────────────────────────────────────
    async def run_agent_command(self, chat_id: int, ticker: str):
        """Runs the multi-agent prediction graph."""
        USER_TICKERS[chat_id] = ticker
        await self.send_typing(chat_id)
        await self.send_message(
            chat_id, f"⏳ <b>Running AI Multi-Agent graph for {ticker}...</b>\n<i>Analyzing Technicals, Scraped News, and Risk Model...</i>"
        )

        try:
            res = await asyncio.to_thread(self.graph.run, ticker)
            final = res.get("final_output", {})

            rec = final.get("recommendation", "N/A")
            summary = final.get("summary", {})
            levels = final.get("levels", {})

            rec_emoji = "🟢" if "BUY" in rec.upper() else ("🔴" if "SELL" in rec.upper() else "🟡")

            tech_sig = summary.get("technical", "N/A")
            sent_sig = summary.get("sentiment", "N/A")
            sent_score = summary.get("sentiment_score", 0.0)
            risk_assess = summary.get("risk_assessment", "N/A")
            art_count = summary.get("articles_analysed", 0)

            entry = levels.get("entry", 0.0)
            sl = levels.get("stop_loss", 0.0)
            tp = levels.get("take_profit", 0.0)

            text = (
                f"🤖 <b>AI Multi-Agent Report for {ticker.upper()}</b>\n\n"
                f"🎯 <b>Recommendation:</b> {rec_emoji} <b>{rec}</b>\n\n"
                f"<b>📊 Agent Analysis Breakdown:</b>\n"
                f"• <b>Technical Signal:</b> {tech_sig}\n"
                f"• <b>Sentiment Score:</b> {sent_score:+.2f} ({sent_sig})\n"
                f"• <b>News Analysed:</b> {art_count} articles\n"
                f"• <b>Risk Assessment:</b> {risk_assess}\n\n"
                f"<b>💰 Target Price Levels:</b>\n"
                f"• <b>Entry Price:</b> ₹{entry:,.2f}\n"
                f"• <b>Stop Loss:</b> ₹{sl:,.2f}\n"
                f"• <b>Take Profit:</b> ₹{tp:,.2f}\n\n"
                f"⚡ <i>Engine: LangGraph Multi-Agent Architecture</i>"
            )

            await self.send_message(chat_id, text, self._get_action_keyboard(ticker))
        except Exception as e:
            logger.error(f"Error running agent for {ticker}: {e}")
            await self.send_message(chat_id, f"❌ Failed to run AI agent for <b>{ticker}</b>. Error: {e}")

    async def run_news_command(self, chat_id: int, ticker: str):
        """Scrapes live news & presents Impact Ratings & Direction Predictions."""
        USER_TICKERS[chat_id] = ticker
        await self.send_typing(chat_id)
        await self.send_message(chat_id, f"⏳ <b>Scraping news & computing Impact Ratings & Stock Direction for {ticker}...</b>")

        try:
            articles = await asyncio.to_thread(SentimentAgent.fetch_news, ticker)
            ARTICLE_CACHE[f"{chat_id}_{ticker.upper()}"] = articles

            lines = [
                f"📰 <b>News Summary & Impact Analysis: {ticker.upper()}</b>\n",
                f"📊 <b>Total Articles Scraped:</b> {len(articles)}\n",
            ]

            buttons = []
            if articles:
                lines.append("<b>💡 Recent Articles with Impact Rating & Direction Prediction:</b>\n")
                for i, a in enumerate(articles[:5]):
                    analysis = NewsSummaryService.analyze_news_item(a, ticker)
                    impact = analysis["impact_rating"]
                    badge = analysis["impact_badge"]
                    direction = analysis["direction"]
                    dir_emoji = analysis["direction_emoji"]

                    lines.append(
                        f"<b>{i+1}.</b> {dir_emoji} <a href='{a.get('url')}'>{a.get('title')[:60]}...</a>\n"
                        f"   └ {badge} <b>{impact}</b> | <b>{direction}</b>"
                    )
                    buttons.append([{"text": f"🔍 Summary #{i+1}: {a.get('title')[:30]}...", "callback_data": f"sum:{ticker.upper()}:{i}"}])
            else:
                lines.append("<i>No recent news articles found.</i>")

            buttons.append([
                {"text": "🤖 Run AI Agent", "callback_data": f"agent:{ticker}"},
                {"text": "📈 30d Forecast", "callback_data": f"forecast:{ticker}"},
            ])
            buttons.append([{"text": "🔙 Main Menu", "callback_data": "menu"}])

            text = "\n".join(lines)
            await self.send_message(chat_id, text, {"inline_keyboard": buttons})
        except Exception as e:
            logger.error(f"Error fetching news for {ticker}: {e}")
            await self.send_message(chat_id, f"❌ Failed to fetch news for <b>{ticker}</b>. Error: {e}")

    async def run_forecast_command(self, chat_id: int, ticker: str):
        """Runs XGBoost 30-day price prediction."""
        USER_TICKERS[chat_id] = ticker
        await self.send_typing(chat_id)
        await self.send_message(chat_id, f"⏳ <b>Training XGBoost model & predicting 30-day price trend for {ticker}...</b>")

        try:
            svc = get_predictor(ticker)
            result = await asyncio.to_thread(svc.get_full_series, ticker, 30)

            accuracy = result.get("accuracy", {})
            series = result.get("series", [])

            historical = [p for p in series if p.get("type") == "historical"]
            predicted = [p for p in series if p.get("type") == "predicted"]

            curr_price = historical[-1]["price"] if historical else 0.0
            target_price = predicted[-1]["price"] if predicted else curr_price

            chg = ((target_price - curr_price) / curr_price * 100) if curr_price > 0 else 0.0
            chg_emoji = "🟢" if chg >= 0 else "🔴"

            price_acc = accuracy.get("price_accuracy", 0.0)
            dir_acc = accuracy.get("direction_accuracy", 0.0)
            split_date = result.get("split_date", "Recent")

            text = (
                f"📈 <b>30-Day XGBoost Forecast: {ticker.upper()}</b>\n\n"
                f"💰 <b>Current Price:</b> ₹{curr_price:,.2f}\n"
                f"🎯 <b>30-Day Projected Price:</b> ₹{target_price:,.2f}\n"
                f"📊 <b>Expected Return:</b> {chg_emoji} <b>{chg:+.2f}%</b>\n\n"
                f"<b>🎯 Back-test Model Metrics:</b>\n"
                f"• <b>Price Accuracy:</b> {price_acc}%\n"
                f"• <b>Direction Accuracy:</b> {dir_acc}%\n"
                f"• <b>Data Split Date:</b> {split_date}\n\n"
                f"⚡ <i>ML Engine: XGBoost Regressor with Anti-Drift Decays</i>"
            )

            await self.send_message(chat_id, text, self._get_action_keyboard(ticker))
        except Exception as e:
            logger.error(f"Error forecasting for {ticker}: {e}")
            await self.send_message(chat_id, f"❌ Failed to run forecast for <b>{ticker}</b>. Error: {e}")

    async def run_stock_command(self, chat_id: int, ticker: str):
        """Fetches live stock quote."""
        USER_TICKERS[chat_id] = ticker
        await self.send_typing(chat_id)

        try:
            df = await asyncio.to_thread(DataFetcher.get_stock_data, ticker, "1mo")
            if df.empty:
                await self.send_message(chat_id, f"❌ No market data found for ticker <b>{ticker}</b>.")
                return

            last_row = df.iloc[-1]
            prev_row = df.iloc[-2] if len(df) > 1 else last_row

            close_price = float(last_row["Close"])
            prev_close = float(prev_row["Close"])
            high_price = float(last_row["High"])
            low_price = float(last_row["Low"])
            volume = int(last_row["Volume"])

            change = close_price - prev_close
            change_pct = (change / prev_close * 100) if prev_close > 0 else 0.0
            emoji = "🟢" if change >= 0 else "🔴"

            text = (
                f"📊 <b>Stock Quote: {ticker.upper()}</b>\n\n"
                f"💰 <b>Close Price:</b> ₹{close_price:,.2f}\n"
                f"📈 <b>Day Change:</b> {emoji} ₹{change:+.2f} ({change_pct:+.2f}%)\n"
                f"🔼 <b>Day High:</b> ₹{high_price:,.2f}\n"
                f"🔽 <b>Day Low:</b> ₹{low_price:,.2f}\n"
                f"📦 <b>Volume:</b> {volume:,}\n\n"
                f"👇 <i>Select an action below to run AI agents or set price alerts:</i>"
            )

            await self.send_message(chat_id, text, self._get_action_keyboard(ticker))
        except Exception as e:
            logger.error(f"Error fetching stock data for {ticker}: {e}")
            await self.send_message(chat_id, f"❌ Failed to fetch quote for <b>{ticker}</b>. Error: {e}")


# Singleton bot instance
bot_instance = TelegramBot()

async def run_bot():
    """Entry point to run Telegram bot asynchronously."""
    await bot_instance.start()

if __name__ == "__main__":
    logger.info("Launching AINSEPS Telegram Bot...")
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
