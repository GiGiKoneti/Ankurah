import { useState, useEffect } from 'react'

const DUMMY_CAMERAS = [
  { id: 'CAM-02', name: 'LIVE_DETECTOR', type: 'LIVE', location: 'Webcam Feed', src: null },
  { id: 'CAM-01', name: 'ENTRY_GATE', type: 'DUMMY', location: 'Perimeter A', src: '/videos/cam02.mp4' },
  { id: 'CAM-03', name: 'LOBBY_MAIN', type: 'DUMMY', location: 'Reception', src: '/videos/cam03.mp4' },
  { id: 'CAM-04', name: 'PARKING_B1', type: 'DUMMY', location: 'Level 1', src: '/videos/cam04.mp4' },
  { id: 'CAM-05', name: 'SERVER_ROOM', type: 'DUMMY', location: 'Data Center', src: '/videos/cam05.mp4' },
  { id: 'CAM-06', name: 'EXIT_NORTH', type: 'DUMMY', location: 'Perimeter B', src: '/videos/cam06.mp4' },
  { id: 'CAM-07', name: 'CAFETERIA', type: 'DUMMY', location: 'Area 4', src: '/videos/cam07.mp4' },
  { id: 'CAM-08', name: 'BACK_ALLEY', type: 'DUMMY', location: 'Loading Dock', src: '/videos/cam08.mp4' },
  { id: 'CAM-09', name: 'ROOFTOP_SEC', type: 'DUMMY', location: 'Mast 1', src: '/videos/cam09.mp4' },
]

export default function CameraGrid({ latestAlert }) {
  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {DUMMY_CAMERAS.map((cam, i) => (
        <div 
          key={cam.id} 
          className={`aspect-video rounded-2xl overflow-hidden bg-zinc-900 border transition-all duration-700 relative group ${
            latestAlert?.camera_id === cam.id 
              ? 'border-red-500 shadow-[0_0_40px_rgba(220,38,38,0.2)] scale-[1.02]' 
              : 'border-white/5 grayscale-[0.5] hover:grayscale-0'
          }`}
        >
          {/* Video / Image Display */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent z-10" />
          
          {cam.type === 'LIVE' ? (
            latestAlert?.snapshot_url ? (
              <img 
                src={`${BACKEND_URL}${latestAlert.snapshot_url}`} 
                alt="Live Detector Feed"
                className="w-full h-full object-cover animate-in fade-in duration-1000"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-zinc-900">
                <div className="text-center space-y-2">
                  <div className="w-8 h-8 border-2 border-white/10 border-t-red-500 rounded-full animate-spin mx-auto" />
                  <span className="text-[10px] font-black uppercase text-zinc-600 tracking-widest">Awaiting Live Feed</span>
                </div>
              </div>
            )
          ) : (
            <video 
              src={cam.src} 
              autoPlay 
              loop 
              muted 
              playsInline
              className="w-full h-full object-cover opacity-40 group-hover:opacity-60 transition-opacity"
              onError={(e) => {
                // Background fallback image if video file is missing
                e.target.style.display = 'none';
                e.target.nextSibling.style.display = 'block';
              }}
            />
          )}

          {/* Fallback Image (hidden by default unless video fails) */}
          <img 
            src={`https://images.unsplash.com/photo-1557597774-9d2739f85a76?q=80&w=800&auto=format&fit=crop&sig=${i}`} 
            alt="Camera Fallback"
            className="w-full h-full object-cover opacity-40 group-hover:opacity-60 transition-opacity hidden"
          />

          {/* Overlay Info */}
          <div className="absolute top-4 left-4 z-20 flex flex-col gap-1">
             <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${latestAlert?.camera_id === cam.id ? 'bg-red-500 animate-pulse' : 'bg-emerald-500'}`} />
                <span className="text-[10px] font-black uppercase tracking-widest text-zinc-100">{cam.name}</span>
             </div>
             <span className="text-[8px] font-bold text-zinc-500 uppercase tracking-tighter ml-4">{cam.location}</span>
          </div>

          <div className="absolute top-4 right-4 z-20">
             <span className="text-[8px] font-mono text-zinc-600 bg-black/40 px-1.5 py-0.5 rounded border border-white/5">CH: 00{i+1}</span>
          </div>

          {/* Alert Visuals — Subtle and Clear */}
          {latestAlert?.camera_id === cam.id && (
            <div className="absolute inset-0 z-30 flex items-center justify-center bg-red-600/5 border-2 border-red-500 animate-in fade-in duration-300">
               <div className="text-center bg-black/40 backdrop-blur-md px-4 py-2 rounded-xl border border-white/10">
                  <span className="text-2xl animate-bounce block">🚨</span>
                  <span className="text-[10px] font-black uppercase tracking-[0.3em] text-red-500 mt-1 block">Signal Identified</span>
               </div>
            </div>
          )}

          {/* Scan Line */}
          <div className="absolute inset-0 pointer-events-none z-40 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_2px,3px_100%] opacity-20" />
        </div>
      ))}
    </div>
  )
}
