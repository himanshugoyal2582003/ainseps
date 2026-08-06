import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.telegram_bot import TelegramBot, TOKEN

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AINSEPS-BotRunner")

def main():
    print("=" * 60)
    print(" 🚀 Starting AINSEPS Telegram Bot (t.me/ainsep_bot)...")
    print(f" Token: {TOKEN[:10]}...{TOKEN[-6:]}")
    print(" Features: Select Stock, AI Multi-Agent Run, News Summary, 30d Forecast")
    print(" Press Ctrl+C to stop.")
    print("=" * 60)

    bot = TelegramBot(TOKEN)
    try:
        asyncio.run(bot.start())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping Telegram Bot...")
        asyncio.run(bot.stop())

if __name__ == "__main__":
    main()
