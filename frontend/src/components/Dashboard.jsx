import { useEffect, useState } from 'react'
import { useSSE } from '../hooks/useSSE'
import ThreatBanner from './ThreatBanner'
import AlertMap from './AlertMap'
import CameraGrid from './CameraGrid'
import AlertLog from './AlertLog'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL

export default function Dashboard() {
  const { latestAlert, alerts, setAlerts, isConnected, lastHeartbeat } = useSSE()
  const [currentTime, setCurrentTime] = useState(new Date())

  // Fetch past alerts on mount to hydrate the log
  useEffect(() => {
    fetch(`${BACKEND_URL}/alerts`)
      .then(r => r.json())
      .then(data => {
        if (data.alerts && data.alerts.length > 0) {
          setAlerts(data.alerts)
        }
      })
      .catch(err => console.warn('[Dashboard] Could not fetch /alerts:', err))
  }, [])

  // Update clock every second
  useEffect(() => {
    const t = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const timeStr = currentTime.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })

  const dateStr = currentTime.toLocaleDateString('en-IN', {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })

  return (
    <div className="min-h-screen bg-ops-black text-gray-100">
      {/* ── Header ── */}
      <header className="bg-ops-dark border-b border-ops-border sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-4 md:px-6 py-3 flex items-center justify-between">
          {/* Left — Brand */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-red-600 to-red-800 flex items-center justify-center shadow-lg shadow-red-900/30">
              <span className="text-lg">🛡️</span>
            </div>
            <div>
              <h1 className="text-base md:text-lg font-black tracking-tight text-white leading-none">
                Ankurah
              </h1>
              <p className="text-[10px] md:text-[11px] text-ops-muted font-medium tracking-wider uppercase">
                Police Control Room
              </p>
            </div>
          </div>

          {/* Center — Clock (hidden on mobile) */}
          <div className="hidden md:flex flex-col items-center">
            <span className="font-mono text-xl font-bold text-white tracking-widest">
              {timeStr}
            </span>
            <span className="text-[10px] text-ops-muted font-medium uppercase tracking-wider">
              {dateStr}
            </span>
          </div>

          {/* Right — Connection status */}
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex flex-col items-end text-[10px] text-ops-muted">
              <span>Alerts: <span className="text-white font-bold font-mono">{alerts.length}</span></span>
              <span>Cameras: <span className="text-emerald-400 font-bold font-mono">3</span></span>
            </div>
            <div
              id="connection-status"
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold ${
                isConnected
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                  : 'bg-red-500/10 border-red-500/30 text-red-400'
              }`}
            >
              {isConnected ? (
                <>
                  <span className="status-dot-live" />
                  <span>Live</span>
                </>
              ) : (
                <>
                  <span className="status-dot-dead" />
                  <span>Disconnected</span>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* ── Threat Banner (only on alert) ── */}
      <ThreatBanner latestAlert={latestAlert} />

      {/* ── Main Content ── */}
      <main className="max-w-[1600px] mx-auto px-4 md:px-6 py-4 md:py-6 space-y-4 md:space-y-6">

        {/* Two-column layout: Map (left, larger) + Cameras (right) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
          {/* Map — takes 2/3 width */}
          <section className="lg:col-span-2 animate-fade-in">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
                <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                </svg>
                Incident Map
              </h2>
              {latestAlert && (
                <span className="text-[10px] font-bold text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-1 rounded-full animate-pulse-alert">
                  ● ACTIVE INCIDENT
                </span>
              )}
            </div>
            <AlertMap latestAlert={latestAlert} />
          </section>

          {/* Camera Grid — takes 1/3 width */}
          <section className="animate-fade-in" style={{ animationDelay: '0.1s' }}>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
                <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Camera Network
              </h2>
              <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-1 rounded-full">
                3 ONLINE
              </span>
            </div>
            <CameraGrid latestAlert={latestAlert} />
          </section>
        </div>

        {/* Alert Log — full width */}
        <section className="animate-fade-in" style={{ animationDelay: '0.2s' }}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
              <svg className="w-4 h-4 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Alert Log
            </h2>
            <span className="text-[10px] font-mono text-ops-muted">
              {alerts.length} records
            </span>
          </div>
          <AlertLog alerts={alerts} />
        </section>
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-ops-border mt-6">
        <div className="max-w-[1600px] mx-auto px-4 md:px-6 py-3 flex items-center justify-between text-[10px] text-ops-muted">
          <span>Ankurah v1.0 — Ankurah Project</span>
          <span className="font-mono">
            {isConnected ? `SSE ↔ ${BACKEND_URL}` : 'Backend unreachable'}
          </span>
        </div>
      </footer>
    </div>
  )
}
