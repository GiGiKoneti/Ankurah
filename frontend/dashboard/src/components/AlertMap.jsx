import { GoogleMap, useJsApiLoader, MarkerF, Circle } from '@react-google-maps/api'
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
      <div className="flex items-center justify-center h-full bg-zinc-900/50 rounded-3xl">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-white/10 border-t-red-500 rounded-full animate-spin" />
          <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Syncing Satellite Data...</span>
        </div>
      </div>
    )
  }

  const alertPos = latestAlert ? { lat: latestAlert.lat, lng: latestAlert.lng } : null

  return (
    <div className="w-full h-full">
      <GoogleMap
        mapContainerStyle={mapContainerStyle}
        center={alertPos || BENGALURU_CENTER}
        zoom={latestAlert ? 15 : 13}
        options={mapOptions}
      >
        {/* Static camera markers */}
        {CAMERAS.map((cam) => (
          <MarkerF
            key={cam.camera_id}
            position={{ lat: cam.lat, lng: cam.lng }}
            icon={{
              path: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z",
              fillColor: "#3f3f46",
              fillOpacity: 1,
              strokeColor: "#000",
              strokeWeight: 1,
              scale: 1.5,
              anchor: new google.maps.Point(12, 24),
            }}
          />
        ))}

        {/* Alert marker & Pins */}
        {latestAlert && (
          <>
            <MarkerF
              position={alertPos}
              animation={google.maps.Animation.BOUNCE}
              icon={{
                path: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z",
                fillColor: "#dc2626",
                fillOpacity: 1,
                strokeColor: "#fff",
                strokeWeight: 2,
                scale: 2,
                anchor: new google.maps.Point(12, 24),
              }}
            />
            {/* 3 Red Rings */}
            <Circle
              center={alertPos}
              radius={100}
              options={{
                fillColor: "#dc2626",
                fillOpacity: 0.2,
                strokeColor: "#dc2626",
                strokeWeight: 2,
              }}
            />
            <Circle
              center={alertPos}
              radius={250}
              options={{
                fillColor: "#dc2626",
                fillOpacity: 0.1,
                strokeColor: "#dc2626",
                strokeWeight: 1,
              }}
            />
            <Circle
              center={alertPos}
              radius={500}
              options={{
                fillColor: "#dc2626",
                fillOpacity: 0.05,
                strokeColor: "#dc2626",
                strokeWeight: 1,
              }}
            />
          </>
        )}
      </GoogleMap>
    </div>
  )
}
