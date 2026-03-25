import { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import api from '../services/api';
import {
  Wallet, AlertTriangle, Clock, TrendingDown, TrendingUp,
  Calendar, BarChart2, History, ArrowDownCircle, ArrowUpCircle
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine
} from 'recharts';

function fmt(n) { return Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 }); }
function fmtDate(d) { return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }); }
function fmtShort(d) { return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }); }

const RISK_STYLE = {
  SAFE: { card: 'text-green-700 bg-green-50 border-green-200', badge: 'bg-green-100 text-green-700', dot: 'bg-green-500' },
  WARNING: { card: 'text-yellow-700 bg-yellow-50 border-yellow-200', badge: 'bg-yellow-100 text-yellow-700', dot: 'bg-yellow-500' },
  CRITICAL: { card: 'text-red-700 bg-red-50 border-red-200', badge: 'bg-red-100 text-red-700', dot: 'bg-red-500' },
};

const TABS = [
  { id: 'overview', label: 'Overview', icon: <BarChart2 size={16}/> },
  { id: 'timeline', label: 'Timeline', icon: <TrendingDown size={16}/> },
  { id: 'inflows', label: 'Inflows', icon: <ArrowUpCircle size={16}/> },
  { id: 'outflows', label: 'Outflows', icon: <ArrowDownCircle size={16}/> },
  { id: 'upcoming', label: 'Upcoming Payments', icon: <Calendar size={16}/> },
];

