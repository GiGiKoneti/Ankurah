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
    <div className="min-h-screen bg-[#020408] text-white font-sans overflow-x-hidden selection:bg-red-500/30">
      {/* ── MISSION HEADER ── */}
      <header className="fixed top-0 inset-x-0 h-20 bg-black/60 backdrop-blur-2xl border-b border-white/5 flex items-center justify-between px-8 z-50">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-red-600 flex items-center justify-center shadow-lg shadow-red-900/30 border border-red-500/20">
            <span className="text-lg">🛡️</span>
          </div>
          <div className="flex flex-col">
            <h1 className="text-xl font-black tracking-tighter leading-none">ANKURAH</h1>
            <span className="text-[8px] text-zinc-600 font-bold uppercase tracking-[0.4em] mt-1.5">Responder Unit</span>
          </div>
        </div>
        
        <div className={`flex items-center gap-3 px-4 py-1.5 rounded-2xl border text-[9px] font-black uppercase tracking-widest transition-colors duration-500 ${
          isConnected ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-red-500/10 border-red-500/20 text-red-400'
        }`}>
          <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
          {isConnected ? 'NODE: LIVE' : 'OFFLINE'}
        </div>
      </header>

      <main className="pt-28 pb-40 px-6 max-w-xl mx-auto space-y-10">
        {!latestAlert ? (
          <div className="py-24 flex flex-col items-center justify-center text-center space-y-8 animate-in fade-in duration-1000">
            <div className="relative">
              <div className="absolute inset-0 bg-red-600/10 blur-[100px] rounded-full animate-pulse" />
              <div className="w-32 h-32 rounded-[2.5rem] bg-zinc-950 border border-white/5 flex items-center justify-center relative shadow-2xl">
                <div className="absolute inset-2 rounded-[2rem] border border-dashed border-zinc-800 animate-[spin_15s_linear_infinite]" />
                <span className="absolute text-5xl">📡</span>
              </div>
            </div>
            <div className="space-y-3">
              <h2 className="text-2xl font-black uppercase tracking-[0.2em] text-white/90">Scanning Grid</h2>
              <p className="text-zinc-600 text-sm font-medium leading-relaxed max-w-xs mx-auto">Listening for encrypted neural distress signals across the sector...</p>
            </div>
          </div>
        ) : (
          <div className="animate-in fade-in slide-in-from-bottom-12 duration-700 space-y-10">
            <div className="space-y-8">
              <div className="flex items-end justify-between border-l-4 border-red-600 pl-6 rounded-sm">
                <div className="flex flex-col gap-2">
                  <span className="text-[10px] font-black text-red-500 uppercase tracking-[0.5em] block animate-pulse">Critical Incident Detected</span>
                  <h2 className="text-5xl font-black tracking-tighter leading-none uppercase italic text-white/95">{latestAlert.location_name}</h2>
                </div>
                <div className="text-right flex flex-col items-end gap-2">
                   <p className="text-[10px] font-mono font-bold text-zinc-600 px-2 py-1 bg-zinc-900 rounded border border-white/5 tracking-tighter uppercase whitespace-nowrap">ID: {latestAlert.camera_id}</p>
                   <p className="text-xs font-black text-red-500 tracking-widest whitespace-nowrap">{(latestAlert.confidence * 100).toFixed(0)}% MATCH</p>
                </div>
              </div>

              <div className="relative aspect-[4/3] rounded-[3rem] overflow-hidden border-2 border-white/10 shadow-[0_40px_100px_-20px_rgba(0,0,0,0.8)] group">
                <div className="absolute inset-0 bg-zinc-950 flex items-center justify-center">
                  {latestAlert.snapshot_url ? (
                    <img 
                      src={`${BACKEND_URL}${latestAlert.snapshot_url}`} 
                      alt="Incident Feed" 
                      className="w-full h-full object-cover animate-in fade-in zoom-in-110 duration-1000"
                    />
                  ) : (
                    <div className="flex flex-col items-center gap-4">
                      <div className="w-12 h-12 border-4 border-white/5 border-t-red-600 rounded-full animate-spin" />
                      <span className="text-[10px] font-black uppercase tracking-widest text-zinc-700">Linking Neural Stream</span>
                    </div>
                  )}
                </div>

                <div className="absolute top-8 left-8 flex items-center gap-3 px-4 py-2 rounded-2xl bg-black/60 backdrop-blur-2xl border border-white/10 shadow-2xl">
                   <div className="w-2 h-2 rounded-full bg-red-600 animate-pulse shadow-[0_0_8px_#ef4444]" />
                   <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/90">Tactical Feed</span>
                </div>
                <div className="absolute inset-0 pointer-events-none opacity-30 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(0,0,0,0.04),rgba(0,0,0,0.01),rgba(0,0,0,0.04))] bg-[length:100%_4px,5px_100%] z-10" />
              </div>

              <div className="flex flex-col gap-5 pt-4">
                <button 
                  onClick={openMaps}
                  className="w-full py-8 rounded-[2.5rem] bg-white text-black font-black text-2xl flex items-center justify-center gap-6 shadow-2xl shadow-white/5 hover:bg-zinc-100 active:scale-[0.98] transition-all duration-300"
                >
                  NAV_TO_INCIDENT
                  <div className="w-12 h-12 rounded-2xl bg-black/5 flex items-center justify-center border border-black/5">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    </svg>
                  </div>
                </button>

                <div className="grid grid-cols-2 gap-5">
                  <button 
                    onClick={() => handleAction('STARTED')}
                    disabled={status !== 'IDLE'}
                    className={`py-8 rounded-[2.5rem] flex flex-col items-center justify-center gap-3 border-2 transition-all duration-500 active:scale-95 ${
                      status === 'STARTED' ? 'bg-emerald-600 border-emerald-400 text-white shadow-[0_0_30px_rgba(16,185,129,0.3)]' :
                      status === 'REACHED' ? 'bg-zinc-900/50 border-zinc-800 text-zinc-700 grayscale' :
                      'bg-emerald-500/5 border-emerald-500/20 text-emerald-500'
                    }`}
                  >
                    <span className="text-3xl">🏃</span>
                    <span className="text-[11px] font-black uppercase tracking-widest leading-none">Acknowledge</span>
                  </button>
                  <button 
                    onClick={() => handleAction('REACHED')}
                    disabled={status !== 'STARTED'}
                    className={`py-8 rounded-[2.5rem] flex flex-col items-center justify-center gap-3 border-2 transition-all duration-500 active:scale-95 ${
                      status === 'REACHED' ? 'bg-blue-600 border-blue-400 text-white shadow-[0_0_30px_rgba(37,99,235,0.3)]' :
                      status === 'IDLE' ? 'bg-zinc-950 border-zinc-900 text-zinc-800 cursor-not-allowed' :
                      'bg-blue-500/5 border-blue-500/20 text-blue-400'
                    }`}
                  >
                    <span className="text-3xl">📍</span>
                    <span className="text-[11px] font-black uppercase tracking-widest leading-none">Confirm Site</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="fixed bottom-0 inset-x-0 p-8 pt-20 bg-gradient-to-t from-black via-black/95 to-transparent pointer-events-none">
         <div className="bg-zinc-950 border border-white/10 rounded-[2rem] p-6 pr-8 flex items-center justify-between pointer-events-auto shadow-2xl">
            <div className="flex items-center gap-5">
               <div className={`w-4 h-4 rounded-full shadow-[0_0_15px_-2px_rgba(255,255,255,0.2)] ${status === 'IDLE' ? 'bg-zinc-800' : status === 'STARTED' ? 'bg-emerald-500 animate-pulse' : 'bg-blue-500'}`} />
               <div className="flex flex-col gap-1">
                  <p className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-600 leading-none">System Status</p>
                  <p className="text-[13px] font-black uppercase tracking-tight text-white/90 leading-none">{status === 'IDLE' ? 'UNIT_STANDBY' : status === 'STARTED' ? 'EN_ROUTE_SIGNAL' : 'SITE_LOCALIZED'}</p>
               </div>
            </div>
            <div className="text-right">
               <p className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-600 leading-none mb-1">Badge Ref</p>
               <p className="text-[13px] font-mono font-black text-white/90 leading-none">0XC-942</p>
            </div>
         </div>
      </footer>
    </div>
  )
}
