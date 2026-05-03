# Chapter 6: Implementation

The implementation phase translates the architectural blueprints and abstract mathematical models into executable code. This chapter details the core algorithms utilized, the development environments, and the specific functional pipelines that dictate the working mechanics of the AI-Based Stock Price Trend Prediction System.

## 6.1 Algorithms and Methods Used

This project employs a hybrid algorithmic approach, fusing deep learning for sequential pattern recognition with advanced tree-based methods for feature extraction.

### 1. Data Preprocessing & Feature Engineering
Before raw financial data can be ingested by machine learning algorithms, it must be meticulously cleaned and engineered.
- **Handling Missing Values:** Market holidays or API glitches result in `NaN` values. The system uses forward-filling (`ffill()`) to propagate the last known price forward, maintaining the temporal sequence.
- **Min-Max Normalization:** Deep learning models like LSTMs are highly sensitive to unscaled data. Closing prices and trading volumes are scaled to a strictly bounded range between [0, 1] using Scikit-Learn’s `MinMaxScaler`. This ensures that large numerical values (like Volume) do not mathematically overwhelm small values (like Price).
- **Technical Indicators:** The system dynamically calculates:
  - **SMA (Simple Moving Average):** Averages prices over a set window (e.g., 20 days).
  - **RSI (Relative Strength Index):** A momentum oscillator measuring the speed of price movements, bounded between 0 and 100.
  - **MACD (Moving Average Convergence Divergence):** A trend-following momentum indicator showing the relationship between two moving averages.

### 2. Long Short-Term Memory (LSTM) Networks
The primary engine for sequence forecasting. LSTMs are a specialized variant of Recurrent Neural Networks (RNNs) explicitly designed to avoid the vanishing gradient problem.
- **Architecture:** The model consists of multiple LSTM layers. Each LSTM cell contains a forget gate, an input gate, and an output gate. This architecture allows the network to "decide" what historical price data is relevant to keep in long-term memory and what recent noise should be forgotten.
- **Implementation:** Built using TensorFlow/Keras. The data is reshaped into a 3D tensor `[samples, time_steps, features]`, where `time_steps` dictates how many days of history the model looks back upon to make a single prediction.

### 3. eXtreme Gradient Boosting (XGBoost)
Operating in parallel with the LSTM, XGBoost is utilized for its supreme capability to handle tabular feature data.
- **Architecture:** XGBoost is an ensemble algorithm based on decision trees. It builds trees sequentially, where each new tree attempts to correct the residual errors made by the previous trees (Gradient Boosting).
- **Implementation:** XGBoost evaluates the complex interplay between the engineered features (RSI, MACD, Volume spikes). It is highly resistant to overfitting when hyperparameters (like `max_depth` and `learning_rate`) are tuned correctly.

## 6.2 Working Mechanics of the System

The complete end-to-end execution flow of the system is orchestrated primarily by the FastAPI backend.

### 1. The FastAPI Backend Flow
When a user requests a prediction from the Next.js frontend, the request hits the `backend.main:app` server.

**Step A: Data Fetching**
The `DataFetcher` service receives the ticker symbol. It utilizes the `yfinance` library to download historical OHLCV data. 
```python
# Conceptual implementation snippet
import yfinance as yf
def fetch_data(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    hist = stock.history(period="5y")
    return hist
```

**Step B: Preprocessing and Scaling**
The raw Pandas DataFrame is passed to the `Preprocessor`. Technical indicators are appended. The data is then split into training and testing sets (typically an 80/20 temporal split) and normalized.

**Step C: Model Inference**
The preprocessed data is fed into the pre-trained models. 
- The LSTM model predicts the $T+n$ sequence based on the last 60 days of closing prices.
- The XGBoost model predicts the directional move based on the current day's technical indicators.

**Step D: The Multi-Agent Aggregator**
Rather than blindly trusting one model, the system implements a rudimentary multi-agent logic layer. If the LSTM predicts a 5% increase, but the XGBoost model identifies heavily overbought conditions (RSI > 80) and predicts a downturn, the aggregator calculates a weighted average or surfaces a "Mixed Signal" warning to the frontend, enhancing the system's reliability.

### 2. The Next.js Frontend Flow
Upon receiving the JSON payload from the backend containing historical dates, historical prices, and the arrays of predicted prices:

**Step A: State Management**
React hooks (`useState`, `useEffect`) update the application's global state with the newly acquired data, triggering a re-render of the DOM.

**Step B: Recharts Rendering**
The data arrays are formatted into the specific object structures required by the `Recharts` library. 
```javascript
// Conceptual implementation snippet
<LineChart data={combinedData}>
  <XAxis dataKey="date" />
  <YAxis domain={['auto', 'auto']} />
  <Tooltip />
  <Line type="monotone" dataKey="actualPrice" stroke="#10b981" />
  <Line type="monotone" dataKey="predictedPrice" stroke="#8b5cf6" strokeDasharray="5 5" />
</LineChart>
```
This renders a smooth, interactive SVG graph where the solid green line represents history, and the dashed purple line represents the AI's forecast.
