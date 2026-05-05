# Antigravity Predict - Backend (FastAPI + LangGraph)

This directory contains the core application logic and machine learning inference engine for the **AI-Based Stock Price Trend Prediction System**.

## 🧠 Architecture Overview

The backend is built with **FastAPI** for high-performance API routing and WebSocket streaming, and **LangGraph** to orchestrate a team of AI agents.

### Key Components

*   **`main.py`**: The entry point for the FastAPI server. It defines HTTP endpoints (like `/history/{ticker}`) and WebSocket endpoints (`/ws/agents`) for real-time communication with the frontend.
*   **`agents/graph.py`**: Contains the LangGraph state machine definition. It coordinates the execution flow between the different specialist agents.
*   **`agents/technical_agent.py`**: Uses `pandas-ta` to calculate Technical Indicators (RSI, MACD, Bollinger Bands) from historical price data.
*   **`agents/sentiment_agent.py`**: Analyzes market sentiment based on news (simulated or real).
*   **`agents/risk_agent.py`**: Calculates volatility, Stop-Loss (SL), and Take-Profit (TP) parameters.
*   **`models/`**: Contains the hybrid machine learning implementation (LSTM for sequences, XGBoost for tabular features).
*   **`services/data_fetcher.py`**: Responsible for downloading live historical OHLCV data using the `yfinance` library.

## 🚀 Setup & Installation

### Prerequisites
*   Python 3.10+

### Installation Steps

1.  **Navigate to the root project directory** (not this backend directory) to create your virtual environment:
    ```bash
    cd ..
    python -m venv .venv
    
    # On Mac/Linux:
    source .venv/bin/activate  
    
    # On Windows (PowerShell):
    .\.venv\Scripts\activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r backend/requirements.txt
    ```



3.  **Run the Server:**
    Run the Uvicorn server from the root directory:
    ```bash
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
    ```

## 📡 API Endpoints

Once running, you can interact with the interactive Swagger documentation at: `http://localhost:8000/docs`.

*   **`GET /history/{ticker}`**: Returns historical price data for the specified ticker.
*   **`WS /ws/agents`**: A WebSocket connection that triggers the LangGraph agent workflow for a given ticker and streams their thought processes back to the client in real-time.
