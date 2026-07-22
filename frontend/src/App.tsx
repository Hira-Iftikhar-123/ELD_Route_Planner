import { useState } from 'react'
import TripForm from './components/TripForm'
import RouteMap from './components/RouteMap'
import StopsList, { scheduledStops } from './components/StopsList'
import DailyLogSheets from './components/DailyLogSheets'
import { apiUrl } from './lib/api'
import type { TripFormValues, TripPlanResponse } from './types'

function hoursLabel(value: number) {
  return `${value.toFixed(2)}h`
}

export default function App() {
  const [status, setStatus] = useState('Enter trip details to plan a legal HOS route.')
  const [loading, setLoading] = useState(false)
  const [plan, setPlan] = useState<TripPlanResponse | null>(null)

  async function handleSubmit(values: TripFormValues) {
    setLoading(true)
    setStatus('Your trip is being planned, please wait…')
    setPlan(null)
    try {
      // Wake free-tier API (cold start can look like a CORS failure)
      try {
        await fetch(apiUrl('/api/health/'), { method: 'GET' })
      } catch {
        setStatus('Waking up the API, please wait…')
        await new Promise((r) => setTimeout(r, 2500))
      }

      const res = await fetchPlan(values)
      const data = await res.json()
      if (!res.ok) {
        throw new Error(
          typeof data.detail === 'string' ? data.detail : `API error ${res.status}`,
        )
      }
      const result = data as TripPlanResponse
      setPlan(result)
      setStatus(
        `Planned ${result.summary.total_miles} mi across ${result.summary.days} day(s).`,
      )
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Trip planning failed.'
      setStatus(
        /Failed to fetch|NetworkError|CORS/i.test(msg)
          ? 'API is waking up or unreachable. Wait ~30s and try Plan trip again.'
          : msg,
      )
    } finally {
      setLoading(false)
    }
  }

  async function fetchPlan(values: TripFormValues, attempt = 1): Promise<Response> {
    try {
      return await fetch(apiUrl('/api/plan-trip/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_location: values.currentLocation,
          pickup_location: values.pickupLocation,
          dropoff_location: values.dropoffLocation,
          cycle_used_hours: values.cycleUsedHours,
        }),
      })
    } catch (err) {
      if (attempt >= 2) throw err
      setStatus('Retrying after API wake-up…')
      await new Promise((r) => setTimeout(r, 4000))
      return fetchPlan(values, attempt + 1)
    }
  }

  return (
    <div className="app">
      <header className="page-header">
        <div>
          <p className="brand">ELD Route Planner</p>
          <h1>Plan smarter. Drive compliant</h1>
          <p className="lede">
          Enter your trip details to generate a compliant route, stop schedule, and daily ELD logs.
          </p>
        </div>
      </header>

      <main className="card">
        <section className="card-section">
          <h2 className="section-title">Trip details</h2>
          <TripForm onSubmit={handleSubmit} loading={loading} />
          <p className="status" role="status">
            {status}
          </p>
        </section>

        {plan && (
          <>
            <section className="card-section result-section">
              <h2 className="section-title">Plan summary</h2>
              <div className="metrics">
                <article className="metric">
                  <span className="metric-label">Miles</span>
                  <strong className="metric-value">
                    {plan.summary.total_miles.toFixed(1)}
                  </strong>
                </article>
                <article className="metric">
                  <span className="metric-label">Drive hours</span>
                  <strong className="metric-value">
                    {plan.summary.total_drive_hours.toFixed(2)}
                  </strong>
                </article>
                <article className="metric">
                  <span className="metric-label">On-duty hours</span>
                  <strong className="metric-value">
                    {plan.summary.total_on_duty_hours.toFixed(2)}
                  </strong>
                </article>
                <article className="metric">
                  <span className="metric-label">Log days</span>
                  <strong className="metric-value">{plan.summary.days}</strong>
                </article>
                <article className="metric">
                  <span className="metric-label">Cycle</span>
                  <strong className="metric-value metric-value--sm">
                    {hoursLabel(plan.summary.cycle_used_start)} →{' '}
                    {hoursLabel(plan.summary.cycle_used_end)}
                  </strong>
                </article>
                <article className="metric">
                  <span className="metric-label">Stops</span>
                  <strong className="metric-value">
                    {scheduledStops(plan.stops).length}
                  </strong>
                </article>
              </div>
            </section>

            <section className="card-section map-section">
              <h2 className="section-title">Route & Stops</h2>
              <div className="map-layout">
                <RouteMap key={`${plan.summary.total_miles}-${plan.summary.days}`} plan={plan} />
                <div className="stops-panel">
                  <h3 className="subsection-title stops-panel-title">Stop schedule</h3>
                  <StopsList stops={plan.stops} />
                </div>
              </div>
            </section>

            <section className="card-section result-section">
              <h2 className="section-title">Daily log sheets</h2>
              <DailyLogSheets
                key={`${plan.daily_logs[0]?.date}-${plan.daily_logs.length}`}
                logs={plan.daily_logs}
              />
            </section>
          </>
        )}
      </main>
    </div>
  )
}