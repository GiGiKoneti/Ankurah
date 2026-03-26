import { useEffect, useState } from 'react'
import { useSSE } from '../hooks/useSSE'
import ThreatBanner from './ThreatBanner'
import AlertMap from './AlertMap'
import CameraGrid from './CameraGrid'
import AlertLog from './AlertLog'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL

export default function Dashboard() {
  const { latestAlert, alerts, setAlerts, isConnected } = useSSE()
  const [activeTab, setActiveTab] = useState('MONITOR') // MONITOR, MAP, FLOW
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    fetch(`${BACKEND_URL}/alerts`)
      .then(r => r.json())
      .then(data => {
        if (data.alerts) setAlerts(data.alerts)
      })
      .catch(err => console.warn('[Dashboard] Could not fetch /alerts:', err))
  }, [])

  useEffect(() => {
    const t = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const tabs = [
    { id: 'MONITOR', label: 'SURVEILLANCE GRID', icon: '📹' },
    { id: 'MAP', label: 'INCIDENT GEOGRAPHY', icon: '🗺️' },
    { id: 'FLOW', label: 'LIFECYCLE SIMULATION', icon: '⚡' },
  ]

  return (
    <div className="min-h-screen bg-black text-white selection:bg-red-500/30 font-sans">
      {/* ── TOP NAV ── */}
      <nav className="h-20 border-b border-white/5 bg-black/50 backdrop-blur-xl flex items-center justify-between px-8 sticky top-0 z-[100]">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-600 flex items-center justify-center shadow-lg shadow-red-900/20">
              <span className="text-xl">🛡️</span>
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tighter leading-none">ANKURAH</h1>
            </div>
          </div>

          <div className="h-8 w-[1px] bg-white/10 mx-2" />

          <div className="flex gap-1 bg-zinc-900/50 p-1 rounded-xl border border-white/5">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-lg text-[10px] font-black uppercase tracking-wider transition-all flex items-center gap-2 ${
                  activeTab === tab.id 
                    ? 'bg-red-600 text-white shadow-lg' 
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                <span>{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="text-right hidden sm:block">
            <p className="text-lg font-black font-mono leading-none tracking-tighter">
              {currentTime.toLocaleTimeString('en-IN', { hour12: false })}
            </p>
            <p className="text-[10px] font-bold text-zinc-500 uppercase">{currentTime.toLocaleDateString()}</p>
          </div>
          <div className={`px-4 py-1.5 rounded-full border text-[10px] font-black uppercase tracking-widest flex items-center gap-2 ${
            isConnected ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-red-500/10 border-red-500/20 text-red-400'
          }`}>
            <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            {isConnected ? 'LIVE FEED ACCESS' : 'NODE DISCONNECTED'}
          </div>
        </div>
      </nav>

      {/* ── THREAT BANNER ── */}
      <ThreatBanner latestAlert={latestAlert} />

      {/* ── MAIN CONTENT ── */}
      <main className="p-8">
        {activeTab === 'MONITOR' && (
          <div className="animate-in fade-in duration-500 flex flex-col gap-8">
             <div className="flex items-center justify-between">
                <div>
                   <h2 className="text-2xl font-black italic tracking-tight">CAMERA NETWORK</h2>
                   <p className="text-xs text-zinc-500 font-medium uppercase tracking-widest">9 Active Channels • High-Density Grid</p>
                </div>
                <div className="flex gap-2">
                   <div className="px-3 py-1 rounded bg-zinc-900 border border-white/5 text-[10px] font-bold">MODE: AI_ENHANCED</div>
                   <div className="px-3 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-[10px] font-bold">ALL_ONLINE</div>
                </div>
             </div>
             <CameraGrid latestAlert={latestAlert} />
          </div>
        )}

        {activeTab === 'MAP' && (
          <div className="animate-in slide-in-from-bottom-4 duration-500 space-y-8">
             <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                <div className="lg:col-span-3 space-y-4">
                   <div className="flex items-center justify-between mb-2">
                      <h2 className="text-xl font-bold italic tracking-tight">INCIDENT GEOGRAPHY</h2>
                      <span className="text-[10px] font-mono text-zinc-500 tracking-[0.3em]">GS-COORD: {latestAlert?.lat || '0'}, {latestAlert?.lng || '0'}</span>
                   </div>
                   <div className="relative aspect-video rounded-3xl overflow-hidden border border-white/5 shadow-2xl">
                      <AlertMap latestAlert={latestAlert} />
                   </div>
                </div>
                <div className="lg:col-span-1 space-y-6">
                   <h2 className="text-xl font-bold italic tracking-tight uppercase">Recent Logs</h2>
                   <AlertLog alerts={alerts} />
                </div>
             </div>
          </div>
        )}

        {activeTab === 'FLOW' && (
          <div className="animate-in zoom-in-95 duration-700 h-[60vh] flex flex-col items-center justify-center space-y-12">
             <div className="text-center space-y-4">
               <h2 className="text-4xl font-black tracking-tighter italic">LIFECYCLE FLOW</h2>
               <p className="text-zinc-500 text-sm max-w-lg mx-auto bg-zinc-900/50 p-4 rounded-xl border border-white/5">
                 Real-time visualization of the distress-to-resolution timeline. Follow the nodes as they activate across the ecosystem.
               </p>
             </div>

             {/* n8n Style Flow Simulation (Mock Visualization) */}
             <div className="flex items-center gap-12 relative w-full max-w-5xl justify-center overflow-x-auto pb-8">
                <FlowStep label="IDLE" icon="🛡️" active={!latestAlert} done={latestAlert} />
                <Connector active={latestAlert} />
                <FlowStep label="ALERT" icon="🚨" active={latestAlert && !latestAlert.responder_status} done={!!latestAlert?.responder_status} pulse />
                <Connector active={!!latestAlert?.responder_status} />
                <FlowStep label="STARTED" icon="🏃" active={latestAlert?.responder_status === 'started'} done={latestAlert?.responder_status === 'reached'} />
                <Connector active={latestAlert?.responder_status === 'reached'} />
                <FlowStep label="REACHED" icon="📍" active={latestAlert?.responder_status === 'reached'} />
             </div>

             <button 
               onClick={() => {
                 // Trigger a demo simulation via a special backend endpoint
                 fetch(`${BACKEND_URL}/demo_replay`)
               }}
               className="px-12 py-5 rounded-2xl bg-white text-black font-black text-lg hover:bg-zinc-200 transition-all active:scale-95 shadow-2xl shadow-white/5"
             >
               EXECUTE SIMULATION REPLAY
             </button>
          </div>
        )}
      </main>

      {/* ── Sub-components for Flow ── */}
      {/* ── DEBUG PANEL ── */}
      <div className="fixed bottom-4 right-4 z-[200] max-w-xs bg-black/80 backdrop-blur-md p-4 rounded-xl border border-white/10 text-[9px] font-mono select-none pointer-events-none">
        <p className="text-zinc-500 mb-2 uppercase tracking-widest font-bold">SSE Debug Diagnostics</p>
        <div className="space-y-1">
          <p>Status: <span className={isConnected ? "text-emerald-500" : "text-red-500"}>{isConnected ? "CONNECTED" : "DISCONNECTED"}</span></p>
          <p>Latest ID: <span className="text-zinc-300">{latestAlert?.camera_id || 'NONE'}</span></p>
          <p>Has Image: <span className={latestAlert?.snapshot_url ? "text-emerald-500" : "text-zinc-600"}>{latestAlert?.snapshot_url ? "YES" : "NO"}</span></p>
          {latestAlert?.snapshot_url && (
            <p className="text-[7px] truncate text-zinc-500">{latestAlert.snapshot_url}</p>
          )}
        </div>
      </div>
    </div>
  )
}

function FlowStep({ label, icon, active, done, pulse }) {
  return (
    <div className={`flex flex-col items-center gap-4 transition-all duration-700 ${active ? 'scale-125' : 'scale-100 opacity-50'}`}>
       <div className={`w-20 h-20 rounded-3xl flex items-center justify-center text-3xl transition-all duration-500 border-2 ${
         done ? 'bg-emerald-500/20 border-emerald-500/50 shadow-[0_0_30px_rgba(16,185,129,0.2)]' :
         active ? 'bg-red-500/20 border-red-500/50 shadow-[0_0_40px_rgba(220,38,38,0.3)]' : 'bg-zinc-900 border-white/5'
       } ${pulse ? 'animate-pulse' : ''}`}>
         {icon}
       </div>
       <span className={`text-[10px] font-black tracking-[0.3em] uppercase transition-colors ${active ? 'text-white' : 'text-zinc-600'}`}>{label}</span>
    </div>
  )
}

function Connector({ active }) {
  return (
    <div className="w-20 h-[2px] bg-zinc-900 relative">
       <div className={`absolute inset-0 bg-gradient-to-r from-red-600 to-red-400 transition-all duration-1000 origin-left ${active ? 'scale-x-100' : 'scale-x-0'}`} />
    </div>
  )
}
