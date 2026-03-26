export default function AlertLog({ alerts }) {
  const safeAlerts = Array.isArray(alerts) ? alerts : [];

  return (
    <div className="flex-grow flex flex-col overflow-hidden bg-zinc-950/20">
      <div className="overflow-y-auto flex-grow custom-scrollbar">
        <table className="w-full text-left border-collapse">
          <thead className="sticky top-0 z-10 bg-zinc-950/80 backdrop-blur-md">
            <tr className="border-b border-white/5">
              <th className="px-8 py-5 text-[9px] font-black uppercase tracking-[0.3em] text-zinc-600">Event Time</th>
              <th className="px-8 py-5 text-[9px] font-black uppercase tracking-[0.3em] text-zinc-600">Source Node</th>
              <th className="px-8 py-5 text-[9px] font-black uppercase tracking-[0.3em] text-zinc-600 text-right">Match</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.03]">
            {safeAlerts.length === 0 ? (
              <tr>
                <td colSpan="3" className="px-8 py-20 text-center">
                   <div className="flex flex-col items-center gap-4 opacity-20">
                      <span className="text-4xl">📡</span>
                      <p className="text-[10px] font-black uppercase tracking-[0.4em]">Listening for Neural Sync</p>
                   </div>
                </td>
              </tr>
            ) : (
              safeAlerts.map((alert, i) => {
                const isHighThreat = alert.confidence > 0.85;
                const isMediumThreat = alert.confidence > 0.6 && alert.confidence <= 0.85;

                return (
                  <tr key={i} className="hover:bg-white/[0.02] transition-colors group cursor-default">
                    <td className="px-8 py-5">
                       <span className="text-[11px] font-mono font-bold text-zinc-500 group-hover:text-zinc-300 transition-colors">
                          {new Date(alert.timestamp).toLocaleTimeString('en-GB', { hour12: false })}
                       </span>
                    </td>
                    <td className="px-8 py-5">
                       <div className="flex flex-col gap-0.5">
                          <span className="text-[12px] font-black tracking-tight text-white/90 group-hover:text-white transition-colors uppercase">{alert.camera_id}</span>
                          <span className="text-[9px] font-bold text-zinc-600 uppercase tracking-tighter transition-colors group-hover:text-zinc-400">{alert.location_name || 'UNDEFINED_ZONE'}</span>
                       </div>
                    </td>
                    <td className="px-8 py-5 text-right">
                       <div className={`px-3 py-1.5 rounded-lg inline-flex items-center gap-2 border transition-all duration-500 ${
                         isHighThreat ? 'bg-red-500/10 border-red-500/30 text-red-500 shadow-[0_0_15px_rgba(239,68,68,0.1)]' : 
                         isMediumThreat ? 'bg-amber-500/10 border-amber-500/20 text-amber-500' :
                         'bg-zinc-900/50 border-white/5 text-zinc-500'
                       }`}>
                          <div className={`w-1 h-1 rounded-full ${isHighThreat ? 'bg-red-500 animate-pulse' : isMediumThreat ? 'bg-amber-500' : 'bg-zinc-600'}`} />
                          <span className="text-[10px] font-black tracking-tighter leading-none">
                            {(alert.confidence * 100).toFixed(0)}%
                          </span>
                       </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.1);
        }
      `}</style>
    </div>
  )
}
