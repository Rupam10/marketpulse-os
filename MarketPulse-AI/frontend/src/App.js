import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine, Cell } from 'recharts';
import './App.css';

// --- Premium Cinematic CSS & Animations ---
const premiumStyles = `
  @keyframes pulseGlow {
    0% { box-shadow: 0 0 5px rgba(56, 189, 248, 0.2); }
    50% { box-shadow: 0 0 15px rgba(56, 189, 248, 0.6); }
    100% { box-shadow: 0 0 5px rgba(56, 189, 248, 0.2); }
  }
  @keyframes fadeUpIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes blink-caret {
    from, to { border-color: transparent }
    50% { border-color: #38bdf8; }
  }
  
  .typing-effect {
    display: inline-block;
    overflow: hidden;
    white-space: nowrap;
    border-right: 2px solid #38bdf8;
    animation: typing 1.2s steps(40, end), blink-caret .75s step-end infinite;
  }
  @keyframes typing {
    from { width: 0 }
    to { width: 100% }
  }
  
  .glass-card {
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  }
  
  .glass-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 15px 35px 0 rgba(0, 0, 0, 0.5);
    border-color: rgba(56, 189, 248, 0.3);
  }

  .premium-scrollbar::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }
  .premium-scrollbar::-webkit-scrollbar-track {
    background: rgba(15, 23, 42, 0.3);
  }
  .premium-scrollbar::-webkit-scrollbar-thumb {
    background: rgba(56, 189, 248, 0.4);
    border-radius: 10px;
  }
  .premium-scrollbar::-webkit-scrollbar-thumb:hover {
    background: #38bdf8;
  }
  
  .responsive-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 20px;
  }
  
  .responsive-flex {
    display: flex;
    flex-wrap: wrap;
    gap: 25px;
  }
`;

const AnimatedCounter = ({ value, suffix = "" }) => {
  const [count, setCount] = useState(0);
  // Only animate plain integers (e.g. "87%") — not decimal scores like "7.2/10"
  const numericValue = parseFloat(String(value).replace(/[^0-9.]/g, '')) || 0;
  const isDecimal = String(value).includes('.');

  useEffect(() => {
    if (isDecimal) return; // don't animate decimals — display as-is
    let start = 0;
    const end = Math.round(numericValue);
    if (start === end) return;
    const totalMilSecDur = 1200;
    const incrementTime = (totalMilSecDur / end) * 2;
    let timer = setInterval(() => {
      start += 1;
      setCount(start);
      if (start >= end) { clearInterval(timer); setCount(end); }
    }, incrementTime);
    return () => clearInterval(timer);
  }, [numericValue, isDecimal]);

  if (isDecimal) return <span>{value}</span>;
  return <span>{numericValue > 0 ? count : value}{suffix}</span>;
};

