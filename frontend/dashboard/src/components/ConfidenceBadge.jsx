export default function ConfidenceBadge({ confidence }) {
  const pct = Math.round(confidence * 100)

  let colorClasses = ''
  let bgClasses = ''

  if (confidence >= 0.9) {
    colorClasses = 'text-red-400'
    bgClasses = 'bg-red-500/20 border-red-500/30'
  } else if (confidence >= 0.7) {
    colorClasses = 'text-yellow-400'
    bgClasses = 'bg-yellow-500/20 border-yellow-500/30'
  } else {
    colorClasses = 'text-emerald-400'
    bgClasses = 'bg-emerald-500/20 border-emerald-500/30'
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${colorClasses} ${bgClasses} font-mono`}
    >
      {pct}%
    </span>
  )
}
