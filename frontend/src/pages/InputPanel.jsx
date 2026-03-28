import { useState, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import api from '../services/api';
import { FileText, MessageSquare, Image, Mic, CheckCircle } from 'lucide-react';

function fmt(n) {
  return Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

export default function InputPanel() {
  const { userId } = useContext(AuthContext);
  const [activeTab, setActiveTab] = useState('text');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  // Text input state
  const [textMsg, setTextMsg] = useState('');

  // File input state
  const [selectedFile, setSelectedFile] = useState(null);
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [audioChunks, setAudioChunks] = useState([]);

  const tabs = [
    { id: 'text', icon: <MessageSquare size={16} />, label: 'Natural Language' },
    { id: 'receipt', icon: <Image size={16} />, label: 'Receipt Image' },
    { id: 'bank', icon: <FileText size={16} />, label: 'Bank Statement' },
    { id: 'audio', icon: <Mic size={16} />, label: 'Voice Input' },
  ];

  const handleText = async (e) => {
    e.preventDefault();
    if (!textMsg.trim()) return;
    setLoading(true); setError(''); setResult(null);
    try {
      const res = await api.post('/input', { user_id: userId, message: textMsg });
      setResult({
        type: res.data.entry.type,
        amount: res.data.entry.amount,
        description: res.data.entry.description,
        date: res.data.entry.date,
        cashBalance: res.data.cash_balance,
      });
      setTextMsg('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to process input');
    } finally {
      setLoading(false);
    }
  };

  const handleFile = async (endpoint) => {
    if (!selectedFile) { setError('Please select a file first.'); return; }
    setLoading(true); setError(''); setResult(null);
    const form = new FormData();
    form.append('file', selectedFile);
    form.append('user_id', userId);
    try {
      const res = await api.post(endpoint, form, { headers: { 'Content-Type': 'multipart/form-data' } });
      const entries = res.data.entries || [res.data.entry];
      setResult({
        multiple: true,
        entries,
        cashBalance: res.data.cash_balance,
      });
      setSelectedFile(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to process file');
    } finally {
      setLoading(false);
    }
  };

  const handleAudioUpload = async (blob) => {
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const form = new FormData();
      form.append('file', blob, 'voice_input.webm');
      form.append('user_id', userId);

      const res = await api.post('/audio', form, { headers: { 'Content-Type': 'multipart/form-data' } });
      const entry = res.data.entry;
      setResult({
        type: entry.type,
        amount: entry.amount,
        description: entry.description,
        date: entry.date,
        cashBalance: res.data.cash_balance,
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Audio transcription failed');
    } finally {
      setLoading(false);
    }
  };

  const handleStartRecording = async () => {
    if (recording) {
      // Stop and upload
      mediaRecorder.stop();
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      setMediaRecorder(recorder);
      setAudioChunks([]);
      const chunks = [];

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunks.push(event.data);
          setAudioChunks((prev) => prev.concat(event.data));
        }
      };

      recorder.onstop = async () => {
        setRecording(false);
        const blob = new Blob(chunks, { type: 'audio/webm' });
        await handleAudioUpload(blob);
      };

      recorder.start();
      setRecording(true);
    } catch (err) {
      setError('Microphone access denied or unavailable');
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Financial Inputs</h1>
        <p className="text-slate-500 mt-1">Record financial events via any input method. Each entry is normalized and added to your financial state.</p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Tab bar */}
        <div className="flex border-b border-slate-200 bg-slate-50">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); setResult(null); setError(''); }}
              className={`flex-1 flex items-center justify-center gap-2 py-4 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-white text-blue-600 border-b-2 border-blue-600'
                  : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        <div className="p-8">
          {/* Error */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">{error}</div>
          )}

          {/* Success Result */}
          {result && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-xl">
              <div className="flex items-center gap-2 text-green-700 font-semibold mb-2">
                <CheckCircle size={18} /> Entry recorded successfully!
              </div>
              {result.multiple ? (
                <div>
                  <p className="text-sm text-green-700">{result.entries.length} entries imported. New balance: <strong>₹{fmt(result.cashBalance)}</strong></p>
                </div>
              ) : (
                <div className="text-sm text-green-700 space-y-1">
                  <p><span className="capitalize font-medium">{result.type}</span> of <strong>₹{fmt(result.amount)}</strong> on {new Date(result.date).toLocaleDateString('en-IN')}</p>
                  <p className="text-green-600">{result.description}</p>
                  <p className="font-medium">Updated cash balance: ₹{fmt(result.cashBalance)}</p>
                </div>
              )}
            </div>
          )}

          {/* TEXT Input */}
          {activeTab === 'text' && (
            <form onSubmit={handleText} className="space-y-4">
              <label className="block text-sm font-semibold text-slate-700">Describe your financial event in plain language</label>
              <textarea
                value={textMsg}
                onChange={e => setTextMsg(e.target.value)}
                className="w-full h-36 p-4 border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 resize-none text-sm"
                placeholder={`Examples:\n• "I paid ₹20,000 rent today"\n• "Received ₹50,000 from client ABC next Friday"\n• "Electricity bill of ₹3,500 due on April 15"`}
              />
              <p className="text-xs text-slate-400">The system will parse dates, amounts, and classify as inflow or outflow automatically.</p>
              <button
                type="submit"
                disabled={loading || !textMsg.trim()}
                className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-2.5 px-6 rounded-lg text-sm transition-colors flex items-center gap-2"
              >
                {loading ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : null}
                Process Input
              </button>
            </form>
          )}

          {/* Receipt / Bank upload */}
          {(activeTab === 'receipt' || activeTab === 'bank') && (
            <div className="space-y-6">
              <label
                className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-2xl p-12 cursor-pointer hover:bg-slate-50 transition-colors"
                htmlFor="file-upload"
              >
                <div className={`w-14 h-14 rounded-full flex items-center justify-center mb-4 ${activeTab === 'receipt' ? 'bg-blue-100 text-blue-600' : 'bg-purple-100 text-purple-600'}`}>
                  {activeTab === 'receipt' ? <Image size={24} /> : <FileText size={24} />}
                </div>
                <p className="font-semibold text-slate-700">
                  {selectedFile ? selectedFile.name : 'Click to upload or drag & drop'}
                </p>
                <p className="text-sm text-slate-400 mt-1">
                  {activeTab === 'receipt' ? 'PNG, JPG (max 10MB)' : 'PDF (max 20MB)'}
                </p>
                <input
                  id="file-upload"
                  type="file"
                  className="hidden"
                  accept={activeTab === 'receipt' ? 'image/*' : '.pdf'}
                  onChange={e => setSelectedFile(e.target.files[0])}
                />
              </label>
              <button
                onClick={() => handleFile(activeTab === 'receipt' ? '/upload-receipt' : '/upload-bank-statement')}
                disabled={loading || !selectedFile}
                className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-2.5 px-6 rounded-lg text-sm transition-colors flex items-center gap-2"
              >
                {loading ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : null}
                Upload & Process
              </button>
            </div>
          )}

          {/* Audio */}
          {activeTab === 'audio' && (
            <div className="text-center py-12 space-y-4">
              <div className="w-24 h-24 rounded-full bg-red-50 text-red-400 flex items-center justify-center mx-auto ring-8 ring-red-50/50 transition-all">
                <Mic size={32} />
              </div>
              <p className="font-medium text-slate-700">Voice input mode</p>
              <p className="text-slate-400 text-sm max-w-sm mx-auto">Talk naturally, e.g. “Paid ₹12,500 office supplies” or “Received ₹50,000 salary”.</p>

              <button
                onClick={handleStartRecording}
                disabled={loading}
                className={`text-white font-medium py-2 px-6 rounded-lg text-sm transition ${recording ? 'bg-rose-600 hover:bg-rose-700' : 'bg-blue-600 hover:bg-blue-700'}`}
              >
                {recording ? 'Stop & Upload' : 'Start Recording'}
              </button>

              {recording ? <p className="text-rose-500 text-sm">Recording... speak now (microphone active)</p> : <p className="text-slate-400 text-xs">Tap to begin voice capture; tap again to stop and upload.</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
