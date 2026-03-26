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
    { id: 'FLOW', label: 'LIFECYCLE FLOW', icon: '⚡' },
  ]

  return (
    <div className="min-h-screen bg-[#020408] text-white selection:bg-red-500/30 font-sans overflow-x-hidden">
      {/* ── TOP NAV ── */}
      <nav className="h-20 border-b border-white/5 bg-black/60 backdrop-blur-2xl flex items-center justify-between px-10 sticky top-0 z-[100]">
        <div className="flex items-center gap-10">
          <div className="flex items-center gap-4 group cursor-default">
            <div className="w-11 h-11 rounded-2xl bg-red-600 flex items-center justify-center shadow-lg shadow-red-900/30 border border-red-500/20 group-hover:scale-105 transition-transform duration-500">
              <span className="text-xl">🛡️</span>
            </div>
            <div className="flex flex-col">
              <h1 className="text-xl font-black tracking-widest leading-none">ANKURAH</h1>
              <span className="text-[8px] text-zinc-600 font-bold uppercase tracking-[0.4em] mt-1.5">SafeSight Console v2.0</span>
            </div>
          </div>

          <div className="h-10 w-[1px] bg-white/5 mx-2" />

          <div className="flex gap-2 p-1.5 bg-zinc-900/30 rounded-2xl border border-white/5">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-6 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all duration-300 flex items-center gap-2.5 ${
                  activeTab === tab.id 
                    ? 'bg-red-600 text-white shadow-xl shadow-red-900/10' 
                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/5'
                }`}
              >
                <span className="text-sm opacity-80">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-10">
          <div className="text-right hidden md:block">
            <p className="text-xl font-black font-mono leading-none tracking-tighter text-white/90">
              {currentTime.toLocaleTimeString('en-IN', { hour12: false })}
            </p>
            <p className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest mt-1">
              {currentTime.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
            </p>
          </div>
          
          <div className={`px-5 py-2 rounded-2xl border text-[9px] font-black uppercase tracking-[0.2em] flex items-center gap-3 transition-colors duration-500 ${
            isConnected ? 'bg-emerald-500/5 border-emerald-500/10 text-emerald-400' : 'bg-red-500/5 border-red-500/10 text-red-400'
          }`}>
            <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse shadow-[0_0_8px_#10b981]' : 'bg-red-500 shadow-[0_0_8px_#ef4444]'}`} />
            {isConnected ? 'LIVE FEED ACTIVE' : 'SYSTEM LINK OFFLINE'}
          </div>
        </div>
      </nav>

      {/* ── THREAT BANNERS & NOTIFICATIONS ── */}
      <ThreatBanner latestAlert={latestAlert} />

      {/* ── MAIN CONTENT ── */}
      <main className="p-10 max-w-[1920px] mx-auto min-h-[calc(100vh-5rem)]">
        {activeTab === 'MONITOR' && (
          <div className="animate-in fade-in slide-in-from-top-4 duration-700 flex flex-col gap-10">
             <div className="flex items-end justify-between border-l-2 border-red-600/30 pl-6">
                <div>
                   <h2 className="text-3xl font-black italic tracking-tighter uppercase">Nodal Surveillance</h2>
                   <p className="text-xs text-zinc-600 font-bold uppercase tracking-[0.3em] mt-1">Intelligent Detection Grid • Multi-Channel Feed</p>
                </div>
                <div className="flex gap-3">
                   <div className="px-4 py-2 rounded-xl bg-zinc-900/50 border border-white/5 text-[9px] font-black tracking-widest text-zinc-400">ENGINE: NEURAL-V4</div>
                   <div className="px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-[9px] font-black tracking-widest">GRID_OPTIMAL</div>
                </div>
             </div>
             
             <div className="bg-zinc-900/10 rounded-[2.5rem] border border-white/5 p-2 shadow-inner">
                <CameraGrid latestAlert={latestAlert} />
             </div>
          </div>
        )}

        {activeTab === 'MAP' && (
          <div className="animate-in fade-in slide-in-from-bottom-8 duration-700 space-y-10">
             <div className="grid grid-cols-1 lg:grid-cols-4 gap-10">
                <div className="lg:col-span-3 space-y-6">
                   <div className="flex items-center justify-between pl-2">
                      <div className="flex items-center gap-4">
                        <div className="w-8 h-8 rounded-lg bg-zinc-900 flex items-center justify-center text-sm border border-white/10">🗺️</div>
                        <h2 className="text-2xl font-black italic tracking-tight uppercase">Incident Geography</h2>
                      </div>
                      <span className="text-[10px] font-mono text-zinc-600 font-bold tracking-[0.4em]">GS-COORD: {latestAlert?.lat || '0'}, {latestAlert?.lng || '0'}</span>
                   </div>
                   <div className="relative aspect-[21/9] rounded-[3rem] overflow-hidden border border-white/5 shadow-2xl bg-zinc-900/40 group">
                      <AlertMap latestAlert={latestAlert} />
                      <div className="absolute inset-0 border-[20px] border-black/20 pointer-events-none rounded-[3rem]" />
                   </div>
                </div>
                <div className="lg:col-span-1 flex flex-col pt-12">
                   <div className="bg-zinc-900/20 border border-white/5 rounded-[2rem] flex-grow flex flex-col overflow-hidden">
                      <div className="px-8 py-6 border-b border-white/5 flex items-center justify-between">
                        <h2 className="text-xs font-black italic tracking-[0.2em] uppercase text-zinc-500">Recent Logs</h2>
                        <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse" />
                      </div>
                      <AlertLog alerts={alerts} />
                   </div>
                </div>
             </div>
          </div>
        )}

        {activeTab === 'FLOW' && (
          <div className="animate-in zoom-in-95 duration-700 h-[65vh] flex flex-col items-center justify-center space-y-16">
             <div className="text-center space-y-6 max-w-2xl px-8">
               <h2 className="text-5xl font-black tracking-tighter italic uppercase text-white/90">Lifecycle Engine</h2>
               <p className="text-zinc-600 text-[13px] font-medium leading-relaxed tracking-wide bg-zinc-950/40 p-6 rounded-2xl border border-white/5 shadow-xl">
                 Visualization of the neural-distress lifecycle. Follow the active nodes as they move from detection to site resolution in real-time.
               </p>
             </div>

             <div className="flex items-center gap-16 relative w-full max-w-5xl justify-center overflow-x-auto pb-12 pt-8">
                <FlowStep label="IDLE" icon="🛡️" active={!latestAlert} done={latestAlert} />
                <Connector active={latestAlert} />
                <FlowStep label="ALERT" icon="🚨" active={latestAlert && !latestAlert.responder_status} done={!!latestAlert?.responder_status} pulse />
                <Connector active={!!latestAlert?.responder_status} />
                <FlowStep label="EN-ROUTE" icon="🏃" active={latestAlert?.responder_status === 'started'} done={latestAlert?.responder_status === 'reached'} />
                <Connector active={latestAlert?.responder_status === 'reached'} />
                <FlowStep label="RESOLVED" icon="📍" active={latestAlert?.responder_status === 'reached'} />
             </div>

             <button 
               onClick={() => {
                 fetch(`${BACKEND_URL}/demo_replay`)
               }}
               className="group relative px-14 py-6 rounded-2xl bg-white text-black font-black text-xl hover:bg-red-600 hover:text-white transition-all duration-500 active:scale-95 shadow-2xl shadow-white/5 flex items-center gap-4"
             >
               <span>REPLAY SIMULATION</span>
               <div className="w-8 h-8 rounded-lg bg-black/10 flex items-center justify-center group-hover:bg-white/20">
                  <span className="text-sm">▶️</span>
               </div>
             </button>
          </div>
        )}
      </main>

      {/* ── SSE DIAGNOSTIC OVERLAY ── */}
      <div className="fixed bottom-6 left-6 z-[200] group pointer-events-auto">
        <div className="bg-zinc-950/80 backdrop-blur-xl p-5 pr-10 rounded-2xl border border-white/10 text-[9px] font-mono shadow-2xl transition-all duration-500 translate-y-20 group-hover:translate-y-0 opacity-0 group-hover:opacity-100">
          <p className="text-zinc-600 mb-3 uppercase tracking-widest font-black flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            System Diagnostics
          </p>
          <div className="space-y-2">
            <p className="flex justify-between gap-8">Status: <span className={isConnected ? "text-emerald-500 font-bold" : "text-red-500 font-bold"}>{isConnected ? "LIVE_LINK" : "DISCONNECT"}</span></p>
            <p className="flex justify-between gap-8">Node Ref: <span className="text-zinc-300">{latestAlert?.camera_id || 'IDLE'}</span></p>
            <p className="flex justify-between gap-8">Encryption: <span className="text-emerald-500/80">AES_256_ACTIVE</span></p>
            <p className="flex justify-between gap-8">Snap: <span className={latestAlert?.snapshot_url ? "text-emerald-500" : "text-zinc-700"}>{latestAlert?.snapshot_url ? "READY" : "WAIT"}</span></p>
          </div>
        </div>
        <div className="w-10 h-10 rounded-full bg-zinc-900 border border-white/10 flex items-center justify-center text-xs opacity-50 group-hover:opacity-100 transition-opacity">⚡</div>
      </div>
    </div>
  )
}

