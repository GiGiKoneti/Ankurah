import { useEffect, useState, useRef } from 'react'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL

export function useSSE() {
  const [alerts, setAlerts] = useState([])
  const [latestAlert, setLatestAlert] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [lastHeartbeat, setLastHeartbeat] = useState(null)
  const reconnectAttempts = useRef(0)

  useEffect(() => {
    let es = null
    let isCancelled = false

    function connect() {
      if (isCancelled) return

      es = new EventSource(`${BACKEND_URL}/stream`)

      es.onopen = () => {
        setIsConnected(true)
        reconnectAttempts.current = 0
      }

      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          if (data.type === 'alert') {
            setLatestAlert(data)
            setAlerts(prev => [data, ...prev].slice(0, 50))
          } else if (data.type === 'heartbeat') {
            setLastHeartbeat(data.ts)
          }
        } catch (err) {
          console.warn('[SSE] Failed to parse event data:', err)
        }
      }

      es.onerror = () => {
        setIsConnected(false)
        es.close()
        // Exponential backoff reconnect
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
        reconnectAttempts.current += 1
        setTimeout(() => connect(), delay)
      }
    }

    connect()

    return () => {
      isCancelled = true
      if (es) es.close()
    }
  }, [])

  // ── MOCK — uncomment for testing without backend ──
  // useEffect(() => {
  //   setIsConnected(true)
  //   const interval = setInterval(() => {
  //     const cameras = [
  //       { camera_id: 'CAM-01', lat: 12.9747, lng: 77.6094, location_name: 'MG Road Junction' },
  //       { camera_id: 'CAM-02', lat: 12.9352, lng: 77.6245, location_name: 'Koramangala Market' },
  //       { camera_id: 'CAM-03', lat: 12.9784, lng: 77.6408, location_name: 'Indiranagar Metro' },
  //     ]
  //     const cam = cameras[Math.floor(Math.random() * cameras.length)]
  //     const mockAlert = {
  //       type: 'alert',
  //       camera_id: cam.camera_id,
  //       confidence: +(0.6 + Math.random() * 0.39).toFixed(2),
  //       timestamp: new Date().toISOString(),
  //       lat: cam.lat,
  //       lng: cam.lng,
  //       location_name: cam.location_name
  //     }
  //     setLatestAlert(mockAlert)
  //     setAlerts(prev => [mockAlert, ...prev].slice(0, 50))
  //   }, 5000) // Trigger every 5 seconds for faster testing
  //   return () => clearInterval(interval)
  // }, [])

  return { latestAlert, alerts, setAlerts, isConnected, lastHeartbeat }
}
