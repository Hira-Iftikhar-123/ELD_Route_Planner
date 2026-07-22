import { useState } from 'react'
import type { DailyLog } from '../types'
import EldLogSheet from './EldLogSheet'

type Props = {
  logs: DailyLog[]
}

export default function DailyLogSheets({ logs }: Props) {
  const [active, setActive] = useState(0)
  const current = logs[Math.min(active, logs.length - 1)]

  if (!logs.length || !current) return null

  return (
    <div className="eld-logs">
      <div className="eld-tabs" role="tablist" aria-label="Daily log sheets">
        {logs.map((log, i) => (
          <button
            key={log.date}
            type="button"
            role="tab"
            aria-selected={i === active}
            className={i === active ? 'eld-tab eld-tab--active' : 'eld-tab'}
            onClick={() => setActive(i)}
          >
            Day {i + 1}
            <span>{log.date}</span>
          </button>
        ))}
      </div>
      <EldLogSheet log={current} />
    </div>
  )
}