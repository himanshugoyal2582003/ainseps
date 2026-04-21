from typing import TypedDict, Annotated, List, Dict
import operator
from langgraph.graph import StateGraph, END
from .technical_agent import TechnicalAgent
from .sentiment_agent import SentimentAgent
from .risk_agent import RiskManagerAgent
from ..services.data_fetcher import DataFetcher


class AgentState(TypedDict):
    ticker: str
    messages: Annotated[List[str], operator.add]
    tech_data: dict
    sentiment_data: dict
    risk_data: dict
    final_output: dict


class StockPredictorGraph:
    def __init__(self):
        self.builder = StateGraph(AgentState)
        self._build_graph()

    def _tech_node(self, state: AgentState) -> dict:
        """Technical Analysis Node"""
        df = DataFetcher.get_stock_data(state["ticker"])
        result = TechnicalAgent.analyze(df)
        return {
            "tech_data": result,
            "messages": [f"Technical analysis complete for {state['ticker']}."],
        }

    def _sent_node(self, state: AgentState) -> dict:
        """Sentiment Analysis Node — now uses real news scraper + TextBlob NLP"""
        articles = SentimentAgent.fetch_news(state["ticker"])
        result = SentimentAgent.analyze_sentiment(articles)
        return {
            "sentiment_data": result,
            "messages": [
                f"Sentiment analysis complete for {state['ticker']}. "
                f"Score={result['score']:.2f} ({result['sentiment']}). "
                f"Analysed {len(result['articles'])} articles."
            ],
        }

    def _risk_node(self, state: AgentState) -> dict:
        """Risk Management Node — uses numeric sentiment score"""
        current_price   = state["tech_data"].get("latest_close", 0)
        tech_sig        = state["tech_data"].get("signal", "Neutral")
        sent_sig        = state["sentiment_data"].get("sentiment", "Neutral")
        sentiment_score = state["sentiment_data"].get("score", 0.0)   # ← NEW

        result = RiskManagerAgent.calculate_risk(
            state["ticker"], current_price, 0.05,
            tech_sig, sent_sig, sentiment_score=sentiment_score,       # ← NEW
        )
        return {
            "risk_data": result,
            "messages": [f"Risk management check complete. Assessment: {result['assessment']}."],
        }

    def _aggregator_node(self, state: AgentState) -> dict:
        """Final Aggregation Node"""
        final_output = {
            "ticker": state["ticker"],
            "recommendation": state["risk_data"]["recommendation"],
            "summary": {
                "technical":        state["tech_data"]["signal"],
                "sentiment":        state["sentiment_data"]["sentiment"],
                "sentiment_score":  state["sentiment_data"]["score"],
                "risk_assessment":  state["risk_data"]["assessment"],
                "articles_analysed": len(state["sentiment_data"].get("articles", [])),
            },
            "levels": {
                "entry":       state["tech_data"]["latest_close"],
                "stop_loss":   state["risk_data"]["stop_loss"],
                "take_profit": state["risk_data"]["take_profit"],
            },
        }
        return {
            "final_output": final_output,
            "messages": ["Final analysis aggregated."],
        }

    def _build_graph(self):
        self.builder.add_node("technical",  self._tech_node)
        self.builder.add_node("sentiment",  self._sent_node)
        self.builder.add_node("risk",       self._risk_node)
        self.builder.add_node("aggregator", self._aggregator_node)

        self.builder.set_entry_point("technical")
        self.builder.add_edge("technical",  "sentiment")
        self.builder.add_edge("sentiment",  "risk")
        self.builder.add_edge("risk",       "aggregator")
        self.builder.add_edge("aggregator", END)

        self.graph = self.builder.compile()

    def run(self, ticker: str):
        """Runs the multi-agent graph for a specific ticker."""
        initial_state = {
            "ticker":         ticker,
            "messages":       [],
            "tech_data":      {},
            "sentiment_data": {},
            "risk_data":      {},
            "final_output":   {},
        }
        return self.graph.invoke(initial_state)


if __name__ == "__main__":
    predictor = StockPredictorGraph()
    result = predictor.run("RELIANCE")
    print(result["final_output"])
