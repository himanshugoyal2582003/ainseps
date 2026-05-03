'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  TrendingUp, TrendingDown, Shield, Brain, Activity,
  Search, Loader2, PieChart as PieChartIcon, Newspaper,
  ExternalLink, ThumbsUp, ThumbsDown, Minus, RefreshCw,
  Target, Zap, BarChart2, CheckCircle2, AlertTriangle,
} from 'lucide-react';
import {
  ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis,
  Tooltip, CartesianGrid, ReferenceLine, Legend, AreaChart,
  BarChart, Bar, Cell,
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';

// ── Constants ─────────────────────────────────────────────────────────────────
const STOCK_LIST = [
  { symbol: 'RELIANCE',  name: 'Reliance Industries', sector: 'Energy'     },
  { symbol: 'HDFCBANK',  name: 'HDFC Bank',           sector: 'Finance'    },
  { symbol: 'INFY',      name: 'Infosys Ltd',          sector: 'IT Services'},
  { symbol: 'TATASTEEL', name: 'Tata Steel',           sector: 'Metals'    },
];
const LIVE_REFRESH_MS = 60_000; // auto-refresh every 60 s
const API_IP = process.env.NEXT_PUBLIC_API_IP || '34.136.55.49';

// ── Types ─────────────────────────────────────────────────────────────────────
interface PricePt   { date: string; price: number; type: 'historical' | 'predicted' }
interface AccuracyPt { date: string; actual: number; predicted: number; error_pct: number }
interface Accuracy  {
  mape: number; price_accuracy: number; direction_accuracy: number;
  test_days: number; comparison: AccuracyPt[];
}
interface ForecastData {
  ticker: string; series: PricePt[]; accuracy: Accuracy;
  split_date: string; future_days: number;
}
interface Article {
  title: string; url: string; source: string; time: string;
  label: 'Positive' | 'Negative' | 'Neutral'; score: number;
}
interface NewsData {
  ticker: string; sentiment: string; score: number; articles: Article[];
}





// ── Helpers ───────────────────────────────────────────────────────────────────
const sentColor = (label: string) =>
  label === 'Positive' ? '#10b981' : label === 'Negative' ? '#ef4444' : '#6b7280';

const recColor = (rec: string) =>
  rec?.includes('BUY')  ? '#10b981' :
  rec?.includes('SELL') ? '#ef4444' : '#f59e0b';

const fmt = (n: number | undefined) =>
  n != null ? `₹${n.toLocaleString('en-IN')}` : '—';

// ── Custom Tooltip for combined chart ─────────────────────────────────────────
const CombinedTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const pt = payload[0];
  const isPred = pt?.payload?.type === 'predicted';
  return (
    <div className="rounded-xl border border-white/10 px-3 py-2 text-xs backdrop-blur-md"
      style={{ background: '#0d0d18' }}>
      <div className="font-semibold mb-1 text-gray-300">{label}</div>
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full" style={{ background: isPred ? '#d946ef' : '#14b8a6' }} />
        <span style={{ color: isPred ? '#d946ef' : '#14b8a6' }}>
          {isPred ? 'Predicted' : 'Historical'}: ₹{Number(pt?.value).toLocaleString('en-IN')}
        </span>
      </div>
    </div>
  );
};

