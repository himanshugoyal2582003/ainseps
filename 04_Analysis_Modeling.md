# Chapter 4: Analysis Modeling

Analysis modeling provides an abstract, visual representation of the system's data architecture, internal logic flows, and functional interactions. By modeling the system prior to extensive coding, developers ensure that the data structures are optimized for machine learning ingestion and that the asynchronous communication between the Next.js frontend and FastAPI backend is logically sound.

## 4.1 Data Modeling

In a machine learning-centric application, the data model defines the schema of the inputs, the engineered features, and the predictive outputs. Unlike traditional CRUD (Create, Read, Update, Delete) applications, this system primarily relies on transient, in-memory Pandas DataFrames generated on-the-fly rather than persistent SQL tables, though the logical relationships remain identical.

### Core Data Entities and Attributes

1. **Raw_Stock_Data**
   Represents the time-series payload directly fetched from external APIs.
   - `date` (Index, Datetime): The specific trading day.
   - `open` (Float): Price at market open.
   - `high` (Float): Highest price during the session.
   - `low` (Float): Lowest price during the session.
   - `close` (Float): Price at market close (primary target variable).
   - `volume` (Integer): Total shares traded.

2. **Engineered_Feature_Space**
   Represents the enriched dataset passed into the machine learning models.
   - `raw_data_attributes` (Inherited from Raw_Stock_Data).
   - `sma_20` (Float): 20-day Simple Moving Average.
   - `ema_50` (Float): 50-day Exponential Moving Average.
   - `rsi_14` (Float): 14-day Relative Strength Index.
   - `macd` (Float): Moving Average Convergence Divergence value.
   - `lag_1` to `lag_n` (Float): Previous days' closing prices shifted backwards.

3. **Prediction_Output**
   Represents the final payload sent to the frontend for visualization.
   - `ticker` (String): The stock symbol.
   - `historical_dates` (Array of Strings): Dates for the x-axis.
   - `historical_prices` (Array of Floats): Actual past prices.
   - `predicted_dates` (Array of Strings): Future dates.
   - `predicted_prices` (Array of Floats): Model's forecasted prices.
   - `model_confidence` (Float): Ensemble agreement or error margin.

## 4.2 Activity Diagrams and Class Models

### Activity Diagram: The Prediction Workflow
The activity flow dictates how a single prediction request traverses the entire system architecture.

1. **Start:** User inputs ticker symbol and clicks 'Analyze'.
2. **Action 1 (Frontend):** Next.js validates the input and fires an API request to `http://localhost:8000/api/predict/{ticker}`.
3. **Action 2 (Backend - DataFetcher):** FastAPI receives the request and triggers the `DataFetcher` service. `yfinance` connects to external servers and downloads 5 years of OHLCV data.
4. **Decision Node:** Did the data fetch successfully?
   - *No:* Return HTTP 404/500 error to frontend. Workflow terminates.
   - *Yes:* Proceed to Preprocessing.
5. **Action 3 (Backend - Preprocessor):** Data is scrubbed for NaNs, scaled, and technical features (RSI, MACD) are generated.
6. **Action 4 (Backend - PredictorService):** The preprocessed 2D array is reshaped into a 3D tensor for LSTM ingestion. Both LSTM and XGBoost models generate isolated predictions.
7. **Action 5 (Backend - Aggregator):** The multi-agent aggregator blends the LSTM and XGBoost outputs based on weighted confidence scores to produce a final hybrid prediction.
8. **Action 6 (Frontend):** FastAPI returns JSON. Next.js parses the JSON and updates the React state.
9. **Action 7 (Frontend - Recharts):** The graphical user interface re-renders, displaying the newly plotted data.
10. **End:** User views the results.

### Class Diagram Abstractions

While Python scripts heavily utilize functional programming for data science pipelines, the backend services are structured using Object-Oriented paradigms for scalability.

- `class DataFetcher`: 
  - `fetch_historical_data(ticker, period)`
  - `fetch_news_sentiment(ticker)`
- `class Preprocessor`:
  - `clean_data(dataframe)`
  - `compute_technical_indicators(dataframe)`
  - `scale_features(dataframe)`
- `class PredictorService`:
  - `load_models()`
  - `predict_lstm(tensor)`
  - `predict_xgboost(dataframe)`
  - `aggregate_predictions(preds_a, preds_b)`

## 4.3 Functional Modeling: Data Flow Diagrams (DFD)

Data Flow Diagrams illustrate how data transforms as it moves through the system.

**Level 0 DFD (Context Diagram):**
The highest level of abstraction. The `User` (External Entity) sends a `Ticker Request` to the central process `AI Stock Predictor System`. The system responds by sending `Prediction Visualizations` back to the `User`. Behind the scenes, the system exchanges `API Queries` and `Market Data` with `Yahoo Finance API`.

**Level 1 DFD:**
Breaks down the central process into interconnected sub-processes:
- **Process 1.0 (UI Handler):** Receives ticker, routes request to backend.
- **Process 2.0 (Data Ingestion):** Pulls raw data from external APIs.
- **Process 3.0 (ETL Pipeline):** Extracts, Transforms, and Loads data into feature matrices.
- **Process 4.0 (ML Engine):** Consumes feature matrices, outputs numerical predictions.
- **Process 5.0 (Response Formatter):** Converts Numpy arrays back into JSON-serializable structures for frontend consumption.
