import { useEffect, useState } from 'react'

export default function ThreatBanner({ latestAlert }) {
  const [visible, setVisible] = useState(false)
  const [currentAlert, setCurrentAlert] = useState(null)

  useEffect(() => {
    if (latestAlert) {
      setCurrentAlert(latestAlert)
      setVisible(true)
      const t = setTimeout(() => setVisible(false), 8000)
      return () => clearTimeout(t)
    }
  }, [latestAlert])

  if (!visible || !currentAlert) return null

  return (
    <div className="bg-red-600 relative overflow-hidden shadow-[0_0_60px_rgba(220,38,38,0.4)] z-[90]">
      {/* Scan Line Background */}
      <div className="absolute inset-0 opacity-10 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02),rgba(255,255,255,0.06))] bg-[length:100%_4px,4px_100%]" />
      
      <div className="max-w-[1600px] mx-auto px-8 py-5 flex items-center justify-between text-white relative z-10">
        <div className="flex items-center gap-8">
           <div className="flex items-center gap-4">
              <span className="text-4xl animate-bounce">🚨</span>
              <div>
                 <h3 className="text-2xl font-black italic tracking-tighter leading-none">THREAT IDENTIFIED</h3>
                 <p className="text-[10px] font-bold uppercase tracking-[0.4em] opacity-80">Immediate Response Required</p>
              </div>
           </div>

           <div className="h-10 w-[1px] bg-white/20 mx-4" />

           <div className="space-y-1">
              <div className="flex items-center gap-2">
                 <span className="text-xs font-black uppercase bg-black/20 px-2 py-0.5 rounded border border-white/10 tracking-widest">{currentAlert.camera_id}</span>
                 <span className="text-lg font-bold tracking-tight">{currentAlert.location_name}</span>
              </div>
              <p className="text-[10px] font-mono opacity-80 uppercase tracking-widest">
                COORD: {currentAlert.lat}, {currentAlert.lng} • CONFIDENCE: {(currentAlert.confidence * 100).toFixed(0)}%
              </p>
           </div>
        </div>

        <div className="flex items-center gap-4">
           <div className="text-right hidden md:block">
              <p className="text-[10px] font-black uppercase tracking-widest leading-none">Signal Intercepted</p>
              <p className="text-xs font-mono opacity-80">{new Date(currentAlert.timestamp).toLocaleTimeString()}</p>
           </div>
           <div className="w-12 h-12 rounded-full border-4 border-white/20 border-t-white animate-spin" />
        </div>
      </div>
    </div>
  )
}
