export default function AlertLog({ alerts }) {
  return (
    <div className="bg-zinc-900/40 rounded-3xl border border-white/5 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-white/5 bg-white/[0.02]">
              <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-zinc-500">Timestamp</th>
              <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-zinc-500">Device</th>
              <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-zinc-500 text-right">Confidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.02]">
            {alerts.length === 0 ? (
              <tr>
                <td colSpan="3" className="px-6 py-12 text-center">
                   <p className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">No Signals Logged</p>
                </td>
              </tr>
            ) : (
              alerts.map((alert, i) => (
                <tr key={i} className="hover:bg-white/[0.01] transition-colors group">
                  <td className="px-6 py-4">
                     <span className="text-[10px] font-mono text-zinc-400">{new Date(alert.timestamp).toLocaleTimeString()}</span>
                  </td>
                  <td className="px-6 py-4">
                     <div className="flex flex-col">
                        <span className="text-[11px] font-black tracking-tight">{alert.camera_id}</span>
                        <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-tighter">{alert.location_name}</span>
                     </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                     <span className={`text-[10px] font-black px-2 py-0.5 rounded ${
                       alert.confidence > 0.8 ? 'bg-red-500/10 text-red-500 border border-red-500/20' : 'bg-zinc-800 text-zinc-400'
                     }`}>
                        {(alert.confidence * 100).toFixed(0)}%
                     </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