// ── Accuracy Meter ────────────────────────────────────────────────────────────
const AccuracyMeter = ({ label, value, color, suffix = '%' }:
  { label: string; value: number; color: string; suffix?: string }) => (
  <div>
    <div className="flex justify-between text-xs mb-1.5">
      <span className="text-gray-400">{label}</span>
      <span className="font-bold font-mono" style={{ color }}>{value}{suffix}</span>
    </div>
    <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${value}%` }}
        transition={{ duration: 1.2, ease: 'easeOut' }}
        className="h-full rounded-full"
        style={{ background: `linear-gradient(90deg, ${color}88, ${color})` }}
      />
    </div>
  </div>
);

// ── News Card ─────────────────────────────────────────────────────────────────
const NewsCard = ({ article, index }: { article: Article; index: number }) => {
  const borderColors = { Positive: '#10b981', Negative: '#ef4444', Neutral: '#6b7280' };
  return (
    <motion.a
      href={article.url} target="_blank" rel="noopener noreferrer"
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="block p-3 rounded-xl bg-white/[0.03] hover:bg-white/[0.07] transition-all group"
      style={{ borderLeft: `3px solid ${borderColors[article.label]}` }}
    >
      <div className="flex justify-between items-start gap-2 mb-1.5">
        <span className="text-[10px] text-gray-500 bg-white/5 px-2 py-0.5 rounded-full">{article.source}</span>
        <div className="flex items-center gap-1 shrink-0">
          {article.label === 'Positive' ? <ThumbsUp className="w-3 h-3 text-emerald-400" /> :
           article.label === 'Negative' ? <ThumbsDown className="w-3 h-3 text-red-400" /> :
           <Minus className="w-3 h-3 text-gray-500" />}
          <span className="text-[10px] font-semibold" style={{ color: sentColor(article.label) }}>
            {article.label}
          </span>
          <ExternalLink className="w-3 h-3 text-gray-600 group-hover:text-gray-400 transition-colors" />
        </div>
      </div>
      <p className="text-xs text-gray-200 leading-relaxed line-clamp-2">{article.title}</p>
    </motion.a>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN DASHBOARD
// ═══════════════════════════════════════════════════════════════════════════════
export default function Dashboard() {
  const [selectedStock,  setSelectedStock]  = useState(STOCK_LIST[0]);
  const [forecastData,   setForecastData]   = useState<ForecastData | null>(null);
  const [newsData,       setNewsData]       = useState<NewsData | null>(null);
  const [isTraining,     setIsTraining]     = useState(false);
  const [isRefreshing,   setIsRefreshing]   = useState(false);
  const [isAnalyzing,    setIsAnalyzing]    = useState(false);
  const [logs,           setLogs]           = useState<any[]>([]);
  const [techData,       setTechData]       = useState<any>(null);
  const [sentData,       setSentData]       = useState<any>(null);
  const [riskData,       setRiskData]       = useState<any>(null);
  const [finalRec,       setFinalRec]       = useState<any>(null);
  const [lastRefresh,    setLastRefresh]    = useState('');
  const [animTick,       setAnimTick]       = useState(0); // drives live chart anim
  const [isMounted,      setIsMounted]      = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const logEndRef   = useRef<HTMLDivElement>(null);
  const refreshRef  = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Chart data split ─────────────────────────────────────────────────────
  const historicalSeries = forecastData?.series.filter(p => p.type === 'historical') ?? [];
  const predictedSeries  = forecastData?.series.filter(p => p.type === 'predicted')  ?? [];

  // For the ComposedChart: merge both with nulls so lines don't connect across gap
  const chartData = (() => {
    if (!forecastData) return [];
    const splitIdx = historicalSeries.length - 1;
    return forecastData.series.map((pt, i) => ({
      date:       pt.date,
      historical: pt.type === 'historical' ? pt.price : (i === splitIdx ? pt.price : null),
      predicted:  pt.type === 'predicted'  ? pt.price : (i === splitIdx ? null : null),
      // bridge: connect last historical point to first predicted
      bridge:     (i === splitIdx || i === splitIdx + 1) ? pt.price : null,
    }));
  })();

  // ── Fetch forecast (train + predict) ─────────────────────────────────────
  const fetchForecast = useCallback(async (retrain = false) => {
    retrain ? setIsTraining(true) : setIsRefreshing(true);
    try {
      const endpoint = retrain
        ? `http://${API_IP}:8000/retrain/${selectedStock.symbol}`
        : `http://${API_IP}:8000/forecast/${selectedStock.symbol}?days=30`;
      const res  = await fetch(endpoint);
      const data = retrain ? await fetch(`http://${API_IP}:8000/forecast/${selectedStock.symbol}?days=30`).then(r => r.json()) : await res.json();
      setForecastData(data);
      setLastRefresh(new Date().toLocaleTimeString('en-IN'));
      setAnimTick(t => t + 1);
    } catch (e) {
      console.error('Forecast error:', e);
    } finally {
      setIsTraining(false);
      setIsRefreshing(false);
    }
  }, [selectedStock.symbol]);

  // ── Fetch news ────────────────────────────────────────────────────────────
  const fetchNews = useCallback(async () => {
    try {
      const res  = await fetch(`http://${API_IP}:8000/news/${selectedStock.symbol}`);
      const data = await res.json();
      setNewsData(data);
    } catch (e) { console.error('News error:', e); }
  }, [selectedStock.symbol]);

  // ── On stock change ───────────────────────────────────────────────────────
  useEffect(() => {
    setForecastData(null); setNewsData(null);
    setLogs([]); setTechData(null); setSentData(null); setRiskData(null); setFinalRec(null);
    fetchForecast();
    fetchNews();
    // Auto-refresh interval
    if (refreshRef.current) clearInterval(refreshRef.current);
    refreshRef.current = setInterval(() => fetchForecast(false), LIVE_REFRESH_MS);
    return () => { if (refreshRef.current) clearInterval(refreshRef.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedStock.symbol]);

  // ── Agent WebSocket ───────────────────────────────────────────────────────
  const startAnalysis = () => {
    setIsAnalyzing(true);
    setLogs([{ type: 'status', message: `Initializing agents for ${selectedStock.symbol}...` }]);
    setTechData(null); setSentData(null); setRiskData(null); setFinalRec(null);

    const ws = new WebSocket(`ws://${API_IP}:8000/ws/analyze/${selectedStock.symbol}`);
    ws.onmessage = (ev) => {
      const d = JSON.parse(ev.data);
      if (d.status)  setLogs(p => [...p, { type: 'status', message: d.status }]);
      if (d.agent) {
        setLogs(p => [...p, { type: 'agent', name: d.agent, message: 'Completed.' }]);
        if (d.agent === 'Technical Analyst') setTechData(d.result);
        if (d.agent === 'Sentiment Analyst') setSentData(d.result);
        if (d.agent === 'Risk Manager')      setRiskData(d.result);
      }
      if (d.final)  { setFinalRec(d.final); setIsAnalyzing(false); ws.close(); }
      if (d.error)  { setLogs(p => [...p, { type: 'status', message: `Error: ${d.error}` }]); setIsAnalyzing(false); ws.close(); }
    };
    ws.onerror = () => { setLogs(p => [...p, { type: 'status', message: 'Backend connection failed.' }]); setIsAnalyzing(false); };
  };

  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [logs]);

  const rc = recColor(finalRec?.recommendation ?? '');
  const acc = forecastData?.accuracy;

  // ── X-axis ticks: show every ~30th label ────────────────────────────────
  const tickInterval = Math.max(1, Math.floor(chartData.length / 12));

  return (
    <main className="min-h-screen p-4 md:p-8 space-y-6">

      {/* ── Header ── */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold gradient-text">AINSEP Predict</h1>
          <p className="text-gray-400 text-sm">
            Multi-Agent NSE/BSE Intel · Live Forecast Engine
            {lastRefresh && <span className="ml-2 text-gray-600">· Refreshed {lastRefresh}</span>}
          </p>
        </div>
        <div className="flex gap-3 w-full md:w-auto">
          <select
            className="glass px-4 py-2 bg-transparent outline-none flex-1 md:w-56"
            value={selectedStock.symbol}
            onChange={e => setSelectedStock(STOCK_LIST.find(s => s.symbol === e.target.value) || STOCK_LIST[0])}
          >
            {STOCK_LIST.map(s => (
              <option key={s.symbol} value={s.symbol} className="bg-[#0a0a0f]">
                {s.name} ({s.symbol})
              </option>
            ))}
          </select>
          <button
            onClick={() => fetchForecast(true)}
            disabled={isTraining || isRefreshing}
            title="Retrain model on latest data"
            className="px-4 py-2 rounded-lg font-semibold flex items-center gap-2 text-xs transition border border-white/10 hover:bg-white/5 disabled:opacity-40"
          >
            {isTraining ? <Loader2 className="animate-spin w-4 h-4" /> : <Zap className="w-4 h-4 text-yellow-400" />}
            {isTraining ? 'Training…' : 'Retrain'}
          </button>
          <button
            onClick={startAnalysis}
            disabled={isAnalyzing}
            className="px-5 py-2 bg-accent-primary hover:bg-opacity-80 transition rounded-lg font-semibold flex items-center gap-2 text-black glow disabled:opacity-50"
          >
            {isAnalyzing ? <Loader2 className="animate-spin w-4 h-4" /> : <Brain className="w-4 h-4" />}
            {isAnalyzing ? 'Analyzing…' : 'Run Agents'}
          </button>
        </div>
      </header>

      {/* ── Row 1: Main Combined Chart ── */}
      <section className="glass p-6 relative overflow-hidden">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-3">
          <div>
            <h2 className="flex items-center gap-2 font-semibold text-base">
              <Activity className="w-4 h-4 text-accent-primary" />
              Price History + 30-Day AI Forecast · {selectedStock.symbol}
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              {forecastData
                ? `${historicalSeries.length} historical · ${predictedSeries.length} predicted · split at ${forecastData.split_date}`
                : 'Loading forecast…'}
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1.5">
              <span className="w-8 h-0.5 bg-teal-400 inline-block rounded" />
              Historical
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-8 h-0.5 bg-fuchsia-500 inline-block rounded" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #d946ef 0, #d946ef 4px, transparent 4px, transparent 8px)' }} />
              Predicted
            </span>
            {isRefreshing && <RefreshCw className="w-3 h-3 animate-spin text-gray-500" />}
          </div>
        </div>

        {(isTraining && !forecastData) ? (
          <div className="h-[380px] flex flex-col items-center justify-center gap-4">
            <Loader2 className="w-10 h-10 animate-spin text-accent-primary" />
            <p className="text-gray-400 text-sm">Training XGBoost model on 2 years of data…</p>
          </div>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div key={`chart-${animTick}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-[380px]">
              {isMounted && (
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                    <defs>
                      <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#14b8a6" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#14b8a6" stopOpacity={0}    />
                      </linearGradient>
                      <linearGradient id="predGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#d946ef" stopOpacity={0.20} />
                        <stop offset="95%" stopColor="#d946ef" stopOpacity={0}    />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 10, fill: '#6b7280' }}
                      tickLine={false}
                      axisLine={false}
                      interval={tickInterval}
                      tickFormatter={d => d.slice(5)} // show MM-DD
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: '#6b7280' }}
                      tickLine={false}
                      axisLine={false}
                      domain={['auto', 'auto']}
                      tickFormatter={v => `₹${(v / 1000).toFixed(1)}k`}
                      width={55}
                    />
                    <Tooltip content={<CombinedTooltip />} />

                    {/* Split date reference line */}
                    {forecastData && (
                      <ReferenceLine
                        x={forecastData.split_date}
                        stroke="#ffffff22"
                        strokeDasharray="4 3"
                        label={{ value: 'Today', fill: '#6b7280', fontSize: 10, position: 'insideTopRight' }}
                      />
                    )}

                    {/* Historical area */}
                    <Area
                      type="monotone"
                      dataKey="historical"
                      stroke="#14b8a6"
                      strokeWidth={2}
                      fill="url(#histGrad)"
                      dot={false}
                      connectNulls={false}
                      isAnimationActive={true}
                      animationDuration={1500}
                    />

                    {/* Predicted line (dashed) */}
                    <Line
                      type="monotone"
                      dataKey="predicted"
                      stroke="#d946ef"
                      strokeWidth={2}
                      strokeDasharray="6 3"
                      dot={false}
                      connectNulls={false}
                      isAnimationActive={true}
                      animationDuration={2000}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </motion.div>
          </AnimatePresence>
        )}
      </section>

      {/* ── Row 2: Accuracy + Agent Log + Final Verdict ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* ── Prediction Accuracy Panel ── */}
        <section className="glass p-6 space-y-5">
          <h3 className="flex items-center gap-2 font-semibold">
            <Target className="w-4 h-4 text-fuchsia-400" />
            Model Accuracy
          </h3>

          {acc ? (
            <>
              <AccuracyMeter label="Price Accuracy"     value={acc.price_accuracy}     color="#10b981" />
              <AccuracyMeter label="Direction Accuracy" value={acc.direction_accuracy}  color="#14b8a6" />
              <AccuracyMeter label="Error Rate (MAPE)"  value={Math.min(acc.mape, 100)} color="#f59e0b" />

              <div className="mt-2 text-xs text-gray-500">
                Back-tested on last <span className="text-gray-300 font-semibold">{acc.test_days} trading days</span>
              </div>

              {/* Mini back-test chart */}
              <div>
                <p className="text-[10px] text-gray-500 mb-2 uppercase tracking-widest">Actual vs Predicted (back-test)</p>
                <div className="h-[120px]">
                  {isMounted && (
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={acc.comparison.slice(-20)} margin={{ top:0, right:0, left:0, bottom:0 }}>
                        <XAxis dataKey="date" hide />
                        <YAxis domain={['auto','auto']} hide />
                        <Tooltip
                          contentStyle={{ background: '#0d0d18', borderColor: '#1f2937', fontSize: 10 }}
                          formatter={(v: any, name: any) => [`₹${Number(v).toLocaleString('en-IN')}`, name]}
                        />
                        <Line type="monotone" dataKey="actual"    stroke="#14b8a6" dot={false} strokeWidth={1.5} />
                        <Line type="monotone" dataKey="predicted" stroke="#d946ef" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
                      </ComposedChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </div>

              {/* Score badges */}
              <div className="grid grid-cols-2 gap-2">
                {[
                  { icon: <CheckCircle2 className="w-3.5 h-3.5" />, label: 'Price Acc', val: `${acc.price_accuracy}%`,     color: '#10b981' },
                  { icon: <BarChart2  className="w-3.5 h-3.5" />, label: 'Direction',  val: `${acc.direction_accuracy}%`,  color: '#14b8a6' },
                  { icon: <AlertTriangle className="w-3.5 h-3.5" />, label: 'MAPE',    val: `${acc.mape}%`,               color: '#f59e0b' },
                  { icon: <Target className="w-3.5 h-3.5" />,     label: 'Test Days',  val: `${acc.test_days}d`,          color: '#6b7280' },
                ].map(({ icon, label, val, color }) => (
                  <div key={label} className="rounded-lg p-2.5" style={{ background: `${color}10`, border: `1px solid ${color}22` }}>
                    <div className="flex items-center gap-1" style={{ color }}>
                      {icon}
                      <span className="text-[9px] uppercase tracking-wide text-gray-500 ml-0.5">{label}</span>
                    </div>
                    <div className="font-bold font-mono text-sm mt-1" style={{ color }}>{val}</div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-40 text-gray-600">
              <Target className="w-8 h-8 mb-2 opacity-30" />
              <p className="text-xs">Training model…</p>
            </div>
          )}
        </section>

        {/* ── Agent Log ── */}
        <section className="glass p-6 flex flex-col h-[520px]">
          <h3 className="flex items-center gap-2 font-semibold mb-4">
            <Loader2 className={`w-4 h-4 ${isAnalyzing ? 'animate-spin' : ''}`} />
            Agent Collaboration
          </h3>
          <div className="flex-1 overflow-y-auto space-y-3 pr-1 custom-scrollbar">
            <AnimatePresence>
              {logs.map((log, i) => (
                <motion.div
                  key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                  className={`text-sm p-3 rounded-lg ${
                    log.type === 'agent'
                      ? 'bg-white/5 border border-white/10'
                      : 'text-accent-primary font-mono bg-accent-primary/5'
                  }`}
                >
                  {log.type === 'agent' && (
                    <div className="text-[10px] font-bold text-accent-secondary uppercase mb-1">{log.name}</div>
                  )}
                  {log.message}
                </motion.div>
              ))}
              <div ref={logEndRef} />
            </AnimatePresence>
            {!logs.length && (
              <p className="text-gray-600 text-xs italic text-center mt-10">
                Click "Run Agents" to start analysis…
              </p>
            )}
          </div>
        </section>

        {/* ── Final Verdict + Risk ── */}
        <div className="space-y-4">
          {/* Verdict */}
          <motion.section
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            className="p-6 rounded-2xl border-2 relative overflow-hidden"
            style={{ background: `${rc}14`, borderColor: `${rc}33` }}
          >
            <div className="relative z-10">
              <div className="text-xs uppercase tracking-widest text-gray-500 mb-1">Final Verdict</div>
              <div className="text-2xl font-black mb-4" style={{ color: rc }}>
                {finalRec ? finalRec.recommendation : 'READY FOR SCAN'}
              </div>
              {finalRec && riskData && (
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { label: 'Entry',   val: fmt(techData?.latest_close), color: '#fff'     },
                    { label: 'SL',      val: fmt(riskData?.stop_loss),    color: '#ef4444'  },
                    { label: 'Target',  val: fmt(riskData?.take_profit),  color: '#10b981'  },
                    { label: 'Risk',    val: `${riskData?.assessment} ${riskData?.risk_score}/10`, color: '#f59e0b' },
                  ].map(({ label, val, color }) => (
                    <div key={label} className="glass p-2.5 text-center rounded-xl">
                      <div className="text-[10px] text-gray-400">{label}</div>
                      <div className="font-mono text-xs font-bold mt-0.5" style={{ color }}>{val}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <Shield className="absolute top-0 right-0 w-20 h-20 opacity-10 m-4" />
          </motion.section>

          {/* Sentiment Drivers */}
          <section className="glass p-5">
            <h3 className="flex items-center gap-2 font-semibold mb-3 text-sm">
              <Search className="w-3.5 h-3.5 text-accent-primary" />
              Sentiment Drivers
            </h3>
            {sentData ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-bold px-2 py-0.5 rounded-full"
                    style={{ color: sentColor(sentData.sentiment === 'Bullish' ? 'Positive' : sentData.sentiment === 'Bearish' ? 'Negative' : 'Neutral'), background: `${sentColor(sentData.sentiment === 'Bullish' ? 'Positive' : sentData.sentiment === 'Bearish' ? 'Negative' : 'Neutral')}20` }}>
                    {sentData.sentiment} ({sentData.score > 0 ? '+' : ''}{sentData.score?.toFixed(2)})
                  </span>
                </div>
                {sentData.reasons?.map((r: string, i: number) => (
                  <div key={i} className="flex gap-2 text-xs text-gray-300">
                    <div className="w-1.5 h-1.5 rounded-full bg-accent-primary mt-1 shrink-0" />
                    {r}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-600 text-xs italic">Awaiting sentiment analysis…</p>
            )}
          </section>
        </div>
      </div>

      {/* ── Row 3: News Feed ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* News Articles */}
        <section className="glass p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="flex items-center gap-2 font-semibold">
              <Newspaper className="w-4 h-4 text-accent-primary" />
              Live News Feed · {selectedStock.symbol}
            </h3>
            <button onClick={fetchNews} className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
              <RefreshCw className="w-3.5 h-3.5 text-gray-400" />
            </button>
          </div>

          {newsData?.sentiment && (
            <div className="flex items-center gap-3 mb-4 p-3 rounded-xl"
              style={{ background: `${sentColor(newsData.sentiment === 'Bullish' ? 'Positive' : newsData.sentiment === 'Bearish' ? 'Negative' : 'Neutral')}15`,
                       border: `1px solid ${sentColor(newsData.sentiment === 'Bullish' ? 'Positive' : newsData.sentiment === 'Bearish' ? 'Negative' : 'Neutral')}30` }}>
              <div className="text-sm font-bold" style={{ color: sentColor(newsData.sentiment === 'Bullish' ? 'Positive' : newsData.sentiment === 'Bearish' ? 'Negative' : 'Neutral') }}>
                {newsData.sentiment}
              </div>
              <div className="text-xs text-gray-500">
                Overall sentiment · score {newsData.score > 0 ? '+' : ''}{newsData.score?.toFixed(2)} · {newsData.articles.length} articles
              </div>
            </div>
          )}

          <div className="space-y-2.5 max-h-[420px] overflow-y-auto custom-scrollbar pr-1">
            {newsData?.articles.length ? (
              newsData.articles.map((a, i) => <NewsCard key={i} article={a} index={i} />)
            ) : (
              <div className="flex flex-col items-center justify-center h-32 text-gray-600">
                <Newspaper className="w-8 h-8 mb-2 opacity-30" />
                <p className="text-xs">Loading news…</p>
              </div>
            )}
          </div>
        </section>

        {/* SHAP Factor Influence */}
        <section className="glass p-6">
          <h3 className="flex items-center gap-2 font-semibold mb-5">
            <PieChartIcon className="w-4 h-4 text-accent-secondary" />
            Factor Influence (SHAP)
          </h3>
          <div className="space-y-5">
            {[
              { name: 'Sentiment (NLP)', val: 45, color: '#d946ef' },
              { name: 'Technicals',      val: 35, color: '#14b8a6' },
              { name: 'Risk Score',      val: 20, color: '#f59e0b' },
            ].map(item => (
              <div key={item.name}>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="text-gray-400">{item.name}</span>
                  <span className="font-bold" style={{ color: item.color }}>{item.val}%</span>
                </div>
                <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)' }}>
                  <motion.div
                    initial={{ width: 0 }} animate={{ width: `${item.val}%` }}
                    transition={{ duration: 1 }}
                    className="h-full rounded-full"
                    style={{ background: `linear-gradient(90deg, ${item.color}80, ${item.color})` }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Predicted price target */}
          {forecastData && predictedSeries.length > 0 && (
            <div className="mt-6 p-4 rounded-xl" style={{ background: '#d946ef10', border: '1px solid #d946ef25' }}>
              <div className="text-[10px] uppercase tracking-widest text-gray-500 mb-2">30-Day Price Target</div>
              <div className="text-2xl font-black text-fuchsia-400 font-mono">
                ₹{predictedSeries[predictedSeries.length - 1]?.price?.toLocaleString('en-IN')}
              </div>
              <div className="text-xs text-gray-500 mt-1">by {predictedSeries[predictedSeries.length - 1]?.date}</div>
              {historicalSeries.length > 0 && (
                <div className="text-xs mt-2 font-semibold" style={{
                  color: predictedSeries[predictedSeries.length - 1]?.price > historicalSeries[historicalSeries.length - 1]?.price
                    ? '#10b981' : '#ef4444'
                }}>
                  {(() => {
                    const now = historicalSeries[historicalSeries.length - 1]?.price;
                    const then = predictedSeries[predictedSeries.length - 1]?.price;
                    const pct = ((then - now) / now * 100).toFixed(2);
                    return `${Number(pct) >= 0 ? '▲' : '▼'} ${Math.abs(Number(pct))}% from today`;
                  })()}
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
