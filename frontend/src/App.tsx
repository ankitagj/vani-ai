import { ElevenLabsInput } from './components/ElevenLabsInput';
import SetupPage from './components/SetupPage';
import BusinessDirectory from './components/BusinessDirectory';
import AdminPage from './components/AdminPage';
import DashboardView from './components/DashboardView';
import { API_URL } from './config';
import { useState, useEffect } from 'react';

interface BusinessConfig {
  agent_name: string;
  business_name: string;
  greeting_message: string;
  onboarding_status: string;
}

type View = 'directory' | 'chat' | 'setup' | 'admin' | 'dashboard';

function App() {
  const [view, setView] = useState<View>('directory');
  const [businessId, setBusinessId] = useState<string | null>(null);
  const [config, setConfig] = useState<BusinessConfig | null>(null);
  const [loadingConfig, setLoadingConfig] = useState(false);
  const [showKB, setShowKB] = useState(false);
  const [kbContent, setKbContent] = useState<any>(null);

  // Load config when entering chat or dashboard mode
  useEffect(() => {
    if ((view === 'chat' || view === 'dashboard') && businessId) {
      setLoadingConfig(true);
      fetch(`${API_URL}/config/${businessId}`)
        .then(res => res.json())
        .then(data => {
          setConfig(data);
          if (data.onboarding_status !== 'complete') {
            setView('setup');
          }
        })
        .catch(err => console.error(err))
        .finally(() => setLoadingConfig(false));
    }
  }, [view, businessId]);

  const handleTranscriptComplete = async (transcript: string, messages: any[] = []) => {
    try {
      const response = await fetch(`${API_URL}/ask-mom`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript,
          messages,
          business_id: businessId
        }),
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Error sending transcript to backend:', error);
      throw error;
    }
  };

  const handleSetupComplete = () => {
    alert("Business Setup Complete! You can now select it from the directory.");
    setView('directory');
    setBusinessId(null);
  };

  const fetchKB = async () => {
    try {
      const res = await fetch(`${API_URL}/knowledge-base/${businessId}`);
      const data = await res.json();
      setKbContent(data);
      setShowKB(true);
    } catch (e) {
      console.error("Failed to load KB", e);
      alert("Could not load Knowledge Base.");
    }
  };

  // RENDER LOGIC
  if (view === 'directory') {
    return <BusinessDirectory
      onSelect={(id) => { setBusinessId(id); setView('chat'); }}
      onRegister={() => { setBusinessId(null); setView('setup'); }}
      onAdmin={() => setView('admin')}
    />;
  }

  if (view === 'setup') {
    return <SetupPage onComplete={handleSetupComplete} onBack={() => setView('directory')} />
  }

  if (view === 'admin') {
    return <AdminPage onBack={() => setView('directory')} />
  }

  if (view === 'dashboard' && businessId && config) {
    return <DashboardView
      businessId={businessId}
      businessName={config.business_name}
      onBack={() => setView('chat')}
    />
  }

  // Chat View
  if (loadingConfig || !config) return <div style={{ color: '#fff', padding: 20 }}>Loading Config...</div>;

  return (
    <div className="App">
      <header className="App-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px', backgroundColor: 'rgba(30,30,30,0.5)', borderBottom: '1px solid var(--border-color)' }}>
        <button onClick={() => setView('directory')} className="btn-primary" style={{ background: 'transparent', border: '1px solid var(--border-color)', padding: '5px 15px' }}>
          ← Back
        </button>
        <h1 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--text-primary)' }}>{config.business_name}</h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => setView('dashboard')}
            className="btn-primary"
            style={{ padding: '5px 15px', fontSize: '0.8rem', backgroundColor: '#333' }}
          >
            📊 Dashboard
          </button>
          <button onClick={fetchKB} className="btn-primary" style={{ padding: '5px 15px', fontSize: '0.8rem', backgroundColor: '#333' }}>
            📖 View KB
          </button>
        </div>
      </header>
      <main>
        <ElevenLabsInput
          onTranscriptComplete={handleTranscriptComplete}
          agentName={config.agent_name}
          businessId={businessId || 'rainbow_default'}
        />
      </main>

      {showKB && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.8)', zIndex: 1000,
          display: 'flex', justifyContent: 'center', alignItems: 'center'
        }}>
          <div className="card" style={{ width: '80%', height: '80%', overflow: 'hidden', backgroundColor: '#1e1e1e', position: 'relative', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '20px', borderBottom: '1px solid #333', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ margin: 0 }}>📚 Knowledge Base Source</h2>
              <button
                onClick={() => setShowKB(false)}
                style={{ background: 'transparent', border: 'none', color: 'white', fontSize: '1.5rem', cursor: 'pointer' }}
              >
                ×
              </button>
            </div>
            <div style={{ padding: '20px', overflow: 'auto', flex: 1 }}>
              <pre style={{ textAlign: 'left', background: '#111', padding: '20px', borderRadius: '8px', overflow: 'auto' }}>
                {JSON.stringify(kbContent, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
