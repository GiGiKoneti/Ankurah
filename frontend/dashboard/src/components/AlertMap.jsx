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
      <div className="flex items-center justify-center h-full bg-[#050505]/40 rounded-[2.5rem] backdrop-blur-md border border-white/5">
        <div className="flex flex-col items-center gap-6">
          <div className="w-16 h-16 border-4 border-white/5 border-t-red-600 rounded-full animate-spin shadow-[0_0_20px_rgba(220,38,38,0.2)]" />
          <span className="text-[10px] font-black uppercase tracking-[0.4em] text-zinc-600 animate-pulse">Syncing Tactical Grid</span>
        </div>
      </div>
    )
  }

  const alertPos = latestAlert ? { lat: latestAlert.lat, lng: latestAlert.lng } : null

  return (
    <div className="w-full h-full relative p-1">
      <div className="w-full h-full relative overflow-hidden rounded-[2.8rem] border border-white/10 shadow-inner">
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
                fillColor: "#27272a",
                fillOpacity: 1,
                strokeColor: "#000",
                strokeWeight: 2,
                scale: 1.2,
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
                  fillColor: "#ef4444",
                  fillOpacity: 1,
                  strokeColor: "#fff",
                  strokeWeight: 2,
                  scale: 1.8,
                }}
              />
              {/* Pulsing Alert Rings */}
              <Circle
                center={alertPos}
                radius={200}
                options={{
                  fillColor: "#dc2626",
                  fillOpacity: 0.15,
                  strokeWeight: 0,
                }}
              />
              <Circle
                center={alertPos}
                radius={400}
                options={{
                  fillColor: "#dc2626",
                  fillOpacity: 0.05,
                  strokeWeight: 0,
                }}
              />
            </>
          )}
        </GoogleMap>
        
        {/* Map Overlays: HUD aesthetic */}
        <div className="absolute inset-0 pointer-events-none border-[30px] border-black/20 rounded-[2.8rem]" />
        <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(0,0,0,0.02),rgba(0,0,0,0.01),rgba(0,0,0,0.02))] bg-[length:100%_4px,5px_100%] opacity-40 z-20" />
      </div>

      {/* Map Hud Controls (Decorative) */}
      <div className="absolute top-10 right-10 scale-90 z-30 pointer-events-none opacity-60">
         <div className="flex flex-col gap-3">
            <div className="bg-black/60 backdrop-blur-xl border border-white/10 p-4 rounded-2xl space-y-2">
               <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-[9px] font-black uppercase tracking-widest text-zinc-300">SAT_LINK_UP</span>
               </div>
               <div className="h-[1px] w-full bg-white/5" />
               <div className="flex flex-col">
                  <span className="text-[7px] font-mono text-zinc-600 uppercase">Sector</span>
                  <span className="text-[10px] font-black text-white italic">KA-HQ-09</span>
               </div>
            </div>
         </div>
      </div>
    </div>
  )
}
