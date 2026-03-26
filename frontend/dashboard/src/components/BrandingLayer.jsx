import { useEffect, useState } from 'react'

export default function BrandingLayer() {
  const [showTagline, setShowTagline] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setShowTagline(true), 800)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="min-h-screen bg-[#020408] flex flex-col items-center justify-center overflow-hidden selection:bg-red-500/30">
      {/* Decorative Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-20">
         <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-red-600/10 blur-[150px] rounded-full animate-pulse" />
         <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.4)_50%),linear-gradient(90deg,rgba(0,0,0,0.05),rgba(0,0,0,0),rgba(0,0,0,0.05))] bg-[length:100%_4px,100px_100%]" />
      </div>

      <div className="relative flex flex-col items-center gap-12 z-10">
        {/* Shield Logo Container */}
        <div className="relative group cursor-default">
          <div className="absolute inset-0 bg-red-600/30 blur-[60px] rounded-full group-hover:bg-red-600/50 transition-all duration-1000 scale-125" />
          
          <div className="relative animate-in zoom-in-75 fade-in duration-1000">
            <div className="w-40 h-40 rounded-[2.5rem] bg-zinc-950 border-2 border-white/5 flex items-center justify-center shadow-[0_40px_80px_-20px_rgba(220,38,38,0.3)] group-hover:shadow-[0_40px_100px_-10px_rgba(220,38,38,0.5)] transition-all duration-700">
               <div className="absolute inset-2 rounded-[2rem] border border-dashed border-red-500/20 animate-[spin_20s_linear_infinite]" />
               <div className="absolute inset-6 rounded-[1.5rem] border border-red-500/10 animate-[spin_10s_linear_reverse_infinite]" />
               <span className="text-7xl filter drop-shadow-2xl">🛡️</span>
            </div>
          </div>
        </div>

        {/* Brand Text */}
        <div className="flex flex-col items-center gap-4 text-center">
            <h1 className="text-6xl font-black italic tracking-tighter text-white animate-in slide-in-from-bottom-8 duration-700 delay-300">
               ANKURAH
            </h1>
            <div className={`transition-all duration-1000 h-6 overflow-hidden ${showTagline ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
               <p className="text-[11px] font-black uppercase tracking-[0.6em] text-red-500/80 drop-shadow-md">
                 SafeSight Neural Network
               </p>
            </div>
        </div>
      </div>

      {/* Progressive Loading Bar */}
      <div className="absolute bottom-24 flex flex-col items-center gap-6 z-10">
         <div className="w-64 h-1.5 bg-zinc-900/50 rounded-full border border-white/5 overflow-hidden shadow-inner">
            <div className="h-full bg-gradient-to-r from-red-800 via-red-500 to-red-800 animate-[loading-bar_4s_ease-in-out_infinite] shadow-[0_0_15px_rgba(220,38,38,0.5)]" />
         </div>
         <div className="flex flex-col items-center gap-2">
            <p className="text-zinc-500 font-mono text-[10px] uppercase tracking-[0.3em] font-black animate-pulse transition-all">
               Establishing Secure Uplink
            </p>
            <div className="flex gap-4 opacity-30 font-mono text-[8px] tracking-[0.4em] text-zinc-700">
               <span>NODE_001</span>
               <span>AES_V4</span>
               <span>NC_SYNC</span>
            </div>
         </div>
      </div>

      {/* Decorative Corner Elements */}
      <div className="absolute top-12 left-12 opacity-10 font-mono text-[9px] text-zinc-500 space-y-2 uppercase tracking-[0.2em] hidden md:block">
         <p>Protocol: DISPATCH_V2</p>
         <p>Secure Hash: SHA-512_EN</p>
         <p>Latency: 4.2ms</p>
      </div>
      
      <div className="absolute bottom-12 right-12 opacity-10 font-mono text-[9px] text-zinc-500 text-right uppercase tracking-[0.2em] hidden md:block">
         <p>© 2026 Ankurah Defense Systems</p>
         <p>Sector: HQ_OPS_NORTH</p>
      </div>
    </div>
  )
}
