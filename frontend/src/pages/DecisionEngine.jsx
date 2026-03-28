import { useState, useEffect, useContext, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import api from '../services/api';
import {
  Play, CheckCircle2, XCircle, CreditCard, RefreshCw,
  AlertTriangle, Info, ChevronDown, ChevronUp, ExternalLink,
  FileText, Loader2, Mail, Unplug
} from 'lucide-react';

function fmt(n) { return Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 }); }
function fmtDate(d) { return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }); }

// Gateway modal to simulate payment
function PaymentGatewayModal({ item, onSuccess, onClose }) {
  const [processing, setProcessing] = useState(false);
  const { userId } = useContext(AuthContext);

  const confirm = async () => {
    setProcessing(true);
    try {
      const res = await api.post('/pay', { amount: item.amount, description: item.description });
      // Pass back the server-confirmed new balance
      onSuccess(item.description, res.data.new_balance);
    } catch (err) {
      alert(err.response?.data?.detail || 'Payment failed');
    } finally { setProcessing(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full p-6" onClick={e => e.stopPropagation()}>
        <div className="text-center mb-6">
          <div className="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <CreditCard className="text-blue-600" size={26}/>
          </div>
          <h3 className="text-lg font-bold text-slate-800">Confirm Payment</h3>
          <p className="text-slate-500 text-sm mt-1">Via Dummy Payment Gateway</p>
        </div>
        <div className="bg-slate-50 rounded-xl p-4 mb-6 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-slate-500">Payee</span>
            <span className="font-semibold text-slate-800 text-right max-w-[60%] truncate">{item.description}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-500">Amount</span>
            <span className="font-bold text-slate-900 text-lg">₹{fmt(item.amount)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-500">Method</span>
            <span className="text-slate-600">Simulated UPI / NEFT</span>
          </div>
        </div>
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 border border-slate-200 text-slate-600 py-2.5 rounded-xl font-medium hover:bg-slate-50">Cancel</button>
          <button onClick={confirm} disabled={processing}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2.5 rounded-xl font-bold disabled:opacity-60 flex items-center justify-center gap-2">
            {processing ? <Loader2 size={16} className="animate-spin"/> : <CheckCircle2 size={16}/>}
            {processing ? 'Processing…' : 'Pay Now'}
          </button>
        </div>
      </div>
    </div>
  );
}

function NegotiationMailModal({ item, mailConnected, onConnectMail, onClose, onSent }) {
  const [toEmail, setToEmail] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!toEmail.trim() || !toEmail.includes('@')) {
      alert('Enter the recipient email address (To).');
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post('/mail/negotiation', {
        obligation_description: item.description,
        amount: item.amount,
        days_to_due: item.days_to_due,
        to_email: toEmail.trim(),
        note: null,
        send_now: true,
      });
      onSent(data);
      onClose();
    } catch (err) {
      alert(err.response?.data?.detail || 'Could not send email.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
          <Mail className="text-blue-600" size={22} /> Send negotiation email
        </h3>
        <p className="text-sm text-slate-500 mt-1">{item.description} — ₹{fmt(item.amount)} · due in {item.days_to_due}d</p>
        <p className="text-xs text-slate-400 mt-2">Subject and body are filled automatically. Microsoft Graph sends immediately.</p>

        {!mailConnected ? (
          <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-900">
            <p className="font-medium">Connect Microsoft 365 first</p>
            <p className="mt-1 text-amber-800/90">We use OAuth — CashPilot never sees your password.</p>
            <button type="button" onClick={onConnectMail}
              className="mt-3 w-full bg-slate-900 text-white font-semibold py-2.5 rounded-lg text-sm">
              Connect Microsoft 365
            </button>
          </div>
        ) : (
          <>
            <label className="block mt-4 text-xs font-semibold text-slate-600">To</label>
            <input type="email" value={toEmail} onChange={e => setToEmail(e.target.value)}
              placeholder="creditor@example.com"
              autoFocus
              className="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm" />
            <div className="flex gap-3 mt-5">
              <button type="button" onClick={onClose} className="flex-1 border border-slate-200 text-slate-600 py-2.5 rounded-xl font-medium">Cancel</button>
              <button type="button" onClick={submit} disabled={busy}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2.5 rounded-xl font-bold disabled:opacity-60 flex items-center justify-center gap-2">
                {busy ? <Loader2 size={16} className="animate-spin" /> : <Mail size={16} />}
                {busy ? 'Sending…' : 'Send now'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function DecisionEngine() {
  const { userId } = useContext(AuthContext);
  const location = useLocation();
  const [stateLoading, setStateLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [obligations, setObligations] = useState([]);
  const [inflows, setInflows] = useState([]);
  const [currentCash, setCurrentCash] = useState(0);
  const [paidItems, setPaidItems] = useState({}); // description → true
  const [payTarget, setPayTarget] = useState(null); // item to pay via modal
  const [expandedIdx, setExpandedIdx] = useState(null);
  const [mailStatus, setMailStatus] = useState({ connected: false, account_email: null });
  const [mailToast, setMailToast] = useState('');
  const [mailModalItem, setMailModalItem] = useState(null);

  const loadMailStatus = useCallback(async () => {
    try {
      const res = await api.get('/mail/status');
      setMailStatus(res.data);
    } catch (err) {
      setMailStatus({ connected: false, account_email: null });
      if (err.response?.status === 401) {
        setMailToast('Your session expired. Log in again, then reconnect Microsoft 365 if needed.');
      }
    }
  }, []);

  const startMailOAuth = async () => {
    try {
      const res = await api.get('/mail/microsoft/authorize', {
        params: { frontend_origin: window.location.origin },
      });
      window.location.href = res.data.authorization_url;
    } catch (err) {
      alert(err.response?.data?.detail || 'Mail sign-in is not available. Check server configuration.');
    }
  };

  const disconnectMail = async () => {
    if (!confirm('Disconnect Microsoft 365 from CashPilot?')) return;
    try {
      await api.delete('/mail/disconnect');
      await loadMailStatus();
    } catch (err) {
      alert(err.response?.data?.detail || 'Could not disconnect.');
    }
  };

  const loadState = async () => {
    setStateLoading(true); setError('');
    try {
      const res = await api.get(`/state/${userId}`);
      const state = res.data;
      setCurrentCash(parseFloat(state.cash_balance));

      const today = new Date();
      // Map every future payment into obligation format
      const obs = (state.future_payments || []).map(e => {
        const daysLeft = Math.max(0, Math.ceil((new Date(e.date) - today) / 86400000));
        return {
          amount: parseFloat(e.amount),
          due_date: e.date,
          days_to_due: daysLeft,
          // Derive penalty from flexibility: low flex = high penalty
          penalty_score: e.flexibility <= 3 ? 9 : e.flexibility <= 6 ? 5 : 2,
          flexibility: e.flexibility,
          relationship_score: 5,
          description: e.description || 'Payment',
        };
      }).sort((a, b) => a.days_to_due - b.days_to_due); // sort by urgency

      // Use recent inflows as expected inflows
      const inf = (state.inflows || []).slice(0, 10).map(e => ({
        amount: parseFloat(e.amount),
        expected_date: e.date,
        confidence: parseFloat(e.confidence_score || 0.8),
        description: e.description || 'Inflow',
      }));

      setObligations(obs);
      setInflows(inf);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load your financial data.');
    } finally { setStateLoading(false); }
  };

  useEffect(() => { loadState(); }, [userId]);
  useEffect(() => { loadMailStatus(); }, [userId, loadMailStatus]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('mail_connected') === '1') {
      setMailToast('Microsoft 365 connected. Use Send on any obligation below — enter only the To: address.');
      loadMailStatus();
      window.history.replaceState({}, '', `${location.pathname}`);
    }
    const mer = params.get('mail_error');
    if (mer) {
      setError(decodeURIComponent(mer.replace(/\+/g, ' ')));
      window.history.replaceState({}, '', `${location.pathname}`);
    }
  }, [location.search, location.pathname, loadMailStatus]);

  useEffect(() => {
    const onVis = () => {
      if (document.visibilityState === 'visible') loadMailStatus();
    };
    const onFocus = () => loadMailStatus();
    document.addEventListener('visibilitychange', onVis);
    window.addEventListener('focus', onFocus);
    return () => {
      document.removeEventListener('visibilitychange', onVis);
      window.removeEventListener('focus', onFocus);
    };
  }, [loadMailStatus]);

  const runEngine = async () => {
    if (obligations.length === 0) {
      setError('No upcoming payments found. Add future obligations via the Input Panel first.');
      return;
    }
    setRunning(true); setError(''); setResult(null); setPaidItems({});
    try {
      const res = await api.post('/decide', {
        user_id: userId,
        obligations: obligations.map(o => ({
          amount: o.amount,
          due_date: o.due_date,
          penalty_score: o.penalty_score,
          flexibility: o.flexibility,
          relationship_score: o.relationship_score,
          description: o.description,
        })),
        inflows: inflows.map(i => ({
          amount: i.amount,
          expected_date: i.expected_date,
          confidence: i.confidence,
          description: i.description,
        })),
      });
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Engine error. Is the backend running?');
    } finally { setRunning(false); }
  };

  const onPaySuccess = (desc, newBalance) => {
    setPaidItems(prev => ({ ...prev, [desc]: true }));
    setPayTarget(null);
    // Use server-confirmed balance (the future entry was deleted server-side)
    if (newBalance !== undefined) {
      setCurrentCash(newBalance);
    }
    // Remove the paid obligation from the list so it can't be re-submitted
    setObligations(prev => prev.filter(o => o.description !== desc));
  };

  if (stateLoading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"/>
    </div>
  );

  const totalObligation = obligations.reduce((s, o) => s + o.amount, 0);
  const canPayAll = currentCash >= totalObligation;
  const payItems = result?.plan?.pay || [];
  const delayItems = result?.plan?.delay || [];
  const totalPaid = payItems.filter(i => paidItems[i.description]).reduce((s, i) => s + i.amount, 0);
  const remainingCash = currentCash - totalPaid;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Decision Engine</h1>
          <p className="text-slate-500 text-sm mt-1">
            ML-powered analysis of <strong>{obligations.length}</strong> upcoming payment{obligations.length !== 1 ? 's' : ''} against your cash balance of <strong>₹{fmt(currentCash)}</strong>
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={loadState} className="border border-slate-200 text-slate-500 hover:text-slate-700 px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 transition-colors">
            <RefreshCw size={15}/> Refresh
          </button>
          <button onClick={runEngine} disabled={running || obligations.length === 0}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 py-2 rounded-xl font-bold text-sm shadow-sm transition-all flex items-center gap-2">
            {running ? <Loader2 size={16} className="animate-spin"/> : <Play size={16}/>}
            {running ? 'Analysing…' : 'Run ML Engine'}
          </button>
        </div>
      </div>

      {mailToast && (
        <div className="bg-green-50 border border-green-200 p-4 rounded-xl flex items-start justify-between gap-3 text-green-800 text-sm">
          <span className="flex items-start gap-2"><CheckCircle2 size={18} className="shrink-0 mt-0.5"/> {mailToast}</span>
          <button type="button" onClick={() => setMailToast('')} className="text-green-700 font-medium hover:underline">Dismiss</button>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 p-4 rounded-xl flex items-start gap-3 text-red-700 text-sm">
          <AlertTriangle size={18} className="shrink-0 mt-0.5"/> {error}
        </div>
      )}

      <div className={`rounded-xl border p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 ${mailStatus.connected ? 'bg-slate-50 border-slate-200' : 'bg-blue-50/80 border-blue-100'}`}>
        <div className="flex items-start gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${mailStatus.connected ? 'bg-white border border-slate-200' : 'bg-white border border-blue-100'}`}>
            <Mail size={20} className={mailStatus.connected ? 'text-slate-600' : 'text-blue-600'} />
          </div>
          <div>
            <p className="font-semibold text-slate-800 text-sm">Negotiation mail (Microsoft 365)</p>
            <p className="text-xs text-slate-500 mt-0.5">
              {mailStatus.connected
                ? <>Signed in as <span className="font-medium text-slate-700">{mailStatus.account_email || 'your mailbox'}</span>. Click <strong>Send negotiation email</strong> on an obligation — you only enter the recipient (To).</>
                : <>Connect with OAuth — we store only an encrypted token. After connecting, use <strong>Send negotiation email</strong> on any bill row (no need to run ML first).</>}
            </p>
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          {mailStatus.connected ? (
            <button type="button" onClick={disconnectMail}
              className="px-4 py-2 rounded-lg text-sm font-medium border border-slate-200 bg-white text-slate-600 hover:bg-slate-100 flex items-center gap-2">
              <Unplug size={15} /> Disconnect
            </button>
          ) : (
            <button type="button" onClick={startMailOAuth}
              className="px-4 py-2 rounded-lg text-sm font-bold bg-blue-600 text-white hover:bg-blue-700 flex items-center gap-2">
              <ExternalLink size={15} /> Connect Microsoft 365
            </button>
          )}
        </div>
      </div>

      {/* Obligations Preview / Summary Banner */}
      {!result && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-slate-700">Upcoming Obligations to Evaluate</h3>
              <p className="text-xs text-slate-500 mt-0.5">All future payments from your records will be evaluated together</p>
            </div>
            {canPayAll
              ? <span className="text-xs bg-green-100 text-green-700 px-3 py-1.5 rounded-full font-semibold">✓ Sufficient cash to pay all</span>
              : <span className="text-xs bg-red-100 text-red-700 px-3 py-1.5 rounded-full font-semibold">⚠ Cash shortfall of ₹{fmt(totalObligation - currentCash)}</span>
            }
          </div>
          {obligations.length === 0 ? (
            <div className="text-center py-16">
              <FileText className="text-slate-300 mx-auto mb-3" size={36}/>
              <p className="text-slate-500 font-medium">No upcoming payments found</p>
              <p className="text-slate-400 text-sm mt-1">Go to <strong>Input Panel</strong> and add future obligations using natural language</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {obligations.map((o, i) => {
                const urgency = o.days_to_due <= 3 ? 'text-red-600 bg-red-50' : o.days_to_due <= 7 ? 'text-orange-600 bg-orange-50' : 'text-slate-500 bg-slate-100';
                return (
                  <div key={i} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-6 py-4 hover:bg-slate-50">
                    <div className="min-w-0">
                      <p className="font-medium text-slate-800">{o.description}</p>
                      <p className="text-xs text-slate-400 mt-0.5">Due {fmtDate(o.due_date)} · Penalty Risk: {o.penalty_score}/10 · Flexibility: {o.flexibility}/10</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                      <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${urgency}`}>
                        {o.days_to_due === 0 ? 'Overdue' : `In ${o.days_to_due}d`}
                      </span>
                      <span className="font-bold text-slate-800">₹{fmt(o.amount)}</span>
                      <button type="button" onClick={() => setMailModalItem(o)}
                        className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-blue-200 bg-blue-50 text-blue-800 hover:bg-blue-100 flex items-center gap-1.5 shrink-0">
                        <Mail size={14} /> Send email
                      </button>
                    </div>
                  </div>
                );
              })}
              <div className="px-6 py-3 bg-slate-50 flex justify-between items-center">
                <span className="text-sm text-slate-500 font-medium">Total</span>
                <span className="font-bold text-slate-800 text-lg">₹{fmt(totalObligation)}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* RESULTS */}
      {result && (
        <div className="space-y-5">
          {/* Alerts */}
          {(result.alerts || []).map((alert, i) => (
            <div key={i} className="bg-red-50 text-red-700 border border-red-200 p-4 rounded-xl flex items-start gap-3 text-sm">
              <AlertTriangle size={16} className="shrink-0 mt-0.5"/> {alert}
            </div>
          ))}

          {/* Summary */}
          <div className="bg-gradient-to-r from-slate-900 to-slate-800 text-white rounded-2xl p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-slate-200 text-base">ML Decision Summary</h3>
              <button onClick={() => { setResult(null); setPaidItems({}); }}
                className="text-slate-400 hover:text-white text-xs flex items-center gap-1 transition-colors">
                <RefreshCw size={12}/> Re-run
              </button>
            </div>
            <p className="text-slate-300 text-sm leading-relaxed">{result.summary}</p>
            <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-slate-700">
              <div>
                <p className="text-xs text-slate-400">Cash Balance</p>
                <p className="font-bold text-white text-lg">₹{fmt(remainingCash)}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Runway</p>
                <p className="font-bold text-white text-lg">{result.runway_days ?? '90+'} days</p>
              </div>
              <div>
                <p className="text-xs text-green-400">Recommended Pay</p>
                <p className="font-bold text-green-400 text-lg">{payItems.length} items</p>
              </div>
              <div>
                <p className="text-xs text-yellow-400">Recommended Delay</p>
                <p className="font-bold text-yellow-400 text-lg">{delayItems.length} items</p>
              </div>
            </div>
          </div>

          {/* PAY / DELAY columns */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* PAY */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 size={20} className="text-green-500"/>
                <h3 className="font-bold text-slate-800">Pay Now ({payItems.length})</h3>
                <span className="text-xs text-slate-400 ml-auto">Total: ₹{fmt(payItems.reduce((s, i) => s + i.amount, 0))}</span>
              </div>
              <div className="space-y-3">
                {payItems.length === 0 ? (
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-8 text-center text-slate-400 text-sm">
                    No payments recommended right now.
                  </div>
                ) : payItems.map((item, i) => (
                  <div key={i}
                    className={`bg-white border rounded-xl p-5 shadow-sm transition-all ${paidItems[item.description] ? 'border-green-300 bg-green-50' : 'border-green-200'}`}>
                    <div className="flex justify-between items-start">
                      <p className="font-semibold text-slate-800 text-sm">{item.description}</p>
                      <span className="font-bold text-slate-900 text-base ml-2 shrink-0">₹{fmt(item.amount)}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">Due in {item.days_to_due} day(s) · Confidence: {(item.confidence * 100).toFixed(0)}%</p>
                    <button onClick={() => setExpandedIdx(expandedIdx === `pay-${i}` ? null : `pay-${i}`)}
                      className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-1 mt-2 transition-colors">
                      {expandedIdx === `pay-${i}` ? <ChevronUp size={13}/> : <ChevronDown size={13}/>} Why this?
                    </button>
                    {expandedIdx === `pay-${i}` && (
                      <p className="text-xs text-slate-500 mt-2 pl-3 border-l-2 border-slate-200 leading-relaxed">{item.reasoning}</p>
                    )}
                    {item.action_suggestion && (
                      <p className="text-xs text-blue-600 mt-2">💡 {item.action_suggestion}</p>
                    )}
                    <div className="mt-3">
                      {paidItems[item.description] ? (
                        <div className="flex items-center gap-2 text-green-600 text-sm font-semibold">
                          <CheckCircle2 size={16}/> Paid — Balance updated
                        </div>
                      ) : (
                        <button onClick={() => setPayTarget(item)}
                          className="w-full bg-slate-900 hover:bg-slate-800 text-white font-semibold py-2.5 rounded-lg text-sm flex items-center justify-center gap-2 transition-colors">
                          <CreditCard size={15}/> Pay ₹{fmt(item.amount)}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* DELAY */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <XCircle size={20} className="text-amber-500"/>
                <h3 className="font-bold text-slate-800">Delay ({delayItems.length})</h3>
                <span className="text-xs text-slate-400 ml-auto">Total: ₹{fmt(delayItems.reduce((s, i) => s + i.amount, 0))}</span>
              </div>
              <div className="space-y-3">
                {delayItems.length === 0 ? (
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-8 text-center text-slate-400 text-sm">
                    All items can be paid. No delays needed.
                  </div>
                ) : delayItems.map((item, i) => (
                  <div key={i} className="bg-white border border-amber-200 rounded-xl p-5 shadow-sm">
                    <div className="flex justify-between items-start">
                      <p className="font-semibold text-slate-800 text-sm">{item.description}</p>
                      <span className="font-bold text-slate-900 text-base ml-2 shrink-0">₹{fmt(item.amount)}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">Due in {item.days_to_due} day(s) · Confidence: {(item.confidence * 100).toFixed(0)}%</p>
                    <button onClick={() => setExpandedIdx(expandedIdx === `delay-${i}` ? null : `delay-${i}`)}
                      className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-1 mt-2 transition-colors">
                      {expandedIdx === `delay-${i}` ? <ChevronUp size={13}/> : <ChevronDown size={13}/>} Why delay?
                    </button>
                    {expandedIdx === `delay-${i}` && (
                      <p className="text-xs text-slate-500 mt-2 pl-3 border-l-2 border-slate-200 leading-relaxed">{item.reasoning}</p>
                    )}
                    {item.action_suggestion && (
                      <div className="mt-2 bg-amber-50 border border-amber-100 rounded-lg p-2">
                        <p className="text-xs text-amber-700 font-medium">📋 {item.action_suggestion}</p>
                      </div>
                    )}
                    <button type="button" onClick={() => setMailModalItem(item)}
                      className="mt-3 w-full border border-amber-300 bg-white hover:bg-amber-50/80 text-amber-900 font-semibold py-2 rounded-lg text-sm flex items-center justify-center gap-2 transition-colors">
                      <Mail size={15} /> Send negotiation email
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Actions + Explanations */}
          {((result.actions || []).length > 0 || (result.explanations || []).length > 0) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {(result.actions || []).length > 0 && (
                <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
                  <h3 className="font-bold text-slate-800 mb-3 text-sm flex items-center gap-2"><Info size={16} className="text-blue-500"/> Action Items</h3>
                  <ol className="space-y-2">
                    {result.actions.map((act, i) => (
                      <li key={i} className="flex items-start gap-3 text-sm text-slate-600">
                        <span className="bg-blue-100 text-blue-700 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">{i+1}</span>
                        {act}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
              {(result.explanations || []).length > 0 && (
                <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
                  <h3 className="font-bold text-slate-800 mb-3 text-sm flex items-center gap-2"><FileText size={16} className="text-slate-400"/> ML Explanations</h3>
                  <ul className="space-y-2">
                    {result.explanations.map((exp, i) => (
                      <li key={i} className="text-sm text-slate-600 pl-3 border-l-2 border-slate-200">{exp}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Payment Gateway Modal */}
      {payTarget && (
        <PaymentGatewayModal
          item={payTarget}
          onSuccess={onPaySuccess}
          onClose={() => setPayTarget(null)}
        />
      )}

      {mailModalItem && (
        <NegotiationMailModal
          item={mailModalItem}
          mailConnected={mailStatus.connected}
          onConnectMail={startMailOAuth}
          onClose={() => setMailModalItem(null)}
          onSent={() => {
            setMailToast('Message sent via Microsoft Graph. It should arrive in the recipient inbox right away.');
          }}
        />
      )}
    </div>
  );
}
