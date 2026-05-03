# Chapter 2: Literature Review

Stock price prediction has remained one of the most extensively researched and hotly debated topics at the intersection of quantitative finance, computer science, and econometrics. The holy grail of financial engineering is to develop a system capable of consistently generating alpha (market-beating returns) by anticipating future price movements. Over the decades, methodologies have evolved from rudimentary statistical models to incredibly complex deep learning architectures. This chapter reviews the chronological evolution of stock market prediction models, highlighting the strengths and critical limitations of each paradigm.

## 2.1 Traditional Statistical and Econometric Models

Historically, the foundational approaches to stock market forecasting were deeply rooted in classical statistics and econometrics. Early analysts relied on time-series forecasting models such as:

- **Moving Averages (MA) and Exponential Smoothing:** These methods filter out day-to-day noise to reveal underlying directional trends. While useful for simple trend following, they are inherently lagging indicators.
- **Autoregressive Integrated Moving Average (ARIMA):** For many years, ARIMA was the gold standard for financial time-series forecasting. It relies on the assumption of linearity and stationarity (meaning the statistical properties of the data do not change over time).

While these classical models are computationally inexpensive and highly interpretable, they possess a fatal flaw in the context of financial markets: stock prices are notoriously non-linear and non-stationary. Real-world financial data exhibits "volatility clustering" (large changes tend to be followed by large changes) and structural breaks caused by macroeconomic events. ARIMA and its variants consistently fail to capture these complex, dynamic shifts, rendering them ineffective for highly volatile assets.

## 2.2 The Shift to Machine Learning

As computing power exponentially increased and financial data became democratized, researchers began applying Machine Learning (ML) algorithms to overcome the limitations of classical statistics. Machine learning models do not require strict assumptions about data distribution and can automatically learn non-linear decision boundaries.

Prominent ML algorithms explored in financial literature include:

- **Support Vector Machines (SVM):** SVMs map input features (like historical prices and trading volume) into high-dimensional feature spaces to find the optimal hyperplane separating different market states (e.g., bull vs. bear markets).
- **k-Nearest Neighbors (k-NN):** A non-parametric method that predicts future prices based on the historical instances most mathematically similar to the current market condition.
- **Decision Trees and Random Forests:** These algorithms partition the data based on feature thresholds. Random Forest, an ensemble method, constructs a multitude of decision trees at training time, correcting for the habit of single decision trees to overfit to their training set.

Research consistently demonstrated that these ML algorithms outperformed traditional statistical methods. However, classical ML models heavily depend on manual **Feature Engineering**. If an analyst feeds poor quality or irrelevant features into a Random Forest, the model will output poor predictions (Garbage In, Garbage Out). The models themselves cannot natively deduce the sequential order of time-series data without explicit lag features being constructed manually.

## 2.3 The Deep Learning Revolution

The most significant recent leap in financial forecasting literature involves the application of Deep Learning. Unlike traditional ML, deep neural networks can perform automatic feature extraction, learning complex hierarchical representations directly from raw data.

**Recurrent Neural Networks (RNN) and LSTMs:**
Because stock data is sequential (time-series), standard feed-forward neural networks struggle to maintain temporal context. Recurrent Neural Networks (RNNs) address this by maintaining a hidden state that acts as "memory" of previous inputs. 

However, basic RNNs suffer from the "vanishing gradient problem," making them incapable of learning long-term dependencies (e.g., remembering a price pattern from 60 days ago). This led to the widespread adoption of **Long Short-Term Memory (LSTM)** networks in quantitative finance. LSTMs utilize a sophisticated gating mechanism (input, forget, and output gates) to selectively remember crucial long-term patterns while forgetting irrelevant short-term noise. Countless peer-reviewed studies have proven that LSTMs provide vastly superior prediction accuracy for time-series forecasting compared to SVMs or Random Forests.

## 2.4 Hybrid Models and Ensemble Architectures

More recent literature suggests that no single algorithm is a silver bullet. The current state-of-the-art involves **Hybrid Models** and ensemble architectures.

For example, researchers have successfully combined:
1. **LSTMs:** To capture the continuous, sequential price patterns.
2. **eXtreme Gradient Boosting (XGBoost):** To rapidly evaluate discrete technical indicators (MACD, RSI) and fundamental data points.

By blending the outputs of deep learning models with advanced tree-based algorithms, hybrid systems achieve lower variance and higher stability in their predictions, mitigating the weaknesses inherent in relying on a single architecture.

## 2.5 Alternative Data and Sentiment Analysis

Modern financial literature heavily emphasizes the use of "Alternative Data." Stock prices are not simply a function of historical prices; they are heavily influenced by public sentiment, news cycles, and social media buzz.

Natural Language Processing (NLP) techniques are increasingly integrated into prediction pipelines. By performing sentiment analysis on live financial news feeds, Twitter/X, and company earnings transcripts using transformer-based models (like FinBERT), analysts can quantify market psychology. Studies demonstrate that fusing numerical price data with text-based sentiment data significantly reduces prediction error, particularly during periods of high market volatility triggered by breaking news.

## 2.6 Limitations and the Road Ahead

Despite these monumental advancements, the literature universally acknowledges several persistent challenges:

1. **Market Efficiency and Unpredictability:** The Efficient Market Hypothesis dictates that prices quickly reflect all available information. "Black swan" events (e.g., the 2008 financial crisis or the 2020 pandemic) cannot be predicted by any model trained purely on historical data.
2. **Overfitting:** Deep learning models, given their massive parameter counts, are highly prone to overfitting—memorizing the training data but failing catastrophically on unseen future data.
3. **Data Stationarity and Regime Changes:** A model trained during a decade-long bull market will likely fail during a sudden recession. Financial markets frequently undergo "regime shifts" that invalidate historical patterns.

This project synthesizes these literature findings by utilizing a hybrid machine learning approach, avoiding the pitfalls of rigid statistical models while implementing robust data preprocessing to mitigate the overfitting risks associated with deep learning.
