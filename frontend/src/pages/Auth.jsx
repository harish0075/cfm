import { useState, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import api from '../services/api';
import { Lock, Phone, User, Plus, Trash2, Home, Car, Coins, ChevronRight, ChevronLeft } from 'lucide-react';

const ASSET_TYPES = [
  { value: 'house', label: 'House / Property', icon: <Home size={16}/> },
  { value: 'vehicle', label: 'Vehicle', icon: <Car size={16}/> },
  { value: 'gold', label: 'Gold / Jewellery', icon: <Coins size={16}/> },
  { value: 'other', label: 'Other Asset', icon: null },
];
const LIQUIDITY = ['low', 'medium', 'high'];

const defaultAsset = () => ({ asset_type: 'house', name: '', estimated_value: '', liquidity: 'medium' });

export default function Auth() {
  const { login } = useContext(AuthContext);
  const [isLogin, setIsLogin] = useState(true);
  const [step, setStep] = useState(1); // 1 = basic info, 2 = assets
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Login fields
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');

  // Register fields
  const [name, setName] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [cashBalance, setCashBalance] = useState('');
  const [assets, setAssets] = useState([]);

  const addAsset = () => setAssets(prev => [...prev, defaultAsset()]);
  const removeAsset = (i) => setAssets(prev => prev.filter((_, idx) => idx !== i));
  const updateAsset = (i, field, val) => setAssets(prev => prev.map((a, idx) => idx === i ? { ...a, [field]: val } : a));

  const goStep2 = (e) => {
    e.preventDefault();
    if (!name || !regPhone || !regPassword || !cashBalance) { setError('All fields are required.'); return; }
    setError('');
    setStep(2);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const res = await api.post('/login', { phone, password });
      login(res.data.access_token, res.data.user_id);
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid credentials');
    } finally { setLoading(false); }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    const validAssets = assets
      .filter(a => a.estimated_value && parseFloat(a.estimated_value) > 0)
      .map(a => ({ ...a, estimated_value: parseFloat(a.estimated_value) }));
    try {
      await api.post('/onboard', {
        name, phone: regPhone, password: regPassword,
        cash_balance: parseFloat(cashBalance),
        assets: validAssets,
      });
      const loginRes = await api.post('/login', { phone: regPhone, password: regPassword });
      login(loginRes.data.access_token, loginRes.data.user_id);
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed');
      setStep(1);
    } finally { setLoading(false); }
  };

  const switchMode = (toLogin) => { setIsLogin(toLogin); setError(''); setStep(1); };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 p-4">
      <div className="max-w-md w-full bg-white rounded-3xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-800 p-8 text-center">
          <h1 className="text-3xl font-black text-white tracking-tight">CFM</h1>
          <p className="text-blue-200 text-sm mt-1 font-medium">Corporate Finance Manager</p>
        </div>

        <div className="p-8">
          {/* Tabs */}
          <div className="flex bg-slate-100 p-1 rounded-xl mb-6">
            <button
              onClick={() => switchMode(true)}
              className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${isLogin ? 'bg-white shadow text-blue-600' : 'text-slate-500'}`}
            >Sign In</button>
            <button
              onClick={() => switchMode(false)}
              className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${!isLogin ? 'bg-white shadow text-blue-600' : 'text-slate-500'}`}
            >Register</button>
          </div>

          {error && <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-xl border border-red-100">{error}</div>}

          {/* LOGIN */}
          {isLogin && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider">Phone Number</label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16}/>
                  <input type="tel" required value={phone} onChange={e => setPhone(e.target.value)}
                    className="w-full pl-9 pr-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                    placeholder="9999900000"/>
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16}/>
                  <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
                    className="w-full pl-9 pr-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                    placeholder="••••••••"/>
                </div>
              </div>
              <button type="submit" disabled={loading}
                className="w-full mt-2 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl transition-all disabled:opacity-50 flex justify-center items-center">
                {loading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"/> : 'Sign In'}
              </button>
            </form>
          )}

          {/* REGISTER — Step 1: Basic Info */}
          {!isLogin && step === 1 && (
            <form onSubmit={goStep2} className="space-y-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Step 1 of 2 — Basic Info</p>
                <div className="flex gap-1"><div className="w-8 h-1 rounded bg-blue-600"/><div className="w-8 h-1 rounded bg-slate-200"/></div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider">Full Name</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16}/>
                  <input type="text" required value={name} onChange={e => setName(e.target.value)}
                    className="w-full pl-9 pr-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none text-sm" placeholder="John Doe"/>
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider">Initial Cash Balance (₹)</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-bold text-sm">₹</span>
                  <input type="number" required min="0" value={cashBalance} onChange={e => setCashBalance(e.target.value)}
                    className="w-full pl-8 pr-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none text-sm" placeholder="50000"/>
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider">Phone Number</label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16}/>
                  <input type="tel" required value={regPhone} onChange={e => setRegPhone(e.target.value)}
                    className="w-full pl-9 pr-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none text-sm" placeholder="9999900000"/>
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16}/>
                  <input type="password" required minLength={6} value={regPassword} onChange={e => setRegPassword(e.target.value)}
                    className="w-full pl-9 pr-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none text-sm" placeholder="Min 6 characters"/>
                </div>
              </div>
              <button type="submit"
                className="w-full mt-2 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl transition-all flex items-center justify-center gap-2">
                Next — Declare Assets <ChevronRight size={18}/>
              </button>
            </form>
          )}

          {/* REGISTER — Step 2: Assets */}
          {!isLogin && step === 2 && (
            <form onSubmit={handleRegister} className="space-y-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Step 2 of 2 — Your Assets</p>
                <div className="flex gap-1"><div className="w-8 h-1 rounded bg-blue-200"/><div className="w-8 h-1 rounded bg-blue-600"/></div>
              </div>
              <p className="text-xs text-slate-500">Declare your assets (property, gold, vehicles). These act as last-resort liquidity. Skip if none.</p>

              <div className="space-y-3 max-h-52 overflow-y-auto pr-1">
                {assets.map((asset, i) => (
                  <div key={i} className="border border-slate-200 rounded-xl p-4 space-y-2 bg-slate-50">
                    <div className="flex items-center justify-between">
                      <select value={asset.asset_type} onChange={e => updateAsset(i, 'asset_type', e.target.value)}
                        className="text-sm font-medium text-slate-700 border-0 bg-transparent outline-none cursor-pointer">
                        {ASSET_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                      </select>
                      <button type="button" onClick={() => removeAsset(i)} className="text-red-400 hover:text-red-600"><Trash2 size={14}/></button>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <input value={asset.name} onChange={e => updateAsset(i, 'name', e.target.value)}
                        className="border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-400 bg-white" placeholder="Label (e.g. Honda City)"/>
                      <div className="relative">
                        <span className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 text-xs font-bold">₹</span>
                        <input type="number" min="1" value={asset.estimated_value} onChange={e => updateAsset(i, 'estimated_value', e.target.value)}
                          className="w-full pl-6 border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-400 bg-white" placeholder="Value"/>
                      </div>
                    </div>
                    <select value={asset.liquidity} onChange={e => updateAsset(i, 'liquidity', e.target.value)}
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none bg-white">
                      {LIQUIDITY.map(l => <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)} Liquidity</option>)}
                    </select>
                  </div>
                ))}
              </div>

              <button type="button" onClick={addAsset}
                className="w-full border-2 border-dashed border-slate-300 text-slate-500 hover:border-blue-400 hover:text-blue-600 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center justify-center gap-2">
                <Plus size={16}/> Add Asset
              </button>

              <div className="flex gap-3 mt-2">
                <button type="button" onClick={() => setStep(1)}
                  className="flex-1 border border-slate-200 text-slate-600 font-semibold py-3 rounded-xl hover:bg-slate-50 transition-all flex items-center justify-center gap-2">
                  <ChevronLeft size={18}/> Back
                </button>
                <button type="submit" disabled={loading}
                  className="flex-2 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-xl transition-all disabled:opacity-50 flex items-center justify-center">
                  {loading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"/> : 'Create Account'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