export default function Dashboard() {
  const { userId } = useContext(AuthContext);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('overview');

  const load = async () => {
    setLoading(true); setError('');
    try {
      const [stateRes, runwayRes] = await Promise.all([
        api.get(`/state/${userId}`),
        api.get(`/runway/${userId}`),
      ]);
      const state = stateRes.data;
      const runway = runwayRes.data;

      let timeline = [];
      try {
        const simRes = await api.post('/simulate', {
          user_id: userId, outflows: [], inflows: [], horizon_days: 90,
        });
        timeline = (simRes.data.timeline || []).map(d => ({
          date: d.date,
          balance: typeof d.balance === 'number' ? d.balance : parseFloat(d.balance),
          events: d.events || [],
        }));
      } catch {}

      setData({
        cash: parseFloat(state.cash_balance),
        name: state.name,
        runway: runway.runway_days,
        risk: runway.risk_level || 'SAFE',
        crashDate: runway.crash_date,
        inflows: state.inflows || [],
        outflows: state.outflows || [],
        future_payments: state.future_payments || [],
        assets: state.assets || [],
        timeline,
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load dashboard.');
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [userId]);

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"/>
    </div>
  );
  if (error) return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center gap-4">
      <AlertTriangle className="text-red-400" size={40}/>
      <p className="text-red-600 font-medium">{error}</p>
      <button onClick={load} className="text-blue-600 text-sm underline">Retry</button>
    </div>
  );

  const risk = RISK_STYLE[data.risk] || RISK_STYLE.SAFE;
  const totalFuture = data.future_payments.reduce((s, e) => s + parseFloat(e.amount), 0);
  const totalInflow = data.inflows.reduce((s, e) => s + parseFloat(e.amount), 0);

  // Fallback chart: linear depletion if no simulation data
  const chartData = data.timeline.length > 0 ? data.timeline
    : Array.from({ length: 90 }, (_, i) => ({
        date: new Date(Date.now() + i * 86400000).toISOString().split('T')[0],
        balance: Math.max(0, data.cash - i * (data.cash / Math.max(data.runway || 90, 1))),
      }));

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Financial Overview</h1>
          <p className="text-slate-500 text-sm mt-0.5">Welcome, <strong>{data.name}</strong></p>
        </div>
        <button onClick={load} className="text-sm text-slate-400 hover:text-blue-600 flex items-center gap-1 transition-colors">
          <History size={14}/> Refresh
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-start gap-4">
          <div className="bg-blue-100 p-3 rounded-xl shrink-0"><Wallet size={22} className="text-blue-600"/></div>
          <div>
            <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">Cash Balance</p>
            <p className="text-2xl font-bold text-slate-800 mt-0.5">₹{fmt(data.cash)}</p>
            <p className="text-xs text-slate-400 mt-0.5">{data.inflows.length} inflows · {data.outflows.length} outflows on record</p>
          </div>
        </div>
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-start gap-4">
          <div className="bg-purple-100 p-3 rounded-xl shrink-0"><Clock size={22} className="text-purple-600"/></div>
          <div>
            <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">Cash Runway</p>
            <p className="text-2xl font-bold text-slate-800 mt-0.5">{data.runway === null ? '90+ Days' : `${data.runway} Days`}</p>
            {data.crashDate && <p className="text-xs text-red-400 mt-0.5">Zero by {fmtDate(data.crashDate)}</p>}
          </div>
        </div>
        <div className={`p-5 rounded-2xl border flex items-start gap-4 ${risk.card}`}>
          <div className="p-3 bg-white/60 rounded-xl shrink-0"><AlertTriangle size={22}/></div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide opacity-70">Risk Level</p>
            <p className="text-2xl font-bold mt-0.5">{data.risk}</p>
            <p className="text-xs opacity-60 mt-0.5">₹{fmt(totalFuture)} upcoming · ₹{fmt(totalInflow)} inflows logged</p>
          </div>
        </div>
      </div>

      {/* Tab bar */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="flex border-b border-slate-200 bg-slate-50 overflow-x-auto">
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium whitespace-nowrap transition-colors ${
                tab === t.id
                  ? 'bg-white text-blue-600 border-b-2 border-blue-600'
                  : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'
              }`}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        <div className="p-6">
          {/* OVERVIEW */}
          {tab === 'overview' && (
            <div className="space-y-4">
              <p className="text-sm text-slate-500 font-medium">90-Day Cash Flow Projection</p>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <defs>
                      <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.18}/>
                        <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0"/>
                    <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill:'#94A3B8', fontSize:11 }} dy={8}
                      tickFormatter={v => fmtShort(v)} interval={Math.floor(chartData.length / 6)}/>
                    <YAxis axisLine={false} tickLine={false} tick={{ fill:'#94A3B8', fontSize:11 }} dx={-8}
                      tickFormatter={v => `₹${(v/1000).toFixed(0)}k`}/>
                    <Tooltip contentStyle={{ borderRadius:'12px', border:'none', boxShadow:'0 4px 20px rgba(0,0,0,.1)' }}
                      formatter={v => [`₹${fmt(v)}`, 'Balance']} labelFormatter={l => fmtDate(l)}/>
                    <ReferenceLine y={0} stroke="#EF4444" strokeDasharray="4 4" strokeWidth={1.5}/>
                    <Area type="monotone" dataKey="balance" stroke="#3B82F6" strokeWidth={2.5}
                      fill="url(#grad)" dot={false} activeDot={{ r:5, strokeWidth:0, fill:'#3B82F6' }}/>
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              {/* Assets */}
              {data.assets.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Declared Assets</p>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {data.assets.map((a, i) => (
                      <div key={i} className="bg-slate-50 border border-slate-100 rounded-xl p-3">
                        <p className="text-xs text-slate-500 capitalize">{a.asset_type}</p>
                        <p className="font-semibold text-slate-800 text-sm">{a.name || a.asset_type}</p>
                        <p className="text-sm font-bold text-green-600 mt-1">₹{fmt(a.estimated_value)}</p>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${a.liquidity === 'high' ? 'bg-green-100 text-green-700' : a.liquidity === 'medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
                          {a.liquidity} liquidity
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TIMELINE */}
          {tab === 'timeline' && (
            <div>
              <p className="text-sm text-slate-500 mb-4 font-medium">Day-by-day cash balance projection for the next 90 days</p>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <defs>
                      <linearGradient id="grad2" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0"/>
                    <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill:'#94A3B8', fontSize:11 }} dy={8}
                      tickFormatter={v => fmtShort(v)} interval={13}/>
                    <YAxis axisLine={false} tickLine={false} tick={{ fill:'#94A3B8', fontSize:11 }} dx={-8}
                      tickFormatter={v => `₹${(v/1000).toFixed(0)}k`}/>
                    <Tooltip contentStyle={{ borderRadius:'12px', border:'none', boxShadow:'0 4px 20px rgba(0,0,0,.1)' }}
                      formatter={v => [`₹${fmt(v)}`, 'Balance']} labelFormatter={l => fmtDate(l)}/>
                    <ReferenceLine y={0} stroke="#EF4444" strokeDasharray="4 4" strokeWidth={2}/>
                    <Area type="monotone" dataKey="balance" stroke="#8B5CF6" strokeWidth={2.5}
                      fill="url(#grad2)" dot={false} activeDot={{ r:5, strokeWidth:0, fill:'#8B5CF6' }}/>
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="text-xs text-slate-400 font-semibold border-b border-slate-100">
                    <td className="pb-2 pr-4">Date</td>
                    <td className="pb-2 pr-4 text-right">Balance</td>
                    <td className="pb-2">Events</td>
                  </tr></thead>
                  <tbody>
                    {chartData.filter((_, i) => i % 7 === 0).map((d, i) => (
                      <tr key={i} className="border-b border-slate-50 hover:bg-slate-50">
                        <td className="py-2 pr-4 text-slate-600">{fmtDate(d.date)}</td>
                        <td className={`py-2 pr-4 text-right font-semibold ${d.balance <= 0 ? 'text-red-600' : 'text-slate-800'}`}>₹{fmt(d.balance)}</td>
                        <td className="py-2 text-slate-400 text-xs">{(d.events || []).map(e => e.description).join(', ') || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* INFLOWS */}
          {tab === 'inflows' && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-semibold text-slate-700">All Recorded Inflows</p>
                <span className="text-xs bg-green-100 text-green-700 px-3 py-1 rounded-full font-semibold">
                  Total: ₹{fmt(totalInflow)}
                </span>
              </div>
              {data.inflows.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <ArrowUpCircle className="mx-auto mb-3 text-slate-300" size={32}/>
                  <p>No inflows recorded yet. Use the Input Panel to add them.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {data.inflows.map((e, i) => (
                    <div key={i} className="flex items-center justify-between p-4 bg-slate-50 hover:bg-green-50 rounded-xl transition-colors border border-transparent hover:border-green-100">
                      <div>
                        <p className="font-medium text-slate-800">{e.description || 'Inflow'}</p>
                        <p className="text-xs text-slate-400 mt-0.5">{fmtDate(e.date)} · <span className="uppercase">{e.source}</span> · Confidence: {(parseFloat(e.confidence_score)*100).toFixed(0)}%</p>
                      </div>
                      <span className="font-bold text-green-600 text-base">+₹{fmt(e.amount)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* OUTFLOWS */}
          {tab === 'outflows' && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-semibold text-slate-700">All Past Outflows</p>
                <span className="text-xs bg-red-100 text-red-700 px-3 py-1 rounded-full font-semibold">
                  Total: ₹{fmt(data.outflows.reduce((s, e) => s + parseFloat(e.amount), 0))}
                </span>
              </div>
              {data.outflows.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <ArrowDownCircle className="mx-auto mb-3 text-slate-300" size={32}/>
                  <p>No past outflows recorded.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {data.outflows.map((e, i) => (
                    <div key={i} className="flex items-center justify-between p-4 bg-slate-50 hover:bg-red-50 rounded-xl transition-colors border border-transparent hover:border-red-100">
                      <div>
                        <p className="font-medium text-slate-800">{e.description || 'Outflow'}</p>
                        <p className="text-xs text-slate-400 mt-0.5">{fmtDate(e.date)} · <span className="uppercase">{e.source}</span></p>
                      </div>
                      <span className="font-bold text-red-600 text-base">-₹{fmt(e.amount)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* UPCOMING PAYMENTS */}
          {tab === 'upcoming' && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-semibold text-slate-700">Scheduled Future Payments</p>
                <span className="text-xs bg-orange-100 text-orange-700 px-3 py-1 rounded-full font-semibold">
                  Total: ₹{fmt(totalFuture)}
                </span>
              </div>
              {data.future_payments.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <Calendar className="mx-auto mb-3 text-slate-300" size={32}/>
                  <p>No upcoming payments scheduled. Use the Input Panel to add future payments.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {data.future_payments
                    .sort((a, b) => new Date(a.date) - new Date(b.date))
                    .map((e, i) => {
                      const daysLeft = Math.ceil((new Date(e.date) - Date.now()) / 86400000);
                      const urgency = daysLeft <= 3 ? 'bg-red-100 text-red-700' : daysLeft <= 7 ? 'bg-orange-100 text-orange-700' : daysLeft <= 14 ? 'bg-yellow-100 text-yellow-700' : 'bg-slate-100 text-slate-600';
                      return (
                        <div key={i} className="flex items-center justify-between p-4 bg-slate-50 hover:bg-orange-50 rounded-xl transition-colors border border-transparent hover:border-orange-100">
                          <div>
                            <p className="font-medium text-slate-800">{e.description || 'Payment'}</p>
                            <p className="text-xs text-slate-400 mt-0.5">{fmtDate(e.date)}</p>
                          </div>
                          <div className="text-right">
                            <p className="font-bold text-slate-800">-₹{fmt(e.amount)}</p>
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full mt-1 inline-block ${urgency}`}>
                              {daysLeft <= 0 ? 'Overdue' : `In ${daysLeft}d`}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
