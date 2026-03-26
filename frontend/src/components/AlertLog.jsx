import ConfidenceBadge from './ConfidenceBadge'

export default function AlertLog({ alerts }) {
  if (alerts.length === 0) {
    return (
      <div className="glass-panel p-8 text-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
            <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-300">All Clear</p>
            <p className="text-xs text-ops-muted mt-1">No distress signals detected. Monitoring active.</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="glass-panel overflow-hidden">
      <div className="overflow-x-auto overflow-y-auto" style={{ maxHeight: '320px' }}>
        <table className="w-full text-sm" id="alert-log-table">
          <thead className="sticky top-0 z-10">
            <tr className="bg-ops-panel border-b border-ops-border">
              <th className="text-left px-4 py-3 text-[11px] font-bold text-ops-muted uppercase tracking-wider">
                Time
              </th>
              <th className="text-left px-4 py-3 text-[11px] font-bold text-ops-muted uppercase tracking-wider">
                Camera ID
              </th>
              <th className="text-left px-4 py-3 text-[11px] font-bold text-ops-muted uppercase tracking-wider hidden sm:table-cell">
                Location
              </th>
              <th className="text-left px-4 py-3 text-[11px] font-bold text-ops-muted uppercase tracking-wider">
                Confidence
              </th>
              <th className="text-left px-4 py-3 text-[11px] font-bold text-ops-muted uppercase tracking-wider hidden md:table-cell">
                Coordinates
              </th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((alert, index) => {
              const time = new Date(alert.timestamp)
              const timeStr = time.toLocaleTimeString('en-IN', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false,
              })

              return (
                <tr
                  key={`${alert.timestamp}-${alert.camera_id}-${index}`}
                  className={`
                    border-b border-ops-border/50 transition-colors
                    hover:bg-white/[0.02]
                    ${index === 0 ? 'alert-row-new' : ''}
                  `}
                >
                  <td className="px-4 py-3 font-mono text-xs text-gray-300 whitespace-nowrap">
                    {timeStr}
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs font-bold text-gray-200 bg-ops-border/50 px-2 py-0.5 rounded">
                      {alert.camera_id}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400 hidden sm:table-cell">
                    {alert.location_name}
                  </td>
                  <td className="px-4 py-3">
                    <ConfidenceBadge confidence={alert.confidence} />
                  </td>
                  <td className="px-4 py-3 font-mono text-[11px] text-ops-muted whitespace-nowrap hidden md:table-cell">
                    {alert.lat?.toFixed(4)}, {alert.lng?.toFixed(4)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
