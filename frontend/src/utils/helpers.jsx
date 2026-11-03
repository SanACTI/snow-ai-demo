export const confColor = (c) =>
  c >= 0.8 ? '#10B981' : c >= 0.5 ? '#F59E0B' : '#EF4444'

export const riskColor = (r) => {
  const s = (r || '').replace('RiskLevel.', '')
  return {
    Critical: { bg: 'bg-red-900/40', text: 'text-red-400', border: 'border-red-800' },
    High:     { bg: 'bg-amber-900/40', text: 'text-amber-400', border: 'border-amber-800' },
    Medium:   { bg: 'bg-blue-900/40', text: 'text-blue-400', border: 'border-blue-800' },
    Low:      { bg: 'bg-green-900/40', text: 'text-green-400', border: 'border-green-800' },
  }[s] || { bg: 'bg-slate-800', text: 'text-slate-400', border: 'border-slate-700' }
}

export const priorityColor = (p) => ({
  P1: { bg: 'bg-red-900/40', text: 'text-red-400', border: 'border-red-800' },
  P2: { bg: 'bg-amber-900/40', text: 'text-amber-400', border: 'border-amber-800' },
  P3: { bg: 'bg-green-900/40', text: 'text-green-400', border: 'border-green-800' },
}[p] || { bg: 'bg-slate-800', text: 'text-slate-400', border: 'border-slate-700' })

export function Badge({ label, colors }) {
  return (
    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${colors.bg} ${colors.text} ${colors.border}`}>
      {label}
    </span>
  )
}