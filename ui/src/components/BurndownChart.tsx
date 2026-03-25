import type { BurndownDataPoint } from '../lib/types'

interface BurndownChartProps {
  points: BurndownDataPoint[]
  total: number
}

export function BurndownChart({ points, total }: BurndownChartProps) {
  if (points.length === 0 || total === 0) {
    return (
      <div className="text-sm text-muted-foreground text-center py-6">
        Geen burn-down data. Features worden getrackt zodra ze passing zijn.
      </div>
    )
  }

  const W = 320
  const H = 130
  const PAD = { top: 8, right: 12, bottom: 28, left: 28 }
  const plotW = W - PAD.left - PAD.right
  const plotH = H - PAD.top - PAD.bottom
  const n = points.length

  const xScale = (i: number) => PAD.left + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW)
  const yScale = (v: number) => PAD.top + plotH - Math.max(0, Math.min(1, v / total)) * plotH

  // Actual remaining polyline
  const actualPts = points.map((p, i) => `${xScale(i).toFixed(1)},${yScale(p.remaining).toFixed(1)}`).join(' ')

  // Ideal line: linear from total → 0
  const idealX0 = xScale(0)
  const idealY0 = yScale(total)
  const idealX1 = xScale(n - 1)
  const idealY1 = yScale(0)

  // Fill area under actual line
  const fillPts = `${actualPts} ${xScale(n - 1).toFixed(1)},${(PAD.top + plotH).toFixed(1)} ${xScale(0).toFixed(1)},${(PAD.top + plotH).toFixed(1)}`

  // Y-axis labels: 0, half, total
  const yLabels = [
    { v: 0, y: yScale(0) },
    { v: Math.round(total / 2), y: yScale(total / 2) },
    { v: total, y: yScale(total) },
  ]

  // X-axis labels: first and last date
  const dateLabel = (iso: string) => {
    const d = new Date(iso)
    return `${d.getDate()}/${d.getMonth() + 1}`
  }
  const xLabels = n === 1
    ? [{ i: 0, label: dateLabel(points[0].date) }]
    : [
        { i: 0, label: dateLabel(points[0].date) },
        { i: n - 1, label: dateLabel(points[n - 1].date) },
        ...(n > 4 ? [{ i: Math.round((n - 1) / 2), label: dateLabel(points[Math.round((n - 1) / 2)].date) }] : []),
      ]

  // Passed count for annotation on last point
  const lastPassed = points[n - 1].passed
  const lastRemaining = points[n - 1].remaining

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" aria-label="Burn-down chart">
        {/* Horizontal grid lines */}
        {yLabels.map(({ v, y }) => (
          <line
            key={v}
            x1={PAD.left}
            y1={y}
            x2={PAD.left + plotW}
            y2={y}
            stroke="currentColor"
            strokeOpacity={0.1}
            strokeWidth={1}
          />
        ))}

        {/* Ideal burn-down (dashed gray) */}
        <line
          x1={idealX0}
          y1={idealY0}
          x2={idealX1}
          y2={idealY1}
          stroke="currentColor"
          strokeOpacity={0.3}
          strokeWidth={1.5}
          strokeDasharray="5,4"
        />

        {/* Area fill */}
        <polygon points={fillPts} fill="#2563EB" fillOpacity={0.08} />

        {/* Actual remaining line */}
        <polyline
          points={actualPts}
          fill="none"
          stroke="#2563EB"
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* Last point dot */}
        <circle
          cx={xScale(n - 1)}
          cy={yScale(lastRemaining)}
          r={3}
          fill="#2563EB"
        />

        {/* Y-axis labels */}
        {yLabels.map(({ v, y }) => (
          <text
            key={v}
            x={PAD.left - 4}
            y={y + 4}
            textAnchor="end"
            fontSize={8}
            fill="currentColor"
            fillOpacity={0.5}
          >
            {v}
          </text>
        ))}

        {/* X-axis labels */}
        {xLabels.map(({ i, label }) => (
          <text
            key={i}
            x={xScale(i)}
            y={H - 4}
            textAnchor="middle"
            fontSize={8}
            fill="currentColor"
            fillOpacity={0.5}
          >
            {label}
          </text>
        ))}

        {/* Axes */}
        <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={PAD.top + plotH} stroke="currentColor" strokeOpacity={0.2} strokeWidth={1} />
        <line x1={PAD.left} y1={PAD.top + plotH} x2={PAD.left + plotW} y2={PAD.top + plotH} stroke="currentColor" strokeOpacity={0.2} strokeWidth={1} />
      </svg>

      {/* Summary below chart */}
      <div className="flex justify-between text-[10px] text-muted-foreground mt-1 px-1">
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-0.5 bg-primary rounded" />
          Resterend
        </span>
        <span>{lastPassed} / {total} klaar</span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-0.5 rounded" style={{ background: 'currentColor', opacity: 0.35 }} />
          Ideaal
        </span>
      </div>
    </div>
  )
}
