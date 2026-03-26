import { useEffect, useState } from 'react'

export default function BrandingLayer() {
  const [showTagline, setShowTagline] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setShowTagline(true), 1200)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center overflow-hidden">
      <div className="relative">
        {/* Glow Effect */}
        <div className="absolute inset-0 bg-red-600/20 blur-[120px] rounded-full animate-pulse" />
        
        {/* Shield Logo */}
        <div className="relative animate-in zoom-in-50 duration-1000">
          <div className="w-32 h-32 rounded-3xl bg-gradient-to-br from-red-600 to-red-900 flex items-center justify-center shadow-[0_0_60px_rgba(220,38,38,0.4)] border border-red-500/30">
            <span className="text-6xl filter drop-shadow-2xl">🛡️</span>
          </div>
        </div>
      </div>

      <div className="mt-10 text-center space-y-2">
           ANKURAH
        
      </div>

      {/* Loading Indicator */}
      <div className="absolute bottom-20 w-48 h-1 bg-zinc-900 rounded-full overflow-hidden">
        <div className="h-full bg-red-600 animate-loading-bar" />
      </div>
      
      <p className="absolute bottom-12 text-zinc-700 font-mono text-[9px] uppercase tracking-widest">
        Initializing Neural Security Grid v2.0
      </p>
    </div>
  )
}
