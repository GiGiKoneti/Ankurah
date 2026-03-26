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
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 p-1">
      {DUMMY_CAMERAS.map((cam, i) => {
        const isAlerting = latestAlert?.camera_id === cam.id;
        
        return (
          <div 
            key={cam.id} 
            className={`aspect-video rounded-[2rem] overflow-hidden bg-[#0a0a0a] border-2 transition-all duration-1000 relative group ${
              isAlerting 
                ? 'border-red-600 shadow-[0_0_50px_-10px_rgba(220,38,38,0.5)] scale-[1.01]' 
                : 'border-white/5 grayscale-[0.3] hover:grayscale-0 hover:border-white/10'
            }`}
          >
            {/* Background Gradient */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-transparent to-transparent z-10" />
            
            {/* Media Stream */}
            <div className="absolute inset-0 z-0">
              {cam.type === 'LIVE' ? (
                latestAlert?.snapshot_url ? (
                  <img 
                    src={`${BACKEND_URL}${latestAlert.snapshot_url}`} 
                    alt="Live Feed"
                    className="w-full h-full object-cover animate-in fade-in zoom-in-110 duration-1000"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center bg-zinc-950">
                    <div className="w-12 h-12 border-4 border-white/5 border-t-red-600 rounded-full animate-spin mb-4" />
                    <span className="text-[10px] font-black uppercase text-zinc-700 tracking-[0.3em]">Synching Neural Link</span>
                  </div>
                )
              ) : (
                <div className="w-full h-full bg-zinc-950 relative">
                   <video 
                    src={cam.src} 
                    autoPlay 
                    loop 
                    muted 
                    playsInline
                    className="w-full h-full object-cover opacity-20 group-hover:opacity-40 transition-opacity duration-700"
                    onError={(e) => {
                      e.target.style.display = 'none';
                      e.target.nextSibling.style.display = 'block';
                    }}
                  />
                  <img 
                    src={`https://images.unsplash.com/photo-1557597774-9d2739f85a76?q=80&w=800&auto=format&fit=crop&sig=${i}`} 
                    alt="Camera Fallback"
                    className="absolute inset-0 w-full h-full object-cover opacity-10 group-hover:opacity-20 transition-opacity hidden"
                  />
                </div>
              )}
            </div>

            {/* Top Bar Info */}
            <div className="absolute top-6 left-8 right-8 z-20 flex justify-between items-start pointer-events-none">
               <div className="flex flex-col gap-1.5 translate-y-2 group-hover:translate-y-0 transition-transform duration-500">
                  <div className="flex items-center gap-3">
                     <div className={`w-2 h-2 rounded-full ${isAlerting ? 'bg-red-500 animate-pulse shadow-[0_0_10px_#ef4444]' : 'bg-emerald-500 shadow-[0_0_6px_#10b981]'}`} />
                     <span className="text-[11px] font-black uppercase tracking-[0.2em] text-white/90 drop-shadow-md">{cam.name}</span>
                  </div>
                  <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest ml-5 opacity-0 group-hover:opacity-100 transition-opacity duration-700 whitespace-nowrap">{cam.location}</span>
               </div>
               
               <div className="flex flex-col items-end gap-2">
                  <span className="text-[9px] font-mono text-white/40 bg-white/5 backdrop-blur-md px-2 py-1 rounded-lg border border-white/5 uppercase tracking-tighter transition-all group-hover:bg-white/10">CH: 0{i+1}</span>
                  {cam.type === 'LIVE' && (
                    <div className="px-2 py-1 rounded-md bg-red-600/10 border border-red-500/20 text-[8px] font-black text-red-500 tracking-widest uppercase">REC ●</div>
                  )}
               </div>
            </div>

            {/* Central Alert Overlay */}
            {isAlerting && (
              <div className="absolute inset-0 z-30 flex items-center justify-center bg-red-600/10 backdrop-blur-[2px] animate-in fade-in duration-500">
                 <div className="text-center bg-red-600 text-white px-8 py-4 rounded-3xl shadow-2xl shadow-red-900/50 flex flex-col items-center gap-3 border border-red-400/30 scale-100 animate-bounce">
                    <span className="text-3xl">🚨</span>
                    <div className="flex flex-col">
                       <span className="text-[11px] font-black uppercase tracking-[0.3em]">Distress Signal</span>
                       <span className="text-[8px] font-bold uppercase opacity-80 mt-1">Nodal Intersection 0x{i+1}</span>
                    </div>
                 </div>
              </div>
            )}

            {/* CRT / Scanlines Overlay */}
            <div className="absolute inset-0 pointer-events-none z-40 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(0,0,0,0.03),rgba(0,0,0,0.01),rgba(0,0,0,0.03))] bg-[length:100%_4px,5px_100%] opacity-40 group-hover:opacity-20 transition-opacity duration-1000" />
            
            {/* Corner Indicators (Decorative) */}
            <div className="absolute bottom-6 left-8 z-20 flex items-center gap-4 opacity-0 group-hover:opacity-100 transition-all duration-700 translate-y-4 group-hover:translate-y-0">
               <div className="flex flex-col">
                  <span className="text-[7px] font-mono text-zinc-600 uppercase tracking-widest">Latency</span>
                  <span className="text-[9px] font-mono text-emerald-500/80 font-bold tracking-tighter">{Math.floor(Math.random() * 20 + 5)}ms</span>
               </div>
               <div className="h-6 w-[1px] bg-white/5" />
               <div className="flex flex-col">
                  <span className="text-[7px] font-mono text-zinc-600 uppercase tracking-widest">Bitrate</span>
                  <span className="text-[9px] font-mono text-emerald-500/80 font-bold tracking-tighter">4.2 Mbps</span>
               </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
