import { useState, useEffect } from 'react'
import { useSSE } from './hooks/useSSE'
import './index.css'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL

export default function App() {
  const { latestAlert, isConnected } = useSSE()
  const [status, setStatus] = useState('IDLE') // IDLE, STARTED, REACHED
  const [notified, setNotified] = useState(false)

  // Vibrate or play sound on new alert (browser allowing)
  useEffect(() => {
    if (latestAlert && !notified) {
      if ('vibrate' in navigator) navigator.vibrate([200, 100, 200])
      setNotified(true)
    }
    if (!latestAlert) setNotified(false)
  }, [latestAlert, notified])

  const handleAction = async (newStatus) => {
    setStatus(newStatus)
    try {
      const formData = new FormData()
      formData.append('status', newStatus.toLowerCase())
      await fetch(`${BACKEND_URL}/responder/status`, {
        method: 'POST',
        body: formData,
      })
    } catch (err) {
      console.error('Failed to update status:', err)
    }
  }

  const openMaps = () => {
    if (latestAlert) {
      const url = `https://www.google.com/maps?q=${latestAlert.lat},${latestAlert.lng}`
      window.open(url, '_blank')
    }
  }

  return (
    <div className="min-h-screen bg-[#050505] text-white font-sans overflow-x-hidden">
      {/* ── MISSION HEADER ── */}
      <header className="fixed top-0 inset-x-0 h-16 bg-black/60 backdrop-blur-2xl border-b border-white/5 flex items-center justify-between px-6 z-50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-red-600 flex items-center justify-center shadow-lg shadow-red-900/20">
            <span className="text-sm">🛡️</span>
          </div>
          <h1 className="text-xl font-black tracking-tighter">ANKURAH</h1>
        </div>
        
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-[9px] font-black uppercase tracking-widest ${
          isConnected ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-red-500/10 border-red-500/20 text-red-400'
        }`}>
          <div className={`w-1 h-1 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
          {isConnected ? 'NODE: ON' : 'OFFLINE'}
        </div>
      </header>

      <main className="pt-24 pb-32 px-6 max-w-lg mx-auto space-y-8">
        {!latestAlert ? (
          <div className="py-20 flex flex-col items-center justify-center text-center space-y-6">
            <div className="relative">
              <div className="absolute inset-0 bg-red-600/10 blur-3xl rounded-full" />
              <div className="w-24 h-24 rounded-full bg-zinc-900 border border-white/5 flex items-center justify-center relative">
                <div className="w-16 h-16 rounded-full border-2 border-dashed border-zinc-700 animate-[spin_10s_linear_infinite]" />
                <span className="absolute text-4xl">📡</span>
              </div>
            </div>
            <div className="space-y-1">
              <h2 className="text-xl font-black uppercase tracking-widest text-zinc-300">Scanning Grid</h2>
              <p className="text-zinc-500 text-xs font-medium">Listening for encrypted distress signals...</p>
            </div>
          </div>
        ) : (
          <div className="animate-in fade-in slide-in-from-bottom-8 duration-1000">
            {/* INCIDENT CARD */}
            <div className="space-y-6">
              <div className="flex items-end justify-between">
                <div>
                  <span className="text-[10px] font-black text-red-500 uppercase tracking-[0.3em] block mb-2">New Incident Detected</span>
                  <h2 className="text-4xl font-black tracking-tight leading-none uppercase italic">{latestAlert.location_name}</h2>
                </div>
                <div className="text-right">
                   <p className="text-[10px] font-mono text-zinc-500">ID: {latestAlert.camera_id}</p>
                   <p className="text-[10px] font-mono text-red-500 font-bold">{(latestAlert.confidence * 100).toFixed(0)}% MATCH</p>
                </div>
              </div>

              {/* LIVE VIEW */}
              <div className="relative aspect-[4/3] rounded-[2rem] overflow-hidden border border-white/10 shadow-2xl group">
                {latestAlert.snapshot_url ? (
                  <img 
                    src={`${BACKEND_URL}${latestAlert.snapshot_url}`} 
                    alt="Incident Scene" 
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center bg-zinc-900">
                    <div className="w-10 h-10 border-4 border-white/5 border-t-red-500 rounded-full animate-spin" />
                  </div>
                )}
                <div className="absolute top-6 left-6 flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/60 backdrop-blur-xl border border-white/10">
                   <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                   <span className="text-[10px] font-black uppercase tracking-widest">Live Capture</span>
                </div>
                {/* SCAN LINES */}
                <div className="absolute inset-0 pointer-events-none opacity-20 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_4px,4px_100%]" />
              </div>

              {/* ACTION HUB */}
              <div className="grid gap-4 pt-4">
                <button 
                  onClick={openMaps}
                  className="w-full py-6 rounded-3xl bg-white text-black font-black text-xl flex items-center justify-center gap-4 shadow-xl shadow-white/5 active:scale-95 transition-all"
                >
                  NAVIGATE TO SCENE
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  </svg>
                </button>

                <div className="grid grid-cols-2 gap-4">
                  <button 
                    onClick={() => handleAction('STARTED')}
                    disabled={status !== 'IDLE'}
                    className={`py-5 rounded-3xl flex flex-col items-center justify-center gap-2 border-2 transition-all active:scale-95 ${
                      status === 'STARTED' ? 'bg-emerald-500 border-emerald-400 text-white' :
                      status === 'REACHED' ? 'bg-zinc-800 border-zinc-700 text-zinc-500 grayscale' :
                      'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                    }`}
                  >
                    <span className="text-2xl">🏃</span>
                    <span className="text-[10px] font-black uppercase tracking-widest">MISSION START</span>
                  </button>
                  <button 
                    onClick={() => handleAction('REACHED')}
                    disabled={status !== 'STARTED'}
                    className={`py-5 rounded-3xl flex flex-col items-center justify-center gap-2 border-2 transition-all active:scale-95 ${
                      status === 'REACHED' ? 'bg-blue-600 border-blue-400 text-white' :
                      status === 'IDLE' ? 'bg-zinc-900 border-zinc-800 text-zinc-700 cursor-not-allowed opacity-50' :
                      'bg-blue-500/10 border-blue-500/20 text-blue-400'
                    }`}
                  >
                    <span className="text-2xl">📍</span>
                    <span className="text-[10px] font-black uppercase tracking-widest">SITE REACHED</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ── FOOTER STATUS ── */}
      <footer className="fixed bottom-0 inset-x-0 p-6 bg-gradient-to-t from-black via-black/90 to-transparent pointer-events-none">
         <div className="bg-zinc-900/80 backdrop-blur-xl border border-white/5 rounded-2xl p-4 flex items-center justify-between pointer-events-auto">
            <div className="flex items-center gap-3">
               <div className={`w-3 h-3 rounded-full ${status === 'IDLE' ? 'bg-zinc-600' : status === 'STARTED' ? 'bg-emerald-500 animate-pulse' : 'bg-blue-500'}`} />
               <div>
                  <p className="text-[10px] font-black uppercase tracking-widest text-zinc-500 leading-none">Status</p>
                  <p className="text-xs font-bold uppercase">{status === 'IDLE' ? 'On Standby' : status === 'STARTED' ? 'Responding' : 'On Site'}</p>
               </div>
            </div>
            <div className="text-right">
               <p className="text-[10px] font-black uppercase tracking-widest text-zinc-500 leading-none">Officer Ref</p>
               <p className="text-xs font-mono font-bold">ANK-902</p>
            </div>
         </div>
      </footer>
    </div>
  )
}
