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

  const confidence = Math.round(currentAlert.confidence * 100)

  return (
    <div
      id="threat-banner"
      className="w-full animate-slide-down relative overflow-hidden"
      style={{ animation: 'threat-pulse 1.5s ease-in-out infinite' }}
    >
      {/* Scan line effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute w-full h-[2px] bg-gradient-to-r from-transparent via-white/30 to-transparent"
          style={{ animation: 'scan-line 2s linear infinite' }}
        />
      </div>

      <div className="relative px-4 py-4 md:py-5 flex flex-col md:flex-row items-center justify-center gap-2 md:gap-6 text-white">
        {/* Alert icon with glow */}
        <span className="text-2xl md:text-3xl animate-bounce">🚨</span>

        <div className="text-center md:text-left">
          <div className="text-sm md:text-base font-black tracking-wider uppercase">
            Distress Signal Detected
          </div>
          <div className="text-xs md:text-sm font-semibold mt-1 opacity-90 flex flex-wrap items-center justify-center md:justify-start gap-2 md:gap-4">
            <span className="flex items-center gap-1">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              {currentAlert.location_name}
            </span>
            <span className="hidden md:inline text-white/40">|</span>
            <span className="font-mono">CAM: {currentAlert.camera_id}</span>
            <span className="hidden md:inline text-white/40">|</span>
            <span className="font-mono">Confidence: {confidence}%</span>
          </div>
        </div>

        {/* Countdown indicator */}
        <div className="hidden md:flex items-center gap-2 text-white/60 text-xs">
          <div className="w-2 h-2 rounded-full bg-white animate-ping" />
          ACTIVE
        </div>
      </div>
    </div>
  )
}
