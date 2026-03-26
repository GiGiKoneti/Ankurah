import { GoogleMap, useJsApiLoader, MarkerF } from '@react-google-maps/api'
import { CAMERAS } from '../constants/cameras'

const GMAPS_KEY = import.meta.env.VITE_GMAPS_KEY
const BENGALURU_CENTER = { lat: 12.9716, lng: 77.5946 }

const mapContainerStyle = {
  width: '100%',
  height: '100%',
  minHeight: '400px',
}

const darkMapStyles = [
  { elementType: 'geometry', stylers: [{ color: '#1a1a2e' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#1a1a2e' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#6b7280' }] },
  {
    featureType: 'administrative.locality',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#9ca3af' }],
  },
  {
    featureType: 'road',
    elementType: 'geometry',
    stylers: [{ color: '#2d2d44' }],
  },
  {
    featureType: 'road',
    elementType: 'geometry.stroke',
    stylers: [{ color: '#1f1f35' }],
  },
  {
    featureType: 'road.highway',
    elementType: 'geometry',
    stylers: [{ color: '#3a3a55' }],
  },
  {
    featureType: 'water',
    elementType: 'geometry',
    stylers: [{ color: '#0e1525' }],
  },
  {
    featureType: 'water',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#4b5563' }],
  },
  {
    featureType: 'poi',
    elementType: 'geometry',
    stylers: [{ color: '#1a1a30' }],
  },
  {
    featureType: 'poi',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#6b7280' }],
  },
  {
    featureType: 'transit',
    elementType: 'geometry',
    stylers: [{ color: '#1a1a30' }],
  },
]

const mapOptions = {
  styles: darkMapStyles,
  disableDefaultUI: true,
  zoomControl: true,
  mapTypeControl: false,
  streetViewControl: false,
  fullscreenControl: false,
}

export default function AlertMap({ latestAlert }) {
  const { isLoaded } = useJsApiLoader({
    googleMapsApiKey: GMAPS_KEY,
  })

  if (!isLoaded) {
    return (
      <div className="glass-panel flex items-center justify-center" style={{ minHeight: '400px' }}>
        <div className="flex flex-col items-center gap-3 text-ops-muted">
          <div className="w-8 h-8 border-2 border-ops-muted border-t-safe-green rounded-full animate-spin" />
          <span className="text-sm">Loading map...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="map-container relative" style={{ minHeight: '400px' }}>
      <GoogleMap
        mapContainerStyle={mapContainerStyle}
        center={BENGALURU_CENTER}
        zoom={13}
        options={mapOptions}
      >
        {/* Static camera markers — grey/teal */}
        {CAMERAS.map((cam) => (
          <MarkerF
            key={cam.camera_id}
            position={{ lat: cam.lat, lng: cam.lng }}
            title={`${cam.camera_id} — ${cam.location_name}`}
            icon={{
              url: 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png',
              scaledSize: { width: 32, height: 32 },
            }}
          />
        ))}

        {/* Alert marker — RED */}
        {latestAlert && (
          <MarkerF
            position={{ lat: latestAlert.lat, lng: latestAlert.lng }}
            title={`🚨 ALERT — ${latestAlert.location_name} — ${latestAlert.camera_id}`}
            icon={{
              url: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png',
              scaledSize: { width: 44, height: 44 },
            }}
            animation={2} // BOUNCE
            zIndex={1000}
          />
        )}
      </GoogleMap>

      {/* Map overlay labels */}
      <div className="absolute top-3 left-3 bg-black/70 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-ops-border">
        <span className="text-xs font-semibold text-ops-muted uppercase tracking-wider">
          Live Incident Map
        </span>
      </div>

      {latestAlert && (
        <div className="absolute bottom-3 left-3 bg-red-900/80 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-red-500/40 animate-pulse-alert">
          <span className="text-xs font-bold text-red-200">
            🔴 Active Alert — {latestAlert.location_name}
          </span>
        </div>
      )}
    </div>
  )
}