function App() {
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [currentTime, setCurrentTime] = useState(new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}));
  
  const [scanStep, setScanStep] = useState(0);
  const [agentStatus, setAgentStatus] = useState('SYSTEM STANDBY');
  
  const [chatHistory, setChatHistory] = useState([
    { type: 'agent', message: "MarketPulse OS Online. Autonomous logic engines initialized. Awaiting strategic market vector for analysis.", time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }
  ]);
  
  const chatEndRef = useRef(null);
  const terminalEndRef = useRef(null);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})), 60000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);
  
  useEffect(() => {
      terminalEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [scanStep]);

  const scanningSteps = [
    { text: "Connecting to Bright Data APIs...", status: "Establishing Link" },
    { text: "Scanning live Amazon ecosystem...", status: "Live Web Crawl" },
    { text: "Extracting competitor pricing & tiering...", status: "Data Extraction" },
    { text: "Aggregating customer sentiment & reviews...", status: "NLP Analysis" },
    { text: "Calculating pricing pressure & market trends...", status: "Trend Detection" },
    { text: "Executing Gemini AI strategic reasoning...", status: "Reasoning Phase" },
    { text: "Generating executive intelligence report...", status: "Finalizing Render" }
  ];

  useEffect(() => {
    let interval;
    if (loading && scanStep < scanningSteps.length) {
      setAgentStatus(scanningSteps[scanStep].status);
      interval = setInterval(() => {
        setScanStep(prev => prev + 1);
      }, 1200); 
    } else if (!loading && data) {
      setAgentStatus('LIVE DATA ACTIVE');
    }
    return () => clearInterval(interval);
  }, [loading, scanStep, data]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!keyword.trim()) return;

    const timeStr = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    setChatHistory(prev => [...prev, { type: 'user', message: `Execute deep market analysis for: ${keyword}`, time: timeStr }]);
    setLoading(true);
    setScanStep(0); 
    
    try {
      const payload = { keyword: keyword };
      console.log('[MarketPulse] Sending analysis request');
      console.log('[MarketPulse] Request payload', payload);
      console.log('[MarketPulse] Target URL', 'http://127.0.0.1:5000/api/analyze');

      const response = await axios.post('http://127.0.0.1:5000/api/analyze', payload);

      console.log('[MarketPulse] Response received', { status: response.data.status, product_count: response.data.product_count });
      
      if (response.data.status === "error") {
        console.error('[MarketPulse] API Error', response.data);
        setChatHistory(prev => [...prev, { 
          type: 'error', 
          message: response.data.message || "An error occurred. Please try again.", 
          time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) 
        }]);
        setLoading(false);
        setAgentStatus('AWAITING VALID INPUT');
        setKeyword('');
        return; 
      }

      if (response.data.status === "no_data") {
        console.warn('[MarketPulse] No data returned', response.data);
        setChatHistory(prev => [...prev, { 
          type: 'error', 
          message: response.data.message || `No data found for '${keyword}'. Try a different search term.`, 
          time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) 
        }]);
        setLoading(false);
        setAgentStatus('NO DATA RETURNED');
        setKeyword('');
        return;
      }

      const renderData = () => {
        setData(response.data);
        const cacheNote = response.data._cached ? ' (cached)' : '';
        const ms = response.data._response_ms ? ` · ${response.data._response_ms}ms` : '';
        setChatHistory(prev => [...prev, { 
          type: 'agent', 
          message: `Analysis Complete. Processed ${response.data.product_count} products for '${keyword}'${cacheNote}${ms}. Dashboard deployed.`,
          time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
        }]);
        setLoading(false);
      };

      if (scanStep < scanningSteps.length - 1) {
          setTimeout(renderData, (scanningSteps.length - scanStep) * 1000);
      } else {
          renderData();
      }
      
    } catch (err) {
      console.error('[MarketPulse] API Error', err);
      // Show the actual backend error message if available, otherwise a specific network message
      const backendMsg = err.response?.data?.message;
      const msg = backendMsg
        ? backendMsg
        : err.response?.status === 429
        ? "Rate limit reached. Please wait a moment and try again."
        : err.response?.status >= 500
        ? `Server error (${err.response.status}). Please try again.`
        : (err.code === 'ERR_NETWORK' || err.code === 'ECONNREFUSED' || !err.response)
        ? "Cannot connect to the analysis server. Please ensure the backend is running on port 5000."
        : `Request failed: ${err.message}`;
      setChatHistory(prev => [...prev, { type: 'error', message: msg, time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }]);
      setLoading(false);
      setAgentStatus('SYSTEM ERROR');
    }
    setKeyword('');
  };

  const avgPrice = (data && data.market_data && Array.isArray(data.market_data)) 
    ? (data.market_data.reduce((acc, curr) => acc + (curr.clean_price || 0), 0) / data.market_data.length).toFixed(0) 
    : 0;

  // ISSUE 8 — Use pre-computed brand chart data from backend
  // Fix 1: filter out "Unknown Brand" entries — they look unprofessional in charts
  const brandChartData = (data && data.brand_chart)
    ? data.brand_chart.filter(b => b.brand && b.brand !== 'Unknown Brand' && b.brand !== 'Unknown')
    : [];
  const avgOfAvgs = brandChartData.length
    ? Math.round(brandChartData.reduce((s, b) => s + b.avg_price, 0) / brandChartData.length)
    : 0;

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', backgroundColor: '#020617', color: '#e2e8f0', fontFamily: 'Inter, system-ui, sans-serif', overflow: 'hidden' }}>
      <style>{premiumStyles}</style>
      
      {/* ---------------- LEFT PANEL: AI AGENT TERMINAL ---------------- */}
      <div style={{ flex: '0 0 360px', borderRight: '1px solid rgba(255,255,255,0.06)', display: 'flex', flexDirection: 'column', backgroundColor: '#0f172a', zIndex: 10 }}>
        
        <div style={{ padding: '25px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)', background: 'linear-gradient(180deg, rgba(15,23,42,1) 0%, #020617 100%)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '15px' }}>
            <div style={{ 
              width: '14px', height: '14px', borderRadius: '50%', 
              backgroundColor: loading ? '#f59e0b' : (data ? '#10b981' : '#38bdf8'), 
              boxShadow: `0 0 12px ${loading ? '#f59e0b' : (data ? '#10b981' : '#38bdf8')}`,
              animation: loading ? 'pulseGlow 1.5s infinite' : 'none'
            }}></div>
            <div>
              <h2 style={{ margin: 0, color: '#f8fafc', fontSize: '1.3rem', letterSpacing: '2px', fontWeight: '900' }}>MARKETPULSE OS</h2>
              <div style={{ fontSize: '0.65rem', color: '#38bdf8', letterSpacing: '1px', opacity: 0.8 }}>AUTONOMOUS MARKET INTELLIGENCE</div>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.4)', padding: '10px 12px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)' }}>
             <span style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>System Status</span>
             <span style={{ fontSize: '0.7rem', color: loading ? '#fbbf24' : (data ? '#10b981' : '#64748b'), fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '6px', letterSpacing: '0.5px' }}>
                {data && !loading && <span style={{display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10b981', animation: 'pulseGlow 2s infinite'}}></span>}
                {agentStatus}
             </span>
          </div>
        </div>
        
        <div className="premium-scrollbar" style={{ flex: 1, padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {chatHistory.map((chat, idx) => (
            <div key={idx} style={{ 
              alignSelf: chat.type === 'user' ? 'flex-end' : 'flex-start',
              backgroundColor: chat.type === 'user' ? 'rgba(14, 165, 233, 0.12)' : (chat.type === 'error' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(30, 41, 59, 0.6)'),
              border: `1px solid ${chat.type === 'user' ? 'rgba(14, 165, 233, 0.3)' : (chat.type === 'error' ? '#dc2626' : 'rgba(255,255,255,0.05)')}`,
              padding: '16px', borderRadius: '12px', maxWidth: '90%',
              borderBottomRightRadius: chat.type === 'user' ? '2px' : '12px',
              borderTopLeftRadius: chat.type === 'agent' ? '2px' : '12px',
              animation: 'fadeUpIn 0.3s ease-out'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                 <span style={{ fontSize: '0.65rem', color: chat.type === 'user' ? '#7dd3fc' : (chat.type === 'error' ? '#fca5a5' : '#94a3b8'), textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 'bold' }}>
                   {chat.type === 'user' ? 'COMMANDER' : (chat.type === 'error' ? 'SYSTEM ALERT' : 'AI AGENT')}
                 </span>
                 <span style={{ fontSize: '0.65rem', color: '#64748b' }}>{chat.time}</span>
              </div>
              <div style={{ color: chat.type === 'user' ? '#f0f9ff' : (chat.type === 'error' ? '#fca5a5' : '#e2e8f0'), fontSize: '0.95rem', lineHeight: '1.6' }}>{chat.message}</div>
            </div>
          ))}
          
          {loading && (
            <div style={{ alignSelf: 'flex-start', backgroundColor: '#020617', border: '1px solid #334155', padding: '16px', borderRadius: '8px', width: '100%', fontFamily: "'Fira Code', monospace", boxShadow: 'inset 0 0 15px rgba(0,0,0,0.5)' }}>
              <div style={{ color: '#fbbf24', fontSize: '0.75rem', marginBottom: '15px', textTransform: 'uppercase', letterSpacing: '1px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{display: 'inline-block', width: '8px', height: '8px', backgroundColor: '#fbbf24', animation: 'pulseGlow 1s infinite'}}></span>
                Live Intelligence Sweep
              </div>
              <div className="premium-scrollbar" style={{ maxHeight: '160px', overflowY: 'auto' }}>
                {scanningSteps.map((step, idx) => {
                   if (idx > scanStep) return null;
                   const isActive = idx === scanStep;
                   return (
                      <div key={idx} style={{ 
                        color: isActive ? '#38bdf8' : '#10b981',
                        marginBottom: '8px', fontSize: '0.75rem', display: 'flex', alignItems: 'flex-start', gap: '10px'
                      }}>
                        <span style={{ marginTop: '1px' }}>{isActive ? '[>]' : '[✓]'}</span> 
                        <span className={isActive ? "typing-effect" : ""}>{step.text}</span>
                      </div>
                   )
                })}
                <div ref={terminalEndRef} />
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <form onSubmit={handleSearch} style={{ padding: '20px', display: 'flex', gap: '10px', borderTop: '1px solid rgba(255,255,255,0.06)', backgroundColor: '#020617' }}>
          <input 
            type="text" 
            value={keyword} 
            onChange={(e) => setKeyword(e.target.value)} 
            placeholder="Initialize target..."
            style={{ flex: 1, padding: '14px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.1)', backgroundColor: 'rgba(15,23,42,0.8)', color: 'white', outline: 'none', transition: 'all 0.3s', fontSize: '0.95rem' }}
            onFocus={(e) => { e.target.style.border = '1px solid #38bdf8'; e.target.style.boxShadow = '0 0 8px rgba(56,189,248,0.2)'; }}
            onBlur={(e) => { e.target.style.border = '1px solid rgba(255,255,255,0.1)'; e.target.style.boxShadow = 'none'; }}
          />
          <button type="submit" disabled={loading} style={{ 
            padding: '0 20px', backgroundColor: loading ? '#334155' : '#0ea5e9', color: loading ? '#94a3b8' : '#fff', border: 'none', borderRadius: '6px', 
            fontWeight: 'bold', letterSpacing: '1px', cursor: loading ? 'not-allowed' : 'pointer', 
            transition: 'all 0.3s', textTransform: 'uppercase', fontSize: '0.85rem'
          }}>
            Engage
          </button>
        </form>
      </div>

      {/* ---------------- RIGHT PANEL: ENTERPRISE DASHBOARD ---------------- */}
      <div className="premium-scrollbar" style={{ flex: 1, padding: '40px 50px', overflowY: 'auto', backgroundColor: '#020617', backgroundImage: 'radial-gradient(circle at 80% 20%, rgba(14, 165, 233, 0.05) 0%, rgba(2, 6, 23, 1) 60%)' }}>
        {data && data.ai_strategy && !loading ? (
          <div style={{ animation: 'fadeUpIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards' }}>
            
            <div className="responsive-flex" style={{ justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '35px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                  <span style={{ fontSize: '0.65rem', color: '#020617', backgroundColor: '#38bdf8', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', letterSpacing: '1px' }}>AI GENERATED REPORT</span>
                  <span style={{ fontSize: '0.65rem', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.4)', padding: '2px 8px', borderRadius: '4px', letterSpacing: '1px', backgroundColor: 'rgba(16, 185, 129, 0.1)' }}>LIVE DATA ACTIVE</span>
                  {data._cached && (
                    <span style={{ fontSize: '0.65rem', color: '#f59e0b', border: '1px solid rgba(245,158,11,0.4)', padding: '2px 8px', borderRadius: '4px', letterSpacing: '1px', backgroundColor: 'rgba(245,158,11,0.08)' }}>CACHED</span>
                  )}
                </div>
                <h1 style={{ margin: 0, color: '#f8fafc', fontSize: '3rem', letterSpacing: '-1px', fontWeight: '800' }}>
                  {data.keyword.toUpperCase()}
                </h1>
                <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '5px' }}>
                  Category: <span style={{ color: '#38bdf8' }}>{data.category}</span>
                  &nbsp;·&nbsp;{data.product_count} products scraped
                  &nbsp;·&nbsp;Last Update: {currentTime}
                </div>
              </div>
              
              <div className="glass-card" style={{ padding: '15px 20px', borderRadius: '10px', textAlign: 'right' }}>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '1px' }}>Live Intelligence Sources</div>
                <div style={{ display: 'flex', gap: '12px', fontSize: '0.85rem', color: '#e2e8f0', fontWeight: '500' }}>
                  {Object.entries(data.source_counts || {}).map(([src, count]) => (
                    <span key={src} style={{display: 'flex', alignItems: 'center', gap:'5px'}}>
                      <span style={{color: count > 0 ? '#10b981' : '#ef4444', fontSize: '0.6rem'}}>●</span>
                      {src}: {count}
                    </span>
                  ))}
                  {(!data.source_counts || Object.keys(data.source_counts).length === 0) && (
                    <span style={{display: 'flex', alignItems: 'center', gap:'5px'}}>
                      <span style={{color: '#10b981', fontSize: '0.6rem'}}>●</span> Amazon
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '0.65rem', color: '#38bdf8', marginTop: '8px', fontStyle: 'italic', opacity: 0.9 }}>Powered by Bright Data API</div>
              </div>
            </div>

            <div className="glass-card" style={{ 
              borderRadius: '16px', padding: '35px', marginBottom: '35px', 
              borderLeft: '4px solid #38bdf8'
            }}>
              <h2 style={{ margin: '0 0 20px 0', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '12px', fontSize: '1.6rem', fontWeight: '400' }}>
                <span style={{ fontSize: '1.8rem' }}>🧠</span> Executive Intelligence Brief
              </h2>
              {data.ai_strategy.executive_summary && (
                <p style={{ fontSize: '1.05rem', lineHeight: '1.7', color: '#cbd5e1', margin: '0 0 20px 0' }}>
                  {data.ai_strategy.executive_summary}
                </p>
              )}
              <p style={{ fontSize: '1.1rem', lineHeight: '1.7', color: '#cbd5e1', margin: '0 0 25px 0', fontWeight: '400' }}>
                {data.ai_strategy.pricing_strategy}
              </p>
              {data.ai_strategy.opportunities && (
                <div style={{ backgroundColor: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '20px', borderRadius: '10px', display: 'flex', gap: '15px', alignItems: 'flex-start' }}>
                  <div style={{ fontSize: '1.4rem' }}>🎯</div>
                  <div>
                    <strong style={{ color: '#10b981', display: 'block', marginBottom: '6px', fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Strategic Recommendation</strong>
                    <span style={{ color: '#a7f3d0', fontSize: '1.05rem', lineHeight: '1.5' }}>{data.ai_strategy.opportunities}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Customer Sentiment / Pricing Analysis / Risks / Competitive Insights */}
            {(data.ai_strategy.customer_sentiment || data.ai_strategy.pricing_analysis || data.ai_strategy.risks || data.ai_strategy.competitive_insights) && (
              <div className="responsive-flex" style={{ marginBottom: '35px' }}>
                {data.ai_strategy.customer_sentiment && (
                  <div className="glass-card" style={{ flex: '1 1 300px', borderRadius: '16px', padding: '25px', borderLeft: '3px solid #8b5cf6' }}>
                    <h3 style={{ margin: '0 0 12px 0', color: '#f8fafc', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span>💬</span> Customer Sentiment
                    </h3>
                    <p style={{ color: '#cbd5e1', fontSize: '0.9rem', lineHeight: '1.6', margin: 0 }}>{data.ai_strategy.customer_sentiment}</p>
                  </div>
                )}
                {data.ai_strategy.pricing_analysis && (
                  <div className="glass-card" style={{ flex: '1 1 300px', borderRadius: '16px', padding: '25px', borderLeft: '3px solid #fbbf24' }}>
                    <h3 style={{ margin: '0 0 12px 0', color: '#f8fafc', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span>💰</span> Pricing Analysis
                    </h3>
                    <p style={{ color: '#cbd5e1', fontSize: '0.9rem', lineHeight: '1.6', margin: 0 }}>{data.ai_strategy.pricing_analysis}</p>
                  </div>
                )}
                {data.ai_strategy.risks && (
                  <div className="glass-card" style={{ flex: '1 1 300px', borderRadius: '16px', padding: '25px', borderLeft: '3px solid #ef4444' }}>
                    <h3 style={{ margin: '0 0 12px 0', color: '#f8fafc', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span>⚠️</span> Risks
                    </h3>
                    <p style={{ color: '#cbd5e1', fontSize: '0.9rem', lineHeight: '1.6', margin: 0 }}>{data.ai_strategy.risks}</p>
                  </div>
                )}
                {data.ai_strategy.competitive_insights && (
                  <div className="glass-card" style={{ flex: '1 1 300px', borderRadius: '16px', padding: '25px', borderLeft: '3px solid #10b981' }}>
                    <h3 style={{ margin: '0 0 12px 0', color: '#f8fafc', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span>🏆</span> Competitive Insights
                    </h3>
                    <p style={{ color: '#cbd5e1', fontSize: '0.9rem', lineHeight: '1.6', margin: 0 }}>{data.ai_strategy.competitive_insights}</p>
                  </div>
                )}
              </div>
            )}

            <div className="responsive-grid" style={{ marginBottom: '35px' }}>
              {[
                { label: 'AI Confidence', value: data.ai_strategy.market_health.ai_confidence, color: '#38bdf8' },
                { label: 'Market Opportunity', value: data.ai_strategy.market_health.opportunity_score, color: '#fbbf24' },
                { label: 'Competition Intensity', value: data.ai_strategy.market_health.competition, color: '#ef4444' },
                { label: 'Trend Momentum', value: data.ai_strategy.market_health.trend_momentum, color: '#10b981' }
              ].map((metric, i) => {
                const val = String(metric.value || 'N/A');
                // opportunity_score already contains "/10", confidence contains "%"
                // For plain text values (HIGH/MEDIUM/STRONG) just display as-is
                const isPercent = val.includes('%') && !val.includes('/');
                const isScore   = val.includes('/10');
                return (
                  <div key={i} className="glass-card" style={{ borderRadius: '12px', padding: '25px 20px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', position: 'relative', overflow: 'hidden' }}>
                    <div style={{ position: 'absolute', bottom: 0, left: 0, width: '100%', height: '3px', backgroundColor: metric.color, opacity: 0.8 }}></div>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px', textAlign: 'center' }}>{metric.label}</div>
                    <div style={{ fontSize: '2rem', fontWeight: '900', color: '#f8fafc', textShadow: `0 0 15px ${metric.color}60` }}>
                      {isPercent ? (
                        <AnimatedCounter value={val} suffix="%" />
                      ) : isScore ? (
                        <span>{val}</span>
                      ) : (
                        <span>{val}</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="responsive-flex" style={{ marginBottom: '35px' }}>
              <div className="glass-card" style={{ flex: '1 1 500px', borderRadius: '16px', padding: '30px' }}>
                <h3 style={{ margin: '0 0 25px 0', color: '#f8fafc', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ color: '#38bdf8' }}>⚡</span> Recommended Strategic Actions
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {data.ai_strategy.actionable_steps.map((action, i) => (
                    <div key={i} style={{ display: 'flex', gap: '15px', alignItems: 'center', backgroundColor: 'rgba(15, 23, 42, 0.4)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.03)' }}>
                      <div style={{ backgroundColor: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', width: '26px', height: '26px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.85rem', fontWeight: 'bold', flexShrink: 0 }}>
                        {i + 1}
                      </div>
                      <div style={{ color: '#e2e8f0', fontSize: '0.95rem' }}>{action}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ flex: '1 1 300px', display: 'flex', flexDirection: 'column', gap: '25px' }}>
                {/* Fix 3: only show Live Market Alerts when real alerts exist */}
                {(() => {
                  const alerts = data.ai_strategy.live_alerts || [];
                  const realAlerts = alerts.filter(a =>
                    a && a !== 'No significant market alerts detected.' &&
                    !a.startsWith('Insufficient data')
                  );
                  if (realAlerts.length === 0) return null;
                  return (
                <div className="glass-card" style={{ flex: 1, borderRadius: '16px', padding: '25px', borderLeft: '3px solid #ef4444' }}>
                  <h3 style={{ margin: '0 0 20px 0', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.1rem' }}>
                    <span>🚨</span> Live Market Alerts
                  </h3>
                  {realAlerts.map((alert, i) => (
                    <div key={i} style={{ backgroundColor: 'rgba(239, 68, 68, 0.08)', padding: '12px 15px', borderRadius: '6px', marginBottom: '10px', fontSize: '0.9rem', color: '#fecaca', border: '1px solid rgba(239, 68, 68, 0.15)' }}>
                      {alert}
                    </div>
                  ))}
                </div>
                  );
                })()}
                <div className="glass-card" style={{ flex: 1, borderRadius: '16px', padding: '25px', borderLeft: '3px solid #10b981' }}>
                  <h3 style={{ margin: '0 0 20px 0', color: '#f8fafc', fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span>📈</span> Emerging Trends
                  </h3>
                  {data.ai_strategy.trends.map((trend, i) => (
                    <div key={i} style={{ fontSize: '0.95rem', marginBottom: '12px', color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ color: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.15)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.7rem' }}>+</span> 
                      {trend}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="responsive-flex" style={{ marginBottom: '35px' }}>
              <div className="glass-card" style={{ flex: '1 1 400px', borderRadius: '16px', padding: '30px' }}>
                <h3 style={{ margin: '0 0 25px 0', color: '#f8fafc', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{color: '#8b5cf6'}}>🕵️</span> Why This Opportunity Exists
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                  {data.ai_strategy.reasoning.map((r, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'stretch' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginRight: '20px' }}>
                         <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#8b5cf6', marginTop: '6px', boxShadow: '0 0 8px rgba(139, 92, 246, 0.6)' }}></div>
                         {i !== data.ai_strategy.reasoning.length - 1 && <div style={{ width: '2px', height: '100%', backgroundColor: 'rgba(139, 92, 246, 0.2)', margin: '8px 0' }}></div>}
                      </div>
                      <div style={{ paddingBottom: '25px', color: '#cbd5e1', fontSize: '0.95rem', lineHeight: '1.6' }}>{r}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Fix 2: only render Customer Review Intelligence when real data exists */}
              {(() => {
                const ri = data.ai_strategy.review_intelligence || {};
                const complaints = ri.top_complaints || [];
                const praises = ri.top_praises || [];
                const snippets = ri.snippets || [];
                const hasData = complaints.length > 0 || praises.length > 0 || snippets.length > 0;
                if (!hasData) return null;
                return (
              <div className="glass-card" style={{ flex: '1.5 1 500px', borderRadius: '16px', padding: '30px' }}>
                <h3 style={{ margin: '0 0 25px 0', color: '#f8fafc', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span>🗣️</span> Customer Review Intelligence
                </h3>
                {(() => {
                  const note = ri.note || '';
                  return (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      <div className="responsive-flex" style={{ gap: '20px' }}>
                        <div style={{ flex: '1 1 200px', backgroundColor: 'rgba(239,68,68,0.05)', padding: '20px', borderRadius: '10px', border: '1px solid rgba(239,68,68,0.1)' }}>
                          <h4 style={{ color: '#f87171', margin: '0 0 15px 0', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Top Complaints</h4>
                          {complaints.length > 0 ? (
                            <ul style={{ paddingLeft: '20px', margin: 0, fontSize: '0.9rem', color: '#fecaca', lineHeight: '1.8' }}>
                              {complaints.map((c, i) => <li key={i}>{c}</li>)}
                            </ul>
                          ) : (
                            <p style={{ color: '#64748b', fontSize: '0.85rem', fontStyle: 'italic', margin: 0 }}>No complaint data available.</p>
                          )}
                        </div>
                        <div style={{ flex: '1 1 200px', backgroundColor: 'rgba(16,185,129,0.05)', padding: '20px', borderRadius: '10px', border: '1px solid rgba(16,185,129,0.1)' }}>
                          <h4 style={{ color: '#34d399', margin: '0 0 15px 0', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Top Praises</h4>
                          {praises.length > 0 ? (
                            <ul style={{ paddingLeft: '20px', margin: 0, fontSize: '0.9rem', color: '#a7f3d0', lineHeight: '1.8' }}>
                              {praises.map((p, i) => <li key={i}>{p}</li>)}
                            </ul>
                          ) : (
                            <p style={{ color: '#64748b', fontSize: '0.85rem', fontStyle: 'italic', margin: 0 }}>No praise data available.</p>
                          )}
                        </div>
                      </div>
                      {snippets.length > 0 && (
                        <div style={{ backgroundColor: 'rgba(56,189,248,0.04)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(56,189,248,0.1)' }}>
                          <h4 style={{ color: '#38bdf8', margin: '0 0 12px 0', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Raw Review Snippets ({snippets.length})</h4>
                          {snippets.map((s, i) => (
                            <div key={i} style={{ fontSize: '0.8rem', color: '#94a3b8', fontStyle: 'italic', marginBottom: '8px', borderLeft: '2px solid rgba(56,189,248,0.3)', paddingLeft: '10px' }}>
                              "{s}"
                            </div>
                          ))}
                        </div>
                      )}
                      {note && (
                        <div style={{ fontSize: '0.72rem', color: '#475569', fontStyle: 'italic' }}>ℹ️ {note}</div>
                      )}
                    </div>
                  );
                })()}
              </div>
                );
              })()}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
              <div className="glass-card" style={{ padding: '30px', borderRadius: '16px' }}>
                <h3 style={{ margin: '0 0 8px 0', color: '#f8fafc', fontSize: '1.2rem' }}>📊 Brand Pricing Landscape</h3>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '20px' }}>Average price per brand · {brandChartData.length} brands · bars coloured by tier</div>
                {brandChartData.length === 0 ? (
                  <div style={{ height: '100px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569', fontSize: '0.9rem', fontStyle: 'italic' }}>
                    No brand pricing data available.
                  </div>
                ) : (
                <div style={{ height: '350px' }}>
                  <ResponsiveContainer>
                    <BarChart data={brandChartData} margin={{ top: 30, right: 30, left: 10, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false}/>
                      <XAxis dataKey="brand" stroke="#94a3b8" axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 12}} dy={10} />
                      <YAxis stroke="#94a3b8" axisLine={false} tickLine={false} tickFormatter={(v) => `₹${v.toLocaleString()}`} tick={{fontSize: 11}} />
                      <Tooltip
                        cursor={{fill: 'rgba(255,255,255,0.03)'}}
                        contentStyle={{ backgroundColor: 'rgba(15,23,42,0.95)', border: '1px solid #38bdf8', borderRadius: '8px', color: '#fff' }}
                        formatter={(value, name, props) => {
                          const d = props.payload;
                          return [
                            `₹${value.toLocaleString()} avg · ${d.product_count} product${d.product_count > 1 ? 's' : ''}${d.avg_rating ? ` · ★${d.avg_rating}` : ''}`,
                            'Avg Price'
                          ];
                        }}
                      />
                      <ReferenceLine y={avgOfAvgs} stroke="#fbbf24" strokeDasharray="4 4"
                        label={{ position: 'top', value: `Market Avg: ₹${avgOfAvgs.toLocaleString()}`, fill: '#fbbf24', fontSize: 11, fontWeight: 'bold', dy: -8 }} />
                      <Bar dataKey="avg_price" radius={[4,4,0,0]} barSize={50} animationDuration={1500}>
                        {brandChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.avg_price > avgOfAvgs ? 'url(#colorPremium)' : 'url(#colorBudget)'} />
                        ))}
                      </Bar>
                      <defs>
                        <linearGradient id="colorBudget" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.9}/>
                          <stop offset="95%" stopColor="#0284c7" stopOpacity={0.2}/>
                        </linearGradient>
                        <linearGradient id="colorPremium" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#818cf8" stopOpacity={0.9}/>
                          <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.2}/>
                        </linearGradient>
                      </defs>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                )}
              </div>

              <div style={{ marginBottom: '20px' }}>
                 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '20px' }}>
                    <h3 style={{ margin: 0, color: '#e2e8f0', fontSize: '1.2rem' }}>🗃️ Market Entities</h3>
                 </div>
                 
                 <div className="premium-scrollbar" style={{ display: 'flex', gap: '20px', overflowX: 'auto', paddingBottom: '20px' }}>
                  {data.market_data.map((item, idx) => (
                    <div key={idx} className="glass-card" style={{ 
                      minWidth: '250px', borderRadius: '12px', padding: '0', 
                      position: 'relative', overflow: 'hidden'
                    }}>
                      <div style={{ height: '160px', width: '100%', overflow: 'hidden', position: 'relative', backgroundColor: '#fff' }}>
                         {/* 🚨 YAHAN REAL IMAGE LINK USE HO RAHA HAI 👇 */}
                         <img 
                            src={item.image_url} 
                            alt={item.brand} 
                            style={{ width: '100%', height: '100%', objectFit: 'contain', backgroundColor: '#fff', padding: '10px' }} 
                            onError={(e) => { e.target.style.display = 'none'; }}
                         />
                         <div style={{ position: 'absolute', bottom: '10px', left: '10px', backgroundColor: 'rgba(15,23,42,0.85)', backdropFilter: 'blur(4px)', color: '#fff', padding: '4px 10px', borderRadius: '20px', fontSize: '0.65rem', fontWeight: 'bold', border: '1px solid rgba(255,255,255,0.1)' }}>
                            {item.market_position}
                         </div>
                      </div>
                      
                      <div style={{ padding: '20px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                           <h4 style={{ margin: 0, color: '#f8fafc', fontSize: '1.1rem', fontWeight: 'bold' }}>{item.brand}</h4>
                           <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                             <div style={{ fontSize: '0.65rem', color: '#94a3b8', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.08)' }}>
                               {item.platform}
                             </div>
                             {item.refurbished && (
                               <div style={{ fontSize: '0.65rem', color: '#f59e0b', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(245,158,11,0.3)', backgroundColor: 'rgba(245,158,11,0.08)' }}>
                                 REFURB
                               </div>
                             )}
                           </div>
                        </div>
                        <div style={{ fontSize: '1.6rem', fontWeight: '900', color: '#f8fafc', marginBottom: '15px', letterSpacing: '-1px' }}>{item.price}</div>
                        
                        <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '15px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            {item.rating != null ? (
                              <div style={{ fontSize: '0.8rem', color: '#fbbf24' }}>
                                {'★'.repeat(Math.round(item.rating))}{'☆'.repeat(5 - Math.round(item.rating))}
                                <span style={{ color: '#94a3b8', marginLeft: '5px', fontSize: '0.7rem' }}>{item.rating}</span>
                              </div>
                            ) : (
                              <div style={{ fontSize: '0.7rem', color: '#64748b' }}>No rating</div>
                            )}
                            {item.review_count != null ? (
                              <div style={{ fontSize: '0.65rem', color: '#94a3b8' }}>{item.review_count.toLocaleString()} reviews</div>
                            ) : null}
                          </div>
                          {item.reviews && item.reviews.length > 0 && (
                            <div style={{ marginTop: '8px' }}>
                              {item.reviews.slice(0, 2).map((rv, ri) => (
                                <div key={ri} style={{ fontSize: '0.72rem', color: '#94a3b8', fontStyle: 'italic', marginBottom: '4px', borderLeft: '2px solid rgba(56,189,248,0.3)', paddingLeft: '8px' }}>
                                  "{rv}"
                                </div>
                              ))}
                            </div>
                          )}
                          <div style={{ marginTop: '8px' }}>
                            {item.clean_price > avgPrice ? (
                              <div style={{ fontSize: '0.65rem', backgroundColor: 'rgba(245, 158, 11, 0.1)', color: '#fbbf24', padding: '4px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block' }}>🔴 High Price</div>
                            ) : (
                              <div style={{ fontSize: '0.65rem', backgroundColor: 'rgba(16, 185, 129, 0.1)', color: '#34d399', padding: '4px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block' }}>🟢 Strong Value</div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

          </div>
        ) : (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#475569' }}>
            <div style={{ position: 'relative', width: '100px', height: '100px', marginBottom: '25px' }}>
               <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, border: '1px solid rgba(71,85,105,0.5)', borderRadius: '50%', animation: 'pulseGlow 3s infinite' }}></div>
               <div style={{ position: 'absolute', top: '10px', left: '10px', right: '10px', bottom: '10px', border: '1px dashed #475569', borderRadius: '50%', animation: 'spin 20s linear infinite' }}></div>
               <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', fontSize: '2rem' }}>🛰️</div>
            </div>
            <h2 style={{ letterSpacing: '3px', fontWeight: '400', color: '#64748b', margin: '0 0 10px 0', fontSize: '1.1rem' }}>SYSTEM STANDBY</h2>
            <p style={{ fontSize: '0.85rem' }}>Awaiting market vector for intelligence sweep.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;