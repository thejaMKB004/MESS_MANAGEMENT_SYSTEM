import React, { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import { api } from '../../api/client'
import { addDaysISO, todayISO } from '../../utils/date'

export default function Analytics() {
  const [from, setFrom] = useState(addDaysISO(todayISO(), -13))
  const [to, setTo] = useState(todayISO())
  const [attendance, setAttendance] = useState(null)
  const [dishRatings, setDishRatings] = useState(null)
  const [report, setReport] = useState(null)

  const load = async () => {
    const [att, dishes, weekly] = await Promise.all([
      api.attendanceAnalytics(from, to),
      api.dishRatings(6),
      api.weeklyReport(from),
    ])
    setAttendance(att)
    setDishRatings(dishes)
    setReport(weekly)
  }
  useEffect(() => { load() }, [from, to])

  const mealChartData = attendance ? Object.entries(attendance.by_meal).map(([meal, v]) => ({ meal, ...v })) : []
  const hostelChartData = attendance ? Object.entries(attendance.by_hostel).map(([hostel, v]) => ({ hostel, ...v })) : []

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl text-forestdark">Analytics</h1>
        <div className="flex gap-2 items-center text-sm">
          <input type="date" className="input w-auto" value={from} onChange={(e) => setFrom(e.target.value)} />
          <span className="text-ink/50">to</span>
          <input type="date" className="input w-auto" value={to} onChange={(e) => setTo(e.target.value)} />
        </div>
      </div>

      {report && (
        <div className="grid md:grid-cols-4 gap-4">
          <div className="card text-center"><p className="text-2xl text-forestdark">{report.total_waste_meals}</p><p className="text-xs text-ink/60 mt-1">Meals wasted (window)</p></div>
          <div className="card text-center"><p className="text-2xl text-forestdark">₹{report.total_waste_cost_inr}</p><p className="text-xs text-ink/60 mt-1">Est. waste cost</p></div>
          <div className="card text-center"><p className="text-2xl text-forestdark">{report.complaints_received}</p><p className="text-xs text-ink/60 mt-1">Complaints received</p></div>
          <div className="card text-center"><p className="text-2xl text-forestdark">{report.complaints_resolved}</p><p className="text-xs text-ink/60 mt-1">Complaints resolved</p></div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="font-medium text-forestdark mb-3">Attendance by meal</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={mealChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E4DCC9" />
              <XAxis dataKey="meal" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="will_eat" fill="#2F5D50" name="Will eat" />
              <Bar dataKey="skip" fill="#C97A3B" name="Skip" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h3 className="font-medium text-forestdark mb-3">Attendance by hostel</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={hostelChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E4DCC9" />
              <XAxis dataKey="hostel" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="will_eat" fill="#2F5D50" name="Will eat" />
              <Bar dataKey="skip" fill="#C97A3B" name="Skip" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {dishRatings && (
        <div className="grid md:grid-cols-2 gap-6">
          <div className="card">
            <h3 className="font-medium text-forestdark mb-3">Top rated dishes</h3>
            <ul className="text-sm space-y-1.5">
              {dishRatings.top.map((d) => (
                <li key={d.dish_name} className="flex justify-between"><span>{d.dish_name}</span><span className="font-medium">{d.avg_rating} ★ ({d.count})</span></li>
              ))}
            </ul>
          </div>
          <div className="card">
            <h3 className="font-medium text-forestdark mb-3">Lowest rated dishes</h3>
            <ul className="text-sm space-y-1.5">
              {dishRatings.bottom.map((d) => (
                <li key={d.dish_name} className="flex justify-between"><span>{d.dish_name}</span><span className="font-medium text-clay">{d.avg_rating} ★ ({d.count})</span></li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
