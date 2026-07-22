import type { DailyLog, DutyStatus, LogSegment } from '../types'

type Props = {
  log: DailyLog
}

const STATUS_ROWS: DutyStatus[] = ['off_duty', 'sleeper', 'driving', 'on_duty']
const STATUS_LABELS: Record<DutyStatus, string> = {
  off_duty: '1. Off Duty',
  sleeper: '2. Sleeper Berth',
  driving: '3. Driving',
  on_duty: '4. On Duty (not driving)',
}

const LABEL_W = 148
const TOTAL_W = 56
const GRID_W = 720
const ROW_H = 32
const PAD_TOP = 22
const PAD_BOTTOM = 8
const HOUR_W = GRID_W / 24
const TZ = 'America/Chicago'

function localDate(iso: string): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(iso))
}

function fractionalHour(iso: string): number {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-GB', {
      timeZone: TZ,
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23',
    })
      .formatToParts(new Date(iso))
      .map((p) => [p.type, p.value]),
  )
  return Number(parts.hour) + Number(parts.minute) / 60
}

function segmentHours(seg: LogSegment, logDate: string): { start: number; end: number } {
  let start = fractionalHour(seg.start)
  let end = fractionalHour(seg.end)
  const startDay = localDate(seg.start)
  const endDay = localDate(seg.end)

  if (startDay < logDate) start = 0
  if (endDay > logDate) end = 24
  if (endDay === logDate && end === 0 && new Date(seg.end) > new Date(seg.start)) end = 24
  if (end < start) end = 24
  return {
    start: Math.max(0, Math.min(24, start)),
    end: Math.max(0, Math.min(24, end)),
  }
}

function buildDutyPath(segments: LogSegment[], logDate: string): string {
  const points: Array<{ x: number; y: number }> = []

  for (const seg of segments) {
    const { start, end } = segmentHours(seg, logDate)
    if (end - start < 1 / 120) continue
    const row = STATUS_ROWS.indexOf(seg.status)
    if (row < 0) continue
    const y = PAD_TOP + row * ROW_H + ROW_H / 2
    const x1 = LABEL_W + start * HOUR_W
    const x2 = LABEL_W + end * HOUR_W

    if (!points.length) {
      points.push({ x: x1, y })
    } else {
      const prev = points[points.length - 1]
      if (Math.abs(prev.y - y) > 0.5) {
        points.push({ x: x1, y: prev.y })
        points.push({ x: x1, y })
      } else if (Math.abs(prev.x - x1) > 0.5) {
        points.push({ x: x1, y })
      }
    }
    points.push({ x: x2, y })
  }

  if (points.length < 2) return ''
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(' ')
}

