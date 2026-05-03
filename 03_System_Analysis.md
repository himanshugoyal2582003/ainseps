# Chapter 3: System Analysis

System analysis is a crucial phase in the software development life cycle (SDLC) that involves defining exactly what the proposed AI-Based Stock Price Trend Prediction System must accomplish to be deemed successful. This chapter meticulously details the functional requirements, non-functional requirements, specific hardware/software prerequisites, and detailed Use Case diagrams that dictate the system's operational parameters.

## 3.1 Functional Requirements

Functional requirements define the core behaviors, features, and capabilities the system must exhibit to serve its intended purpose. For this full-stack predictive analytics platform, the functional requirements are divided into Frontend, Backend, and Data/ML constraints.

1. **Automated Data Fetching Module:**
   - The system shall automatically fetch historical Daily OHLCV (Open, High, Low, Close, Volume) data for specified ticker symbols (e.g., "TCS.NS" or "RELIANCE.NS") using the `yfinance` Python API.
   - The system shall allow dynamic querying for variable historical time windows (e.g., 1 Year, 5 Years).

2. **Data Preprocessing & Cleaning:**
   - The system shall automatically detect and interpolate missing (NaN) values in the time-series data.
   - The system shall dynamically normalize/scale numerical data using Min-Max Scalers or Standard Scalers before feeding it into the ML models.

3. **Feature Engineering Engine:**
   - The system shall compute technical indicators dynamically, including Simple Moving Averages (SMA), Exponential Moving Averages (EMA), Relative Strength Index (RSI), and MACD, appending them as new features to the raw dataset.

4. **Machine Learning Model Orchestration:**
   - The system shall instantiate, train, and execute inference using pre-configured LSTM and XGBoost models.
   - The system shall execute a multi-agent orchestration workflow where different logic blocks (agents) synthesize technical, fundamental, and sentiment analysis.

5. **RESTful API Backend (FastAPI):**
   - The system shall expose well-documented REST API endpoints to receive data requests from the frontend and return predictive JSON payloads.
   - The API shall handle concurrent asynchronous requests without blocking the event loop.

6. **Interactive Visualization (Next.js & Recharts):**
   - The system shall render an interactive dashboard displaying historical stock charts alongside predicted future trajectories.
   - The UI shall allow the user to toggle between different stocks, timeframes, and model overlays.
   - The system shall provide tooltips detailing exact price predictions and model confidence scores on hover.

## 3.2 Non-Functional Requirements

Non-functional requirements dictate the quality attributes, performance thresholds, and architectural constraints under which the system must operate.

1. **Performance and Latency:**
   - The Next.js frontend shall load initial dashboard assets in under 2 seconds.
   - The FastAPI backend shall return pre-computed prediction results in under 500 milliseconds. Live model inference (if triggered) should return within 5 seconds.

2. **Scalability:**
   - The backend architecture must be inherently stateless, allowing it to scale horizontally via containerization (Docker) to handle increased user loads.
   - The data pipeline must be capable of handling increased feature sets (e.g., adding 50 new technical indicators) without significant architectural refactoring.

3. **Usability:**
   - The dashboard must adhere to modern UI/UX principles, offering an intuitive, "dark-mode" aesthetic suitable for financial analysts.
   - Complex ML metrics (like RMSE or MAE) must be accompanied by contextual tooltips explaining their significance to non-technical users.

4. **Reliability and Fault Tolerance:**
   - The system must gracefully handle external API rate limits or downtime (e.g., if Yahoo Finance is unreachable, the system should fall back to cached data or display a polite error state).
   - Python backend exceptions must be caught and logged; they must not crash the main FastAPI server instance.

5. **Maintainability:**
   - Code must be highly modular. The Machine Learning pipeline, the API routing layer, and the React frontend components must remain strictly decoupled.

## 3.3 Specific Hardware and Software Requirements

**Hardware Requirements:**
- **Processor:** Intel Core i5 / AMD Ryzen 5 or equivalent (Minimum).
- **RAM:** 8 GB DDR4 (16 GB Recommended for training Deep Learning models).
- **Storage:** 500 GB SSD (High read/write speeds necessary for processing Pandas DataFrames efficiently).
- **GPU (Optional but Recommended):** NVIDIA GPU with CUDA support for accelerated training of LSTM networks.

**Software Requirements:**
- **Operating System:** Windows 10/11, macOS, or Ubuntu Linux.
- **Backend Stack:** 
  - Python 3.10+
  - FastAPI, Uvicorn
  - Pandas, NumPy, Scikit-Learn
  - TensorFlow / Keras (for LSTM), XGBoost
  - `yfinance`, `TextBlob` (for NLP/Sentiment if implemented)
- **Frontend Stack:**
  - Node.js (v18+)
  - Next.js (React Framework)
  - Tailwind CSS (for styling)
  - Recharts (for data visualization)
- **Development Tools:** Visual Studio Code, Git, Postman (for API testing).

## 3.4 Use Case Diagrams and Descriptions

Use Case Diagrams visually map the interactions between external actors (users) and the system boundaries. 

### Primary Actors:
1. **End User / Analyst:** Interacts with the frontend dashboard to view predictions.
2. **System Administrator:** Manages backend deployments, updates ML models, and monitors API health.

### Core Use Cases:
**UC-1: Request Stock Prediction**
- **Actor:** End User
- **Pre-condition:** User is on the main dashboard.
- **Trigger:** User types a ticker symbol (e.g., "AAPL") into the search bar and clicks "Predict".
- **Execution:** 
  1. Frontend sends an async HTTP GET request to the FastAPI backend.
  2. Backend triggers the `DataFetcher` to pull historical data.
  3. Backend passes data through the `PredictorService`.
  4. Models generate inferences.
  5. Backend returns a structured JSON response to the frontend.
- **Post-condition:** Frontend renders the updated charts.

**UC-2: View Technical Indicators**
- **Actor:** End User
- **Pre-condition:** Stock chart is populated.
- **Execution:** User toggles "Show RSI/MACD" checkboxes. The frontend renders secondary charts below the main price chart visualizing the technical indicators computed by the backend.

**UC-3: Retrain ML Model (Admin Only)**
- **Actor:** System Administrator
- **Pre-condition:** Admin has terminal access to the backend environment.
- **Execution:** Admin triggers a dedicated Python training script. The script fetches 10 years of historical data, trains the LSTM and XGBoost models over multiple epochs, validates accuracy, and saves the new model weights (`.h5` or `.pkl` files) to the disk.
- **Post-condition:** The FastAPI server loads the newly optimized model weights for subsequent predictions.
