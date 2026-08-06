import os
import asyncio
from datetime import datetime
from typing import List, Dict

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from backend.services.data_fetcher import DataFetcher
from backend.services.news_scraper import NewsScraper
from backend.agents.sentiment_agent import SentimentAgent
from backend.services.predictor_service import get_predictor
from backend.agents.graph import StockPredictorGraph
from backend.services.news_summary_service import NewsSummaryService

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

class PDFReportGenerator:
    """Generates daily PDF stock report for user's portfolio."""

    @staticmethod
    def generate_daily_pdf(chat_id: int, user_name: str, watchlist: List[str]) -> str:
        """
        Builds a multi-stock PDF report containing market prices, ML predictions,
        news impact summaries, and AI agent signals.
        Returns the absolute filepath to the generated PDF.
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = f"AINSEPS_Daily_Report_{chat_id}_{date_str}.pdf"
        filepath = os.path.join(REPORTS_DIR, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1e293b"),
            fontName="Helvetica-Bold",
            alignment=0,
        )
        subtitle_style = ParagraphStyle(
            "SubTitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748b"),
        )
        section_style = ParagraphStyle(
            "SecHead",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#0f172a"),
            fontName="Helvetica-Bold",
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#334155"),
        )

        story = []

        # ── Title & Header Header ──────────────────────────────────────────────
        story.append(Paragraph("📈 AINSEPS AI Stock Intelligence Report", title_style))
        story.append(Spacer(1, 4))
        header_meta = f"Account: <b>{user_name or 'User'}</b> (ID: {chat_id}) &nbsp;|&nbsp; Generated: <b>{time_str}</b>"
        story.append(Paragraph(header_meta, subtitle_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceAfter=12))

        # ── Portfolio Summary Table ────────────────────────────────────────────
        story.append(Paragraph("📊 Portfolio Overview & 30-Day ML Trajectory", section_style))

        table_data = [
            [
                Paragraph("<b>Ticker</b>", body_style),
                Paragraph("<b>Current Price</b>", body_style),
                Paragraph("<b>30d ML Target</b>", body_style),
                Paragraph("<b>Return %</b>", body_style),
                Paragraph("<b>AI Recommendation</b>", body_style),
            ]
        ]

        graph = StockPredictorGraph()
        stock_details_list = []

        tickers_to_process = watchlist if watchlist else ["RELIANCE", "INFY", "AAPL"]

        for ticker in tickers_to_process[:6]:  # Limit to top 6 stocks for clean layout
            clean_t = ticker.upper().replace(".NS", "").replace(".BO", "")
            try:
                # Run graph & predictor
                agent_res = graph.run(clean_t).get("final_output", {})
                rec = agent_res.get("recommendation", "HOLD")

                svc = get_predictor(clean_t)
                pred_res = svc.get_full_series(clean_t, 30)
                series = pred_res.get("series", [])

                hist_pts = [p for p in series if p.get("type") == "historical"]
                pred_pts = [p for p in series if p.get("type") == "predicted"]

                curr_p = hist_pts[-1]["price"] if hist_pts else 0.0
                target_p = pred_pts[-1]["price"] if pred_pts else curr_p
                chg_pct = ((target_p - curr_p) / curr_p * 100) if curr_p > 0 else 0.0

                # News & Impact
                scraped = SentimentAgent.fetch_news(clean_t)
                news_analysis = [NewsSummaryService.analyze_news_item(a, clean_t) for a in scraped[:3]]

                stock_details_list.append({
                    "ticker": clean_t,
                    "agent_res": agent_res,
                    "pred_res": pred_res,
                    "curr_p": curr_p,
                    "target_p": target_p,
                    "chg_pct": chg_pct,
                    "news_analysis": news_analysis,
                    "pred_pts": pred_pts[:5],
                })

                color_hex = "#16a34a" if chg_pct >= 0 else "#dc2626"
                table_data.append([
                    Paragraph(f"<b>{clean_t}</b>", body_style),
                    Paragraph(f"₹{curr_p:,.2f}", body_style),
                    Paragraph(f"₹{target_p:,.2f}", body_style),
                    Paragraph(f"<font color='{color_hex}'><b>{chg_pct:+.2f}%</b></font>", body_style),
                    Paragraph(f"<b>{rec}</b>", body_style),
                ])
            except Exception as e:
                table_data.append([
                    Paragraph(f"<b>{clean_t}</b>", body_style),
                    Paragraph("N/A", body_style),
                    Paragraph("N/A", body_style),
                    Paragraph("N/A", body_style),
                    Paragraph("N/A", body_style),
                ])

        t_summary = Table(table_data, colWidths=[80, 100, 100, 90, 150])
        t_summary.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_summary)
        story.append(Spacer(1, 14))

        # ── Detailed Per-Stock Breakdown ───────────────────────────────────────
        for detail in stock_details_list:
            tk = detail["ticker"]
            ag = detail["agent_res"]
            sum_data = ag.get("summary", {})
            lvl = ag.get("levels", {})

            stock_elements = []
            stock_elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#94a3b8"), spaceBefore=10, spaceAfter=8))
            stock_elements.append(Paragraph(f"🔍 <b>Stock Deep-Dive: {tk}</b>", section_style))

            # Agent Summary Paragraph
            summary_txt = (
                f"<b>Recommendation:</b> {ag.get('recommendation', 'N/A')} &nbsp;|&nbsp; "
                f"<b>Technical:</b> {sum_data.get('technical', 'N/A')} &nbsp;|&nbsp; "
                f"<b>Sentiment:</b> {sum_data.get('sentiment', 'N/A')} (Score: {sum_data.get('sentiment_score', 0):+.2f})<br/>"
                f"<b>Target Levels:</b> Entry: ₹{lvl.get('entry', 0):,.2f} | Stop-Loss: ₹{lvl.get('stop_loss', 0):,.2f} | Take-Profit: ₹{lvl.get('take_profit', 0):,.2f}"
            )
            stock_elements.append(Paragraph(summary_txt, body_style))
            stock_elements.append(Spacer(1, 6))

            # News Impact Table
            if detail["news_analysis"]:
                stock_elements.append(Paragraph("<b>📰 Scraped News & Impact Ratings:</b>", body_style))
                news_rows = [[
                    Paragraph("<b>Headline & Source</b>", body_style),
                    Paragraph("<b>Impact Rating</b>", body_style),
                    Paragraph("<b>Stock Trend Prediction</b>", body_style),
                ]]
                for na in detail["news_analysis"]:
                    news_rows.append([
                        Paragraph(f"{na['title'][:65]}... (<i>{na['source']}</i>)", body_style),
                        Paragraph(f"<b>{na['impact_rating']}</b>", body_style),
                        Paragraph(f"<b>{na['direction']}</b>", body_style),
                    ])
                t_news = Table(news_rows, colWidths=[240, 110, 170])
                t_news.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                stock_elements.append(t_news)
                stock_elements.append(Spacer(1, 6))

            # Upcoming Days Prediction Table
            if detail["pred_pts"]:
                stock_elements.append(Paragraph("<b>📅 Upcoming 5-Day ML Price Forecast:</b>", body_style))
                pred_rows = [[Paragraph("<b>Date</b>", body_style), Paragraph("<b>Predicted Price</b>", body_style)]]
                for pt in detail["pred_pts"]:
                    pred_rows.append([Paragraph(pt["date"], body_style), Paragraph(f"₹{pt['price']:,.2f}", body_style)])
                t_pred = Table(pred_rows, colWidths=[150, 150])
                t_pred.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                stock_elements.append(t_pred)

            story.append(KeepTogether(stock_elements))

        # Footer
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=8))
        story.append(Paragraph("<i>This report is generated automatically by AINSEPS Multi-Agent AI System. Connect via Telegram: t.me/ainsep_bot</i>", subtitle_style))

        # Build PDF document
        doc.build(story)
        return filepath

    @staticmethod
    def generate_single_stock_pdf(ticker: str) -> str:
        """
        Builds a dedicated executive PDF summary report for a single stock
        (e.g., RELIANCE, HDFCBANK, INFY, TATASTEEL).
        """
        clean_t = ticker.upper().replace(".NS", "").replace(".BO", "")
        date_str = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = f"AINSEPS_{clean_t}_Summary_{date_str}.pdf"
        filepath = os.path.join(REPORTS_DIR, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle", parent=styles["Heading1"], fontSize=20, leading=24,
            textColor=colors.HexColor("#1e293b"), fontName="Helvetica-Bold"
        )
        subtitle_style = ParagraphStyle(
            "SubTitle", parent=styles["Normal"], fontSize=10, leading=14,
            textColor=colors.HexColor("#64748b")
        )
        section_style = ParagraphStyle(
            "SecHead", parent=styles["Heading2"], fontSize=14, leading=18,
            textColor=colors.HexColor("#0f172a"), fontName="Helvetica-Bold",
            spaceBefore=10, spaceAfter=6
        )
        body_style = ParagraphStyle(
            "Body", parent=styles["Normal"], fontSize=9, leading=12,
            textColor=colors.HexColor("#334155")
        )

        story = []

        # ── Header Banner ──────────────────────────────────────────────────────
        story.append(Paragraph(f"📊 AINSEPS Stock Intelligence Summary: <b>{clean_t}</b>", title_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"Generated: <b>{time_str}</b> &nbsp;|&nbsp; Target Stock: <b>{clean_t}</b>", subtitle_style))
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=10))

        # Run AI Multi-Agent & Predictor Service
        graph = StockPredictorGraph()
        ag_output = graph.run(clean_t).get("final_output", {})
        rec = ag_output.get("recommendation", "HOLD")
        summary_data = ag_output.get("summary", {})
        levels = ag_output.get("levels", {})

        svc = get_predictor(clean_t)
        pred_res = svc.get_full_series(clean_t, 30)
        series = pred_res.get("series", [])
        accuracy = pred_res.get("accuracy", {})

        hist_pts = [p for p in series if p.get("type") == "historical"]
        pred_pts = [p for p in series if p.get("type") == "predicted"]

        curr_p = hist_pts[-1]["price"] if hist_pts else 0.0
        target_p = pred_pts[-1]["price"] if pred_pts else curr_p
        chg_pct = ((target_p - curr_p) / curr_p * 100) if curr_p > 0 else 0.0

        # Executive Metrics Table
        story.append(Paragraph("📌 Executive Stock Metrics & AI Agent Signals", section_style))

        col_color = "#16a34a" if chg_pct >= 0 else "#dc2626"
        metrics_table = [
            [Paragraph("<b>Metric</b>", body_style), Paragraph("<b>Value</b>", body_style)],
            [Paragraph("<b>Stock Ticker</b>", body_style), Paragraph(f"<b>{clean_t}</b>", body_style)],
            [Paragraph("<b>Current Price</b>", body_style), Paragraph(f"₹{curr_p:,.2f}", body_style)],
            [Paragraph("<b>30-Day Projected Price</b>", body_style), Paragraph(f"₹{target_p:,.2f}", body_style)],
            [Paragraph("<b>Expected 30d Return</b>", body_style), Paragraph(f"<font color='{col_color}'><b>{chg_pct:+.2f}%</b></font>", body_style)],
            [Paragraph("<b>AI Recommendation</b>", body_style), Paragraph(f"<b>{rec}</b>", body_style)],
            [Paragraph("<b>Technical Signal</b>", body_style), Paragraph(f"{summary_data.get('technical', 'N/A')}", body_style)],
            [Paragraph("<b>Sentiment Score</b>", body_style), Paragraph(f"{summary_data.get('sentiment_score', 0):+.2f} ({summary_data.get('sentiment', 'N/A')})", body_style)],
            [Paragraph("<b>Risk Assessment</b>", body_style), Paragraph(f"{summary_data.get('risk_assessment', 'N/A')}", body_style)],
            [Paragraph("<b>Entry Level</b>", body_style), Paragraph(f"₹{levels.get('entry', 0):,.2f}", body_style)],
            [Paragraph("<b>Stop Loss</b>", body_style), Paragraph(f"₹{levels.get('stop_loss', 0):,.2f}", body_style)],
            [Paragraph("<b>Take Profit</b>", body_style), Paragraph(f"₹{levels.get('take_profit', 0):,.2f}", body_style)],
            [Paragraph("<b>Model Backtest Accuracy</b>", body_style), Paragraph(f"Price: {accuracy.get('price_accuracy', 0)}% | Direction: {accuracy.get('direction_accuracy', 0)}%", body_style)],
        ]

        t_m = Table(metrics_table, colWidths=[200, 320])
        t_m.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_m)
        story.append(Spacer(1, 10))

        # News Impact Section
        story.append(Paragraph("📰 Scraped News Summaries & Impact Ratings", section_style))
        scraped = SentimentAgent.fetch_news(clean_t)
        news_analysis = [NewsSummaryService.analyze_news_item(a, clean_t) for a in scraped[:4]]

        if news_analysis:
            n_rows = [[
                Paragraph("<b>News Headline & Source</b>", body_style),
                Paragraph("<b>Impact Rating</b>", body_style),
                Paragraph("<b>Stock Trend Prediction</b>", body_style),
            ]]
            for na in news_analysis:
                n_rows.append([
                    Paragraph(f"{na['title'][:65]}... (<i>{na['source']}</i>)", body_style),
                    Paragraph(f"<b>{na['impact_rating']}</b>", body_style),
                    Paragraph(f"<b>{na['direction']}</b>", body_style),
                ])
            t_n = Table(n_rows, colWidths=[240, 110, 170])
            t_n.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_n)
            story.append(Spacer(1, 10))

        # Upcoming 5-Day Forecast Table
        if pred_pts:
            story.append(Paragraph("📅 Upcoming 5-Day ML Price Forecast", section_style))
            p_rows = [[Paragraph("<b>Date</b>", body_style), Paragraph("<b>Predicted Price</b>", body_style)]]
            for pt in pred_pts[:5]:
                p_rows.append([Paragraph(pt["date"], body_style), Paragraph(f"₹{pt['price']:,.2f}", body_style)])
            t_p = Table(p_rows, colWidths=[250, 270])
            t_p.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(t_p)

        story.append(Spacer(1, 14))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=6))
        story.append(Paragraph("<i>Report generated by AINSEPS Multi-Agent AI System. Official Telegram Bot: t.me/ainsep_bot</i>", subtitle_style))

        doc.build(story)
        return filepath


if __name__ == "__main__":
    path = PDFReportGenerator.generate_daily_pdf(999, "Test User", ["RELIANCE", "INFY"])
    print(f"Generated PDF at: {path}")
    single = PDFReportGenerator.generate_single_stock_pdf("RELIANCE")
    print(f"Single stock PDF at: {single}")