export default function EldLogSheet({ log }: Props) {
  const [y, m, d] = log.date.split('-')
  const gridH = ROW_H * 4
  const svgH = PAD_TOP + gridH + PAD_BOTTOM
  const svgW = LABEL_W + GRID_W + TOTAL_W
  const path = buildDutyPath(log.segments, log.date)

  return (
    <article className="eld-sheet">
      <header className="eld-sheet-header">
        <div className="eld-sheet-title-row">
          <h3>Drivers Daily Log (24 hours)</h3>
          <div className="eld-date">
            <span>
              {m}/{d}/{y}
            </span>
            <small>Home terminal time (CT)</small>
          </div>
        </div>
        <div className="eld-meta-grid">
          <div className="eld-meta-block">
            <label>From</label>
            <p>{log.from_location}</p>
          </div>
          <div className="eld-meta-block">
            <label>To</label>
            <p>{log.to_location}</p>
          </div>
          <div className="eld-meta-stat">
            <label>Total Miles Driving Today</label>
            <strong>{log.total_miles}</strong>
          </div>
          <div className="eld-meta-stat">
            <label>Total Mileage Today</label>
            <strong>{log.total_miles}</strong>
          </div>
        </div>
      </header>

      <div className="eld-grid-wrap">
        <svg
          className="eld-grid-svg"
          viewBox={`0 0 ${svgW} ${svgH}`}
          role="img"
          aria-label={`Duty status grid for ${log.date}`}
        >
          {STATUS_ROWS.map((status, row) => {
            const yPos = PAD_TOP + row * ROW_H
            return (
              <g key={status}>
                <rect
                  x={0}
                  y={yPos}
                  width={svgW}
                  height={ROW_H}
                  fill={row % 2 === 0 ? '#f8fafc' : '#ffffff'}
                />
                <text x={8} y={yPos + ROW_H / 2 + 4} className="eld-row-label">
                  {STATUS_LABELS[status]}
                </text>
                <text
                  x={LABEL_W + GRID_W + TOTAL_W / 2}
                  y={yPos + ROW_H / 2 + 4}
                  textAnchor="middle"
                  className="eld-total-cell"
                >
                  {log.totals[status].toFixed(2)}
                </text>
              </g>
            )
          })}

          <rect
            x={LABEL_W}
            y={PAD_TOP}
            width={GRID_W}
            height={gridH}
            fill="none"
            stroke="#94a3b8"
            strokeWidth={1.2}
          />

          {Array.from({ length: 25 }, (_, h) => {
            const x = LABEL_W + h * HOUR_W
            return (
              <g key={h}>
                <line
                  x1={x}
                  y1={PAD_TOP}
                  x2={x}
                  y2={PAD_TOP + gridH}
                  stroke={h === 12 ? '#64748b' : '#cbd5e1'}
                  strokeWidth={h === 0 || h === 12 || h === 24 ? 1.2 : 0.7}
                />
                {h < 24 && (
                  <text
                    x={x + HOUR_W / 2}
                    y={14}
                    textAnchor="middle"
                    className="eld-hour-label"
                  >
                    {h === 0 ? 'Mid' : h === 12 ? 'Noon' : String(h % 12 || 12)}
                  </text>
                )}
              </g>
            )
          })}

          {[1, 2, 3].map((row) => (
            <line
              key={`h-${row}`}
              x1={LABEL_W}
              y1={PAD_TOP + row * ROW_H}
              x2={LABEL_W + GRID_W}
              y2={PAD_TOP + row * ROW_H}
              stroke="#94a3b8"
              strokeWidth={1}
            />
          ))}

          <text
            x={LABEL_W + GRID_W + TOTAL_W / 2}
            y={14}
            textAnchor="middle"
            className="eld-hour-label"
          >
            Total
          </text>

          {path && (
            <path
              d={path}
              fill="none"
              stroke="#0f4c81"
              strokeWidth={2.4}
              strokeLinejoin="miter"
              strokeLinecap="square"
            />
          )}
        </svg>
      </div>

      <div className="eld-bottom">
        <div className="eld-remarks">
          <h4>Remarks</h4>
          {log.remarks.length === 0 ? (
            <p className="eld-muted">No duty-status remarks for this day.</p>
          ) : (
            <ul>
              {log.remarks.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
        </div>
        <div className="eld-recap">
          <h4>70 Hour / 8 Day Recap</h4>
          <div className="eld-recap-grid">
            <div>
              <span>A. On duty last 8 days (incl. today)</span>
              <strong>{log.recap.total_hours_on_duty_last_8_days.toFixed(2)}</strong>
            </div>
            <div>
              <span>B. Hours available tomorrow</span>
              <strong>{log.recap.hours_available_tomorrow.toFixed(2)}</strong>
            </div>
            <div>
              <span>On duty today (lines 3 & 4)</span>
              <strong>{log.recap.on_duty_today.toFixed(2)}</strong>
            </div>
            <div>
              <span>Cycle used (end of day)</span>
              <strong>{log.recap.cycle_used_end_of_day.toFixed(2)}</strong>
            </div>
          </div>
        </div>
      </div>
    </article>
  )
}