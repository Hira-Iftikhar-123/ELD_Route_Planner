import type { TripPlanResponse } from '../types'

type Props = {
  stops: TripPlanResponse['stops']
}

const LABELS: Record<string, string> = {
  arrival: 'Arrival',
  pickup: 'Pickup',
  dropoff: 'Dropoff',
  fuel: 'Fuel',
  break_30: 'Break',
  rest_10: '10 hr rest',
  restart_34: '34 hr reset',
}

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleString('en-US', {
      timeZone: 'America/Chicago',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function formatDuration(hours: number) {
  if (hours <= 0) return '0'
  if (hours < 1) return `${Math.round(hours * 60)}m`
  return `${hours.toFixed(2)}h`
}

export function scheduledStops(stops: TripPlanResponse['stops']) {
  return stops.filter((s) => s.type !== 'arrival' || s.duration_hours > 0)
}

export default function StopsList({ stops }: Props) {
  const visible = scheduledStops(stops)

  return (
    <div className="stops-table-wrap">
      <table className="stops-table">
        <thead>
          <tr>
            <th scope="col">Type</th>
            <th scope="col">Details</th>
            <th scope="col">Time</th>
            <th scope="col">Duration</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((stop, i) => (
            <tr key={`${stop.type}-${stop.arrival}-${i}`}>
              <td>
                <span className={`stop-badge stop-badge--${stop.type}`}>
                  {LABELS[stop.type] ?? stop.type}
                </span>
              </td>
              <td className="stop-details">{stop.remark || stop.label}</td>
              <td className="stop-time">{formatTime(stop.arrival)}</td>
              <td className="stop-duration">{formatDuration(stop.duration_hours)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}