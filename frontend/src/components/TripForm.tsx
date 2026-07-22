import { useState, type FormEvent } from 'react'
import type { TripFormValues } from '../types'

type Props = {
  onSubmit: (values: TripFormValues) => void | Promise<void>
  loading?: boolean
}

function IconPin() {
  return (
    <svg className="field-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 2C8.1 2 5 5.1 5 9c0 5.2 7 13 7 13s7-7.8 7-13c0-3.9-3.1-7-7-7zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5z"
      />
    </svg>
  )
}

function IconPickup() {
  return (
    <svg className="field-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 2 4 5v6.1c0 5 3.4 9.6 8 10.9 4.6-1.3 8-5.9 8-10.9V5l-8-3zm-1 14-3.5-3.5 1.4-1.4L11 13.2l4.1-4.1 1.4 1.4L11 16z"
      />
    </svg>
  )
}

function IconDropoff() {
  return (
    <svg className="field-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 2C8.1 2 5 5.1 5 9c0 5.2 7 13 7 13s7-7.8 7-13c0-3.9-3.1-7-7-7zm0 4a3 3 0 1 1 0 6 3 3 0 0 1 0-6z"
      />
      <path fill="currentColor" d="M11 10h2v8h-2z" opacity=".35" />
    </svg>
  )
}

function IconClock() {
  return (
    <svg className="field-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 2a10 10 0 1 0 .001 20.001A10 10 0 0 0 12 2zm1 10.6 3.2 1.9-.8 1.3L11 13.2V7h2v5.6z"
      />
    </svg>
  )
}

export default function TripForm({ onSubmit, loading }: Props) {
  const [currentLocation, setCurrentLocation] = useState('')
  const [pickupLocation, setPickupLocation] = useState('')
  const [dropoffLocation, setDropoffLocation] = useState('')
  const [cycleUsedHours, setCycleUsedHours] = useState(0)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    void onSubmit({
      currentLocation: currentLocation.trim(),
      pickupLocation: pickupLocation.trim(),
      dropoffLocation: dropoffLocation.trim(),
      cycleUsedHours: Number(cycleUsedHours) || 0,
    })
  }

  return (
    <form className="trip-form" onSubmit={handleSubmit}>
      <div className="form-grid">
        <label className="field">
          <span className="field-label">
            <IconPin />
            Current location
          </span>
          <input
            required
            value={currentLocation}
            onChange={(e) => setCurrentLocation(e.target.value)}
            placeholder="e.g. Chicago, IL"
          />
        </label>
        <label className="field">
          <span className="field-label">
            <IconPickup />
            Pickup location
          </span>
          <input
            required
            value={pickupLocation}
            onChange={(e) => setPickupLocation(e.target.value)}
            placeholder="e.g. Indianapolis, IN"
          />
        </label>
        <label className="field">
          <span className="field-label">
            <IconDropoff />
            Dropoff location
          </span>
          <input
            required
            value={dropoffLocation}
            onChange={(e) => setDropoffLocation(e.target.value)}
            placeholder="e.g. Atlanta, GA"
          />
        </label>
        <label className="field">
          <span className="field-label">
            <IconClock />
            Current cycle used (Hrs)
          </span>
          <input
            required
            type="number"
            min={0}
            max={70}
            step={0.25}
            value={cycleUsedHours}
            onChange={(e) => setCycleUsedHours(Number(e.target.value))}
          />
        </label>
      </div>
      <button className="btn-primary" type="submit" disabled={loading}>
        {loading ? 'Planning…' : 'Plan trip'}
      </button>
    </form>
  )
}