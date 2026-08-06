import os
import certifi
import pymongo
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("DBService")

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://himanshugoyalarain_db_user:Himanshu@ainesp.mkopbbq.mongodb.net/?appName=ainesp"
)
DB_NAME = "ainesp_db"

class DBService:
    def __init__(self, uri: str = MONGODB_URI):
        self.uri = uri
        self.client: Optional[pymongo.MongoClient] = None
        self.db = None
        self.users_col = None
        self.connected = False
        self._connect()

    def _connect(self):
        try:
            self.client = pymongo.MongoClient(
                self.uri,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=6000
            )
            self.db = self.client[DB_NAME]
            self.users_col = self.db["users"]
            # Ping
            self.client.admin.command('ping')
            self.connected = True
            logger.info("MongoDB Atlas connected successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB Atlas: {e}")
            self.connected = False

    def get_or_create_user(self, chat_id: int, username: str = "", full_name: str = "") -> Dict:
        """Retrieves user profile or creates a new account in MongoDB."""
        default_watchlist = ["RELIANCE", "INFY", "AAPL"]
        if not self.connected or self.users_col is None:
            return {"chat_id": chat_id, "username": username, "full_name": full_name, "watchlist": default_watchlist}

        try:
            user = self.users_col.find_one({"chat_id": chat_id})
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if not user:
                user_doc = {
                    "chat_id": chat_id,
                    "username": username or "",
                    "full_name": full_name or "",
                    "watchlist": default_watchlist,
                    "created_at": now_str,
                    "updated_at": now_str,
                }
                self.users_col.insert_one(user_doc)
                return user_doc
            else:
                # Update last active time & username
                self.users_col.update_one(
                    {"chat_id": chat_id},
                    {"$set": {"updated_at": now_str, "username": username or user.get("username", ""), "full_name": full_name or user.get("full_name", "")}}
                )
                return user
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            return {"chat_id": chat_id, "username": username, "full_name": full_name, "watchlist": default_watchlist}

    def add_to_watchlist(self, chat_id: int, ticker: str) -> List[str]:
        """Adds a stock to user's portfolio watchlist in MongoDB."""
        clean_ticker = ticker.upper().replace(".NS", "").replace(".BO", "")
        if not self.connected or self.users_col is None:
            return [clean_ticker]

        try:
            self.users_col.update_one(
                {"chat_id": chat_id},
                {"$addToSet": {"watchlist": clean_ticker}},
                upsert=True
            )
            user = self.users_col.find_one({"chat_id": chat_id})
            return user.get("watchlist", [clean_ticker]) if user else [clean_ticker]
        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")
            return [clean_ticker]

    def remove_from_watchlist(self, chat_id: int, ticker: str) -> List[str]:
        """Removes a stock from user's portfolio watchlist in MongoDB."""
        clean_ticker = ticker.upper().replace(".NS", "").replace(".BO", "")
        if not self.connected or self.users_col is None:
            return []

        try:
            self.users_col.update_one(
                {"chat_id": chat_id},
                {"$pull": {"watchlist": clean_ticker}}
            )
            user = self.users_col.find_one({"chat_id": chat_id})
            return user.get("watchlist", []) if user else []
        except Exception as e:
            logger.error(f"Error removing from watchlist: {e}")
            return []

    def get_user_watchlist(self, chat_id: int) -> List[str]:
        """Returns list of stock tickers in user's portfolio."""
        if not self.connected or self.users_col is None:
            return ["RELIANCE", "INFY", "AAPL"]

        try:
            user = self.users_col.find_one({"chat_id": chat_id})
            if user and "watchlist" in user and user["watchlist"]:
                return user["watchlist"]
            return ["RELIANCE", "INFY", "AAPL"]
        except Exception as e:
            logger.error(f"Error fetching watchlist: {e}")
            return ["RELIANCE", "INFY", "AAPL"]

    def get_all_users(self) -> List[Dict]:
        """Returns all registered user accounts for daily PDF dispatch."""
        if not self.connected or self.users_col is None:
            return []
        try:
            return list(self.users_col.find({}))
        except Exception as e:
            logger.error(f"Error fetching all users: {e}")
            return []

# Singleton instance
db_service = DBService()
