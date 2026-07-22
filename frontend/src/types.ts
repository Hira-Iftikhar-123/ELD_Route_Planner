export type TripFormValues = {
  currentLocation: string
  pickupLocation: string
  dropoffLocation: string
  cycleUsedHours: number
}

export type DutyStatus = 'off_duty' | 'sleeper' | 'driving' | 'on_duty'

export type LogSegment = {
  status: DutyStatus
  start: string
  end: string
  hours: number
  location: string
  remark: string
  miles: number
}

export type DailyLog = {
  date: string
  from_location: string
  to_location: string
  total_miles: number
  totals: {
    off_duty: number
    sleeper: number
    driving: number
    on_duty: number
  }
  remarks: string[]
  recap: {
    on_duty_today: number
    total_hours_on_duty_last_8_days: number
    hours_available_tomorrow: number
    cycle_used_end_of_day: number
  }
  segments: LogSegment[]
}

export type TripPlanResponse = {
  summary: {
    total_miles: number
    total_drive_hours: number
    total_on_duty_hours: number
    days: number
    cycle_used_start: number
    cycle_used_end: number
  }
  stops: Array<{
    type: string
    label: string
    lat: number
    lon: number
    arrival: string
    duration_hours: number
    remark: string
  }>
  route: {
    distance_miles: number
    geometry: [number, number][]
    waypoints: Array<{ type: string; label: string; lat: number; lon: number }>
  }
  daily_logs: DailyLog[]
  locations: {
    current: { label: string; lat: number; lon: number }
    pickup: { label: string; lat: number; lon: number }
    dropoff: { label: string; lat: number; lon: number }
  }
}