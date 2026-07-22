import { useEffect, useMemo } from 'react'
import { MapContainer, Marker, Popup, Polyline, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import type { TripPlanResponse } from '../types'

type Props = {
  plan: TripPlanResponse
}

const TYPE_COLORS: Record<string, string> = {
  current: '#0f4c81',
  pickup: '#0f766e',
  dropoff: '#b45309',
  arrival: '#64748b',
  fuel: '#0369a1',
  break_30: '#7c3aed',
  rest_10: '#4338ca',
  restart_34: '#be123c',
}

function FitRoute({ points }: { points: [number, number][] }) {
  const map = useMap()
  useEffect(() => {
    if (points.length < 2) return
    map.fitBounds(L.latLngBounds(points), { padding: [36, 36], maxZoom: 10 })
    map.invalidateSize()
  }, [map, points])
  return null
}

const TYPE_LETTER: Record<string, string> = {
  current: 'C',
  pickup: 'P',
  dropoff: 'D',
  arrival: 'A',
  fuel: 'F',
  break_30: 'B',
  rest_10: 'R',
  restart_34: 'X',
}

function markerIcon(type: string) {
  const color = TYPE_COLORS[type] ?? '#334155'
  const short = TYPE_LETTER[type] ?? type.slice(0, 1).toUpperCase()
  return L.divIcon({
    className: 'map-marker',
    html: `<span style="background:${color}">${short}</span>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  })
}

export default function RouteMap({ plan }: Props) {
  const geometry = useMemo(
    () => plan.route.geometry.map(([lat, lon]) => [lat, lon] as [number, number]),
    [plan.route.geometry],
  )

  const markers = useMemo(() => {
    const items: Array<{
      key: string
      type: string
      label: string
      lat: number
      lon: number
      detail?: string
    }> = []

    for (const wp of plan.route.waypoints) {
      items.push({
        key: `wp-${wp.type}`,
        type: wp.type,
        label: wp.label,
        lat: wp.lat,
        lon: wp.lon,
        detail: wp.type.replace('_', ' '),
      })
    }

    plan.stops.forEach((stop, i) => {
      if (!stop.lat && !stop.lon) return
      if (Math.abs(stop.lat) < 0.01 && Math.abs(stop.lon) < 0.01) return
      if (stop.type === 'pickup' || stop.type === 'dropoff') return
      items.push({
        key: `stop-${i}`,
        type: stop.type,
        label: stop.label,
        lat: stop.lat,
        lon: stop.lon,
        detail: stop.remark,
      })
    })

    return items
  }, [plan])

  if (geometry.length < 2) {
    return <p className="map-empty">No route geometry available for this trip.</p>
  }

  return (
    <div className="map-shell">
      <MapContainer
        className="route-map"
        center={geometry[Math.floor(geometry.length / 2)]}
        zoom={6}
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Polyline positions={geometry} pathOptions={{ color: '#0f4c81', weight: 4, opacity: 0.85 }} />
        <FitRoute points={geometry} />
        {markers.map((m) => (
          <Marker
            key={m.key}
            position={[m.lat, m.lon]}
            icon={markerIcon(m.type)}
          >
            <Popup>
              <strong>{m.type.replaceAll('_', ' ')}</strong>
              <br />
              {m.label}
              {m.detail ? (
                <>
                  <br />
                  <span>{m.detail}</span>
                </>
              ) : null}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}