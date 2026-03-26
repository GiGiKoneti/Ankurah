import { useEffect, useState, useRef } from 'react'
import { CAMERAS } from '../constants/cameras'

export default function CameraGrid({ latestAlert }) {
  const [flashingCamera, setFlashingCamera] = useState(null)
  const [lastAlertTimes, setLastAlertTimes] = useState({})
  const [, forceUpdate] = useState(0)
  const tickRef = useRef(null)

  // Track which camera is flashing and last alert time
  useEffect(() => {
    if (latestAlert) {
      setFlashingCamera(latestAlert.camera_id)
      setLastAlertTimes(prev => ({
        ...prev,
        [latestAlert.camera_id]: Date.now()
      }))
      const t = setTimeout(() => setFlashingCamera(null), 5000)
      return () => clearTimeout(t)
    }
  }, [latestAlert])

  // Tick every second to update "X seconds ago"
  useEffect(() => {
    tickRef.current = setInterval(() => forceUpdate(n => n + 1), 1000)
    return () => clearInterval(tickRef.current)
  }, [])

  function getTimeAgo(cameraId) {
    const ts = lastAlertTimes[cameraId]
    if (!ts) return null
    const seconds = Math.floor((Date.now() - ts) / 1000)
    if (seconds < 60) return `${seconds}s ago`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
    return `${Math.floor(seconds / 3600)}h ago`
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-4">
      {CAMERAS.map((cam) => {
        const isFlashing = flashingCamera === cam.camera_id
        const timeAgo = getTimeAgo(cam.camera_id)

        return (
          <div
            key={cam.camera_id}
            id={`camera-card-${cam.camera_id}`}
            className={`
              glass-panel p-4 transition-all duration-300
              ${isFlashing
                ? 'animate-flash-red border-red-500 !bg-red-950/40'
                : 'hover:border-ops-border/80'
              }
            `}
          >
            {/* Header row */}
            <div className="flex items-center justify-between mb-3">
              <span className="font-mono text-sm font-bold text-gray-200">
                {cam.camera_id}
              </span>
              <div className="flex items-center gap-1.5">
                {isFlashing ? (
                  <>
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                    <span className="text-[10px] font-bold text-red-400 uppercase tracking-wider">
                      Alert
                    </span>
                  </>
                ) : (
                  <>
                    <span className="status-dot-live" />
                    <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">
                      Active
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Location */}
            <div className="flex items-start gap-2 mb-3">
              <svg className="w-3.5 h-3.5 mt-0.5 text-ops-muted shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span className="text-sm text-gray-300 leading-tight">{cam.location_name}</span>
            </div>

            {/* Coordinates */}
            <div className="text-[11px] font-mono text-ops-muted mb-2">
              {cam.lat.toFixed(4)}°N, {cam.lng.toFixed(4)}°E
            </div>

            {/* Last alert time */}
            {timeAgo && (
              <div className={`text-[11px] font-semibold mt-1 ${
                isFlashing ? 'text-red-400' : 'text-ops-muted'
              }`}>
                Last alert: {timeAgo}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
