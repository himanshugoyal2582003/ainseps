import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_percentage_error
from typing import Dict, List
from ..services.data_fetcher import DataFetcher


# ── Feature engineering ───────────────────────────────────────────────────────
def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds features from a Close price series.
    TARGET = log_return (log(P_t / P_{t-1}))
    This avoids the flat-line collapse that occurs when predicting raw prices.
    """
    df = df.copy()
    close = df["Close"]

    # Target: log daily return
    df["log_return"] = np.log(close / close.shift(1))

    # Lag returns (not prices — keeps features stationary)
    for lag in [1, 2, 3, 5, 10, 20]:
        df[f"lag_ret_{lag}"] = df["log_return"].shift(lag)

    # Rolling log-return statistics
    df["ret_mean_5"]  = df["log_return"].rolling(5).mean()
    df["ret_mean_20"] = df["log_return"].rolling(20).mean()
    df["ret_std_5"]   = df["log_return"].rolling(5).std()
    df["ret_std_20"]  = df["log_return"].rolling(20).std()

    # Price-level moving averages (normalised as ratio to current price)
    df["ma5_ratio"]  = close.rolling(5).mean()  / close
    df["ma20_ratio"] = close.rolling(20).mean() / close
    df["ma50_ratio"] = close.rolling(50).mean() / close

    # RSI (14)
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / (loss + 1e-9)
    df["rsi"] = (100 - 100 / (1 + rs)) / 100  # normalise to [0,1]

    # MACD histogram (normalised by price)
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd  = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    df["macd_hist"] = (macd - signal) / close

    # Bollinger band width and position
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df["bb_width"] = (2 * bb_std) / (bb_mid + 1e-9)
    df["bb_pos"]   = (close - bb_mid) / (2 * bb_std + 1e-9)

    # Momentum
    df["mom_5"]  = close / close.shift(5)  - 1
    df["mom_20"] = close / close.shift(20) - 1

    return df.dropna()


FEATURE_COLS = [
    "lag_ret_1", "lag_ret_2", "lag_ret_3", "lag_ret_5", "lag_ret_10", "lag_ret_20",
    "ret_mean_5", "ret_mean_20", "ret_std_5", "ret_std_20",
    "ma5_ratio", "ma20_ratio", "ma50_ratio",
    "rsi", "macd_hist", "bb_width", "bb_pos",
    "mom_5", "mom_20",
]
TARGET_COL = "log_return"


class PredictorService:
    """
    XGBoost predictor that models daily log-returns (not raw prices).
    This avoids the flat-line collapse of iterative absolute-price prediction.
    Predictions are converted back to prices via: P_t = P_{t-1} * exp(predicted_return).
    """

    def __init__(self):
        self.model = XGBRegressor(
            n_estimators=600,
            learning_rate=0.03,
            max_depth=4,
            subsample=0.75,
            colsample_bytree=0.75,
            min_child_weight=3,
            reg_lambda=1.5,
            random_state=42,
        )
        self._trained   = False
        self._feat_df   = None   # cached feature df from last train

    # ── Training ──────────────────────────────────────────────────────────────
    def train(self, df: pd.DataFrame) -> None:
        feat_df = _add_features(df)
        X = feat_df[FEATURE_COLS].values
        y = feat_df[TARGET_COL].values
        self.model.fit(X, y, verbose=False)
        self._feat_df = feat_df
        self._trained = True

    # ── Back-test evaluation ──────────────────────────────────────────────────
    def evaluate(self, df: pd.DataFrame, test_days: int = 30) -> Dict:
        feat_df = _add_features(df)
        split   = len(feat_df) - test_days

        X_train = feat_df[FEATURE_COLS].values[:split]
        y_train = feat_df[TARGET_COL].values[:split]
        X_test  = feat_df[FEATURE_COLS].values[split:]
        y_test  = feat_df[TARGET_COL].values[split:]
        dates   = feat_df.index[split:]

        # Temp model for back-test only
        tmp = XGBRegressor(**self.model.get_params())
        tmp.fit(X_train, y_train, verbose=False)
        y_pred_ret = tmp.predict(X_test)

        # Reconstruct prices from returns
        last_train_price = df["Close"].iloc[split]
        actual_prices    = df["Close"].iloc[split : split + test_days].values
        pred_prices      = [last_train_price]
        for r in y_pred_ret:
            pred_prices.append(pred_prices[-1] * np.exp(r))
        pred_prices = np.array(pred_prices[1:])

        mape         = mean_absolute_percentage_error(actual_prices, pred_prices) * 100
        accuracy     = max(0.0, round(100 - mape, 2))
        dir_correct  = int(np.sum(np.sign(np.diff(actual_prices)) == np.sign(np.diff(pred_prices))))
        dir_accuracy = round(dir_correct / (test_days - 1) * 100, 2)

        comparison = [
            {
                "date":      d.strftime("%Y-%m-%d"),
                "actual":    round(float(a), 2),
                "predicted": round(float(p), 2),
                "error_pct": round(abs(a - p) / a * 100, 2),
            }
            for d, a, p in zip(dates, actual_prices, pred_prices)
        ]

        return {
            "mape":               round(mape, 2),
            "price_accuracy":     accuracy,
            "direction_accuracy": dir_accuracy,
            "test_days":          test_days,
            "comparison":         comparison,
        }

    # ── Future prediction ─────────────────────────────────────────────────────
    def predict_future(self, df: pd.DataFrame, days: int = 30) -> List[Dict]:
        """
        Predicts `days` future trading days via iterative log-return prediction.

        Anti-drift safeguards:
          1. Historical volatility cap  – clips each predicted return to ±2σ of
             recent daily returns (never more than ±2.5% per day).
          2. Mean-reversion dampen      – blends predicted return toward 0, with a
             progressively stronger time-decay over the forecast horizon.
          3. Ornstein-Uhlenbeck anchor  – mildly pulls price towards the 50-day moving average.
          4. Smoothing                  – averages recent predictions to prevent single-day snowballing.
        """
        if not self._trained:
            self.train(df)

        # ── Calibrate realistic return bounds from recent history ──────────
        recent_rets = np.log(df["Close"] / df["Close"].shift(1)).dropna().tail(60)
        hist_vol    = float(recent_rets.std())          # daily σ
        max_ret     = min(hist_vol * 2, 0.025)          # cap at 2.5% per day
        origin_price = float(df["Close"].iloc[-1])
        
        extended  = df.copy()
        last_date = df.index[-1]
        result    = []
        
        # Buffer to smooth predictions
        recent_predictions = []

        for step in range(days):
            feat_ext = _add_features(extended)
            if len(feat_ext) == 0:
                break

            last_feats  = feat_ext[FEATURE_COLS].iloc[[-1]].values
            raw_return  = float(self.model.predict(last_feats)[0])

            # 1. Clip to ±2σ historical volatility
            clipped = float(np.clip(raw_return, -max_ret, max_ret))

            # 2. Time-Decay and Dampen
            # Starts at 0.8 weight, decays down to a minimum of 0.1 towards the end of the horizon
            horizon_decay = max(0.1, 0.8 - (step / days) * 0.7)
            dampened = clipped * horizon_decay

            # 3. Ornstein-Uhlenbeck (MA50) anchor
            current_price = float(extended["Close"].iloc[-1])
            ma50 = float(extended["Close"].rolling(50).mean().iloc[-1])
            # Calculate distance from MA50 (percentage)
            ma_dist = (ma50 - current_price) / ma50
            # Apply a slight pull toward the MA50 (acts as a spring)
            # The further away, the stronger the pull, but capped at a modest daily rate
            mean_reversion_pull = ma_dist * 0.05
            dampened += mean_reversion_pull

            # 4. Smooth predictions
            recent_predictions.append(dampened)
            if len(recent_predictions) > 3:
                recent_predictions.pop(0)
            
            # Use the smoothed return
            smoothed_return = sum(recent_predictions) / len(recent_predictions)

            # Derive next price
            next_price = round(current_price * np.exp(smoothed_return), 2)

            next_date = last_date + pd.tseries.offsets.BDay(1)
            last_date = next_date

            result.append({
                "date":  next_date.strftime("%Y-%m-%d"),
                "price": next_price,
                "type":  "predicted",
            })

            new_row = pd.DataFrame(
                {
                    "Close":  [next_price],
                    "High":   [next_price * 1.003],
                    "Low":    [next_price * 0.997],
                    "Volume": [extended["Volume"].iloc[-1]],
                },
                index=[next_date],
            )
            extended = pd.concat([extended, new_row])

        return result

    # ── Combined series for API ───────────────────────────────────────────────
    def get_full_series(self, ticker: str, future_days: int = 30) -> Dict:
        df = DataFetcher.get_stock_data(ticker, period="2y")

        self.train(df)
        accuracy = self.evaluate(df, test_days=30)

        historical = [
            {
                "date":  date.strftime("%Y-%m-%d"),
                "price": round(float(row["Close"]), 2),
                "type":  "historical",
            }
            for date, row in df.iterrows()
        ]

        future = self.predict_future(df, days=future_days)

        return {
            "ticker":      ticker,
            "series":      historical + future,
            "accuracy":    accuracy,
            "future_days": future_days,
            "split_date":  df.index[-1].strftime("%Y-%m-%d"),
        }


# ── Per-ticker singleton cache ────────────────────────────────────────────────
_predictor_cache: Dict[str, "PredictorService"] = {}


def get_predictor(ticker: str) -> "PredictorService":
    if ticker not in _predictor_cache:
        _predictor_cache[ticker] = PredictorService()
    return _predictor_cache[ticker]


if __name__ == "__main__":
    svc    = PredictorService()
    result = svc.get_full_series("RELIANCE")
    prices = [p["price"] for p in result["series"] if p["type"] == "predicted"]
    print(f"Price accuracy : {result['accuracy']['price_accuracy']}%")
    print(f"Dir accuracy   : {result['accuracy']['direction_accuracy']}%")
    print(f"Predicted range: ₹{min(prices):,.2f} – ₹{max(prices):,.2f}")
    print(f"(spread = ₹{max(prices)-min(prices):,.2f} — should NOT be 0)")