function FlowStep({ label, icon, active, done, pulse }) {
  return (
    <div className={`flex flex-col items-center gap-5 transition-all duration-1000 ${active ? 'scale-125' : 'scale-100 opacity-30 blur-[0.5px]'}`}>
       <div className={`w-24 h-24 rounded-[2rem] flex items-center justify-center text-4xl transition-all duration-700 border-2 ${
         done ? 'bg-emerald-500/10 border-emerald-500/40 shadow-[0_0_40px_rgba(16,185,129,0.15)]' :
         active ? 'bg-red-500/10 border-red-500/40 shadow-[0_0_60px_rgba(220,38,38,0.25)]' : 'bg-transparent border-white/5'
       } ${pulse ? 'animate-pulse' : ''}`}>
         {icon}
       </div>
       <span className={`text-[10px] font-black tracking-[0.4em] uppercase transition-colors duration-500 ${active ? 'text-white' : 'text-zinc-700'}`}>{label}</span>
    </div>
  )
}

function Connector({ active }) {
  return (
    <div className="w-24 h-[1px] bg-zinc-900 relative">
       <div className={`absolute inset-0 bg-gradient-to-r from-red-600/50 to-red-400/50 transition-all duration-[2000ms] origin-left ${active ? 'scale-x-100' : 'scale-x-0'}`} />
    </div>
  )
}
