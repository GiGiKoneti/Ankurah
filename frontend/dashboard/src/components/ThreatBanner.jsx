import { useEffect, useState } from 'react'

export default function ThreatBanner({ latestAlert }) {
  const [visible, setVisible] = useState(false)
  const [currentAlert, setCurrentAlert] = useState(null)

  useEffect(() => {
    if (latestAlert) {
      setCurrentAlert(latestAlert)
      setVisible(true)
      const t = setTimeout(() => setVisible(false), 10000)
      return () => clearTimeout(t)
    }
  }, [latestAlert])

  if (!visible || !currentAlert) return null

  return (
    <div className="relative group overflow-hidden z-[90]">
      {/* Intense Strobe Background */}
      <div className="absolute inset-0 bg-red-600 animate-[pulse_0.8s_cubic-bezier(0.4,0,0.6,1)_infinite] opacity-90 shadow-[0_0_80px_rgba(220,38,38,0.6)]" />
      
      {/* Glass Overlay for Text Readability */}
      <div className="absolute inset-0 bg-black/10 backdrop-blur-[2px] z-0" />
      
      {/* Scan Line Background */}
      <div className="absolute inset-0 opacity-20 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,255,255,0.08),rgba(255,255,255,0.04),rgba(255,255,255,0.08))] bg-[length:100%_2px,4px_100%] z-10" />
      
      <div className="max-w-[1920px] mx-auto px-10 py-6 flex flex-col md:flex-row items-center justify-between text-white relative z-20 gap-6 md:gap-0">
        <div className="flex flex-col md:flex-row items-center gap-10">
           <div className="flex items-center gap-6">
              <div className="w-16 h-16 rounded-full bg-white/10 border-4 border-white animate-pulse flex items-center justify-center text-4xl shadow-2xl">
                 🚨
              </div>
              <div className="text-center md:text-left">
                 <h3 className="text-3xl font-black italic tracking-tighter leading-none mb-1">IMMEDIATE RED ALERT</h3>
                 <p className="text-[10px] font-black uppercase tracking-[0.5em] text-white/80 animate-pulse">NEURAL DISTRESS SIGNAL IDENTIFIED</p>
              </div>
           </div>

           <div className="hidden lg:block h-14 w-[1px] bg-white/20 mx-6" />

           <div className="flex flex-col items-center md:items-start space-y-2">
              <div className="flex items-center gap-3">
                 <span className="text-[10px] font-mono font-black uppercase bg-black/40 px-3 py-1 rounded-lg border border-white/20 tracking-[0.2em] shadow-inner">{currentAlert.camera_id}</span>
                 <span className="text-2xl font-black uppercase italic tracking-tight drop-shadow-lg">{currentAlert.location_name}</span>
              </div>
              <div className="flex items-center gap-4 text-[10px] font-mono font-bold text-white/90">
                <span className="bg-red-900/40 px-2 py-0.5 rounded tracking-tighter whitespace-nowrap">COORD: {currentAlert.lat}, {currentAlert.lng}</span>
                <span className="h-1 w-1 rounded-full bg-white/40" />
                <span className="tracking-widest flex items-center gap-2">
                   MATCH: 
                   <span className="text-white bg-green-500/80 px-1.5 py-0.5 rounded leading-none">{(currentAlert.confidence * 100).toFixed(0)}%</span>
                </span>
              </div>
           </div>
        </div>

        <div className="flex items-center gap-8">
           <div className="text-right hidden xl:block">
              <p className="text-[10px] font-black uppercase tracking-[0.3em] leading-none mb-2 text-white/70">Intercepted Time</p>
              <p className="text-sm font-mono font-black drop-shadow-sm">{new Date(currentAlert.timestamp).toLocaleTimeString('en-GB', { hour12: false, second: '2-digit' })}</p>
           </div>
           
           <div className="relative w-16 h-16 flex items-center justify-center">
              <div className="absolute inset-0 border-4 border-white/10 rounded-full" />
              <div className="absolute inset-0 border-4 border-t-white rounded-full animate-spin shadow-[0_0_15px_rgba(255,255,255,0.4)]" />
              <div className="text-[9px] font-black uppercase tracking-tighter opacity-80">Sync</div>
           </div>
        </div>
      </div>
    </div>
  )
}
