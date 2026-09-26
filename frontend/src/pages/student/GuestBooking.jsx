import React, { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { todayISO, weekdayLabel } from '../../utils/date'

export default function GuestBooking() {
  const [date, setDate] = useState(todayISO())
  const [mealType, setMealType] = useState('lunch')
  const [count, setCount] = useState(1)
  const [bookings, setBookings] = useState([])
  const [status, setStatus] = useState('')

  const load = () => api.myGuestBookings().then(setBookings)
  useEffect(() => { load() }, [])

  const submit = async (e) => {
    e.preventDefault()
    try {
      await api.createGuestBooking({ date, meal_type: mealType, count: Number(count) })
      setStatus('Guest meal booked.')
      load()
    } catch (e) {
      setStatus(e.message)
    }
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div>
        <h1 className="text-2xl text-forestdark mb-6">Book a guest meal</h1>
        <form onSubmit={submit} className="card space-y-4">
          <div>
            <label className="label">Date</label>
            <input type="date" className="input" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div>
            <label className="label">Meal</label>
            <select className="input" value={mealType} onChange={(e) => setMealType(e.target.value)}>
              <option value="breakfast">Breakfast</option>
              <option value="lunch">Lunch</option>
              <option value="dinner">Dinner</option>
            </select>
          </div>
          <div>
            <label className="label">Number of guests</label>
            <input type="number" min="1" className="input" value={count} onChange={(e) => setCount(e.target.value)} />
          </div>
          {status && <p className="text-sm text-forest">{status}</p>}
          <button className="btn-primary w-full">Book</button>
        </form>
      </div>
      <div>
        <h2 className="text-lg text-ink/80 mb-3">Your bookings</h2>
        <div className="space-y-2">
          {bookings.length === 0 && <p className="text-sm text-ink/50">No guest meals booked yet.</p>}
          {bookings.map((b) => (
            <div key={b.id} className="card !p-3 text-sm flex justify-between">
              <span>{weekdayLabel(b.date)} · <span className="capitalize">{b.meal_type}</span></span>
              <span className="font-medium">{b.count} guest{b.count > 1 ? 's' : ''}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
