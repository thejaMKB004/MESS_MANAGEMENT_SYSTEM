import React, { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { todayISO } from '../../utils/date'

const MEALS = ['breakfast', 'lunch', 'dinner']

export default function Dashboard() {
  const [date, setDate] = useState(todayISO())
  const [data, setData] = useState({})
  const [anomalies, setAnomalies] = useState([])
  const [checkinId, setCheckinId] = useState('')
  const [checkinStatus, setCheckinStatus] = useState('')

  const load = async () => {
    const results = {}
    for (const meal of MEALS) {
      results[meal] = await api.todayAttendance(meal, date)
    }
    setData(results)
    const anomalyRes = await api.anomalies(date)
    setAnomalies(anomalyRes.anomalies)
  }

  useEffect(() => { load() }, [date])

  const doCheckin = async (e) => {
    e.preventDefault()
    try {
      await api.checkin(Number(checkinId))
      setCheckinStatus('Checked in.')
      setCheckinId('')
      load()
    } catch (e) {
      setCheckinStatus(e.message)
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl text-forestdark">Today's dashboard</h1>
        <input type="date" className="input w-auto" value={date} onChange={(e) => setDate(e.target.value)} />
      </div>

      {anomalies.length > 0 && (
        <div className="card !border-clay/50 bg-clay/5">
          <h3 className="text-clay font-medium mb-2">⚠ Anomalies detected</h3>
          {anomalies.map((a, i) => (
            <p key={i} className="text-sm text-ink/70">
              <span className="capitalize font-medium">{a.meal_type}</span>: {a.alert.replace(/_/g, ' ')} —
              {' '}today's skip rate {Math.round(a.today_skip_rate * 100)}% vs usual {Math.round(a.avg_skip_rate * 100)}%
            </p>
          ))}
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-4">
        {MEALS.map((meal) => {
          const d = data[meal]
          if (!d) return null
          return (
            <div key={meal} className="card">
              <h3 className="capitalize text-lg text-forestdark mb-3">{meal}</h3>
              <dl className="text-sm space-y-1.5">
                <div className="flex justify-between"><dt className="text-ink/60">Predicted total</dt><dd className="font-medium">{d.predicted_total}</dd></div>
                <div className="flex justify-between"><dt className="text-ink/60">Confirmed will-eat</dt><dd>{d.confirmed_will_eat}</dd></div>
                <div className="flex justify-between"><dt className="text-ink/60">Guest bookings</dt><dd>{d.guest_bookings}</dd></div>
                <div className="flex justify-between"><dt className="text-ink/60">Checked in (actual)</dt><dd>{d.checked_in}</dd></div>
                <div className="flex justify-between"><dt className="text-ink/60">Skipped</dt><dd>{d.skipped}</dd></div>
              </dl>
              {Object.keys(d.skip_reasons).length > 0 && (
                <div className="mt-3 pt-3 border-t border-sandline">
                  <p className="text-xs text-ink/50 mb-1">Skip reasons</p>
                  {Object.entries(d.skip_reasons).map(([r, n]) => (
                    <p key={r} className="text-xs text-ink/60">{r.replace(/_/g, ' ')}: {n}</p>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="card max-w-sm">
        <h3 className="font-medium text-forestdark mb-2">Meal counter check-in</h3>
        <p className="text-xs text-ink/50 mb-3">Simulates a QR scan at the serving counter (enter an attendance record id).</p>
        <form onSubmit={doCheckin} className="flex gap-2">
          <input className="input" placeholder="Attendance ID" value={checkinId} onChange={(e) => setCheckinId(e.target.value)} />
          <button className="btn-primary">Check in</button>
        </form>
        {checkinStatus && <p className="text-sm text-ink/60 mt-2">{checkinStatus}</p>}
      </div>
    </div>
  )
}
