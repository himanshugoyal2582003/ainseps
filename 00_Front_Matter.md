# AI-Based Stock Price Trend Prediction System (Educational)

**Submitted in partial fulfillment of requirements for the degree of B.Tech. (Computer Science & Engineering)**

**By:**
- Himanshu Goyal (2415000685)
- Ridam Mittal (2415001273)
- Abhishek (2415000041)
- Priyanshu Yadav (2415001214)

**Under Supervision of:**
Dr. Sayantan Sinha & Dr. Rahul Pradhan
Department of Computer Engineering & Applications
GLA University, 17km Stone, NH-19, Delhi-Mathura Road, P.O. Chaumuhan, Mathura-281 406 (U.P.) India
Batch 2024-2028

---

## Certificate

This is to certify that Mini Project entitled **AI-Based Stock Price Trend Prediction System (Educational)** is a bonafide work of the aforementioned students submitted to the GLA University, Mathura in partial fulfillment of the requirements for the award of the degree of ”Bachelor of Technology” in Computer Science & Engineering.

*(Name and sign)*
(Dr. Rahul Pradhan)
Guide Program Chair-AI & Data Science
Department of Computer Engineering & Applications

---

## Certificate of Approval of Supervisor

The Mini Project report **AI-Based Stock Price Trend Prediction System (Educational)** is approved for the award of Bachelor’s of Technology Degree in Computer Science & Engineering.

**Supervisor**
Date: 2/05/2026
Place: Mathura-281406
Department of Computer Engineering & Applications

---

## Declaration

We declare that this written submission represents our ideas in our own words and where others’ ideas or work have been included. We have adequately cited and referenced the original source. We also declare that we have adhered to all principles of academic honesty and integrity and have not misinterpreted or fabricated or falsified any idea/data/fact/source in our submission. We understand that any violation of the above will be cause for disciplinary action by the Institute and can also evoke the penal action from the sources which have thus not been properly cited or from whom proper permission has not been taken when needed.

**Signatures:**
- Himanshu Goyal
- Ridam Mittal
- Abhishek
- Priyanshu Yadav

Date: 2026-05-02
Place: Mathura - 281406

---

## Abstract

Stock market analysis is a complex and dynamic process that involves handling massive volumes of time-dependent financial data. The prices of stocks fluctuate continuously due to various influencing factors such as macroeconomic conditions, company performance metrics, market sentiment, government policies, and unpredictable global events. Due to this high level of inherent uncertainty and volatility, accurately predicting stock price movements has historically been one of the most challenging tasks in quantitative finance. Traditional methods of stock analysis, which rely heavily on manual calculations and rudimentary statistical techniques, often fail to process large, multi-dimensional datasets efficiently, leading to inconsistent and inaccurate results that do not adapt well to shifting market regimes.

With the rapid and transformative advancement of Artificial Intelligence (AI) and Machine Learning (ML), new paradigms have emerged for analyzing financial data more effectively. Machine learning algorithms, particularly deep learning architectures and tree-based ensemble methods, possess the unique capability to process colossal amounts of historical data, identify non-linear hidden patterns, and make robust predictions based on learned trends. This project focuses on the development of an advanced **AI-Based Stock Price Trend Prediction system** designed for educational, analytical, and simulated portfolio optimization purposes. 

The proposed system adopts a modern tech stack, utilizing a high-performance **FastAPI** backend to orchestrate data pipelines and machine learning inference, paired with a dynamic **Next.js** frontend for real-time visualization and interactive user experience. It employs historical stock price data obtained dynamically via APIs (such as Yahoo Finance) to train sophisticated machine learning models—specifically hybridizing the sequence-modeling strengths of **Long Short-Term Memory (LSTM)** networks with the predictive power of **eXtreme Gradient Boosting (XGBoost)** models. 

The architecture follows a highly structured machine learning pipeline that includes extensive data collection, rigorous data preprocessing, exploratory data analysis (EDA), and sophisticated feature engineering. Preprocessing guarantees dataset integrity by resolving missing, redundant, or anomalous values. EDA provides statistical insights and graphical representations of market trends. Feature engineering is heavily applied to boost model performance by creating actionable, domain-specific attributes such as Moving Average Convergence Divergence (MACD), Relative Strength Index (RSI), lag features, and rolling volatilities.

Furthermore, this project integrates multi-agent orchestration paradigms to simulate a collaborative analysis environment, mimicking a professional trading desk where different agents analyze technical indicators, news sentiment, and risk factors before producing a consensus prediction. The predictions are surfaced to the user via interactive, real-time charts powered by Recharts, ensuring the system remains intuitive and educational.

The primary objective of this comprehensive project is to provide profound practical exposure to cutting-edge AI, ML, and full-stack web development techniques in the domain of financial data analysis. It also aims to emphatically highlight the limitations of predictive models in real-world scenarios. Because stock markets are notoriously influenced by stochastic external factors like breaking news and geopolitical shifts, the system incorporates an element of explainability to help users understand the "why" behind specific model inferences. Ultimately, this system serves as a powerful foundational learning tool bridging quantitative finance, deep learning, and modern web application development, laying the groundwork for future research into fully autonomous, real-time algorithmic trading simulations.
