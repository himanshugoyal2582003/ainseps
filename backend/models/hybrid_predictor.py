import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

class HybridPredictor:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.scaler = MinMaxScaler(feature_range=(0,1))
        self.lstm_model = None
        self.xgb_model = XGBRegressor(n_estimators=100, learning_rate=0.05, max_depth=5)
        
    def prepare_data(self, df: pd.DataFrame, lookback: int = 60):
        """
        Prepares data for LSTM (sequences) and XGBoost (features).
        """
        data = df['Close'].values.reshape(-1,1)
        scaled_data = self.scaler.fit_transform(data)
        
        X_lstm, y = [], []
        for i in range(lookback, len(scaled_data)):
            X_lstm.append(scaled_data[i-lookback:i, 0])
            y.append(scaled_data[i, 0])
        
        return np.array(X_lstm), np.array(y)

    def train_lstm(self, X_train, y_train):
        """
        Trains the LSTM model for temporal features.
        """
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(X_train.shape[1], 1)),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mean_squared_error')
        model.fit(X_train, y_train, batch_size=1, epochs=1, verbose=0)
        self.lstm_model = model

    def train_xgb(self, X_train, y_train):
        """
        Trains XGBoost on the residual errors or as a refiner.
        """
        # Flatten for XGBoost
        X_xgb = X_train.reshape(X_train.shape[0], -1)
        self.xgb_model.fit(X_xgb, y_train)

    def predict(self, df: pd.DataFrame, lookback: int = 60):
        """
        Hybrid prediction: LSTM identifies trend, XGBoost refines with features.
        """
        last_60_days = df['Close'].values[-lookback:].reshape(-1,1)
        scaled_last_60_days = self.scaler.transform(last_60_days)
        
        X_test = np.array([scaled_last_60_days[:, 0]])
        X_test_lstm = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))
        
        lstm_pred = self.lstm_model.predict(X_test_lstm, verbose=0)
        
        X_test_xgb = X_test.reshape(X_test.shape[0], -1)
        xgb_pred = self.xgb_model.predict(X_test_xgb)
        
        # Simple weighted average for hybrid result
        hybrid_pred_scaled = (0.6 * lstm_pred[0][0]) + (0.4 * xgb_pred[0])
        final_price = self.scaler.inverse_transform([[hybrid_pred_scaled]])
        
        return round(float(final_price[0][0]), 2)

if __name__ == "__main__":
    # Test
    # Pre-generate some dummy data for training
    data = pd.DataFrame({"Close": np.random.randint(100, 200, 200)})
    predictor = HybridPredictor("RELIANCE")
    X, y = predictor.prepare_data(data)
    X_train = np.reshape(X, (X.shape[0], X.shape[1], 1))
    
    predictor.train_lstm(X_train, y)
    predictor.train_xgb(X, y)
    
    print(f"Prediction: {predictor.predict(data)}")
