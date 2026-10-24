import React, { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import { api } from '../api/client'

const REASON = {
  over_production: 'Cooked more than needed', unpopular_dish: 'Unpopular dish', low_turnout: 'Lower turnout than expected',
  spoilage: 'Spoilage', other: 'Other', not_specified: 'No reason given',
}

function Stat({ label, value, note }) {
  return (
    <div className="card text-center">
      <p className="text-2xl text-forestdark font-display">{value}</p>
      <p className="text-xs text-ink/60 mt-1">{label}</p>
      {note && <p className="text-xs text-ink/40">{note}</p>}
    </div>
  )
}

export default function RealWastePanel({ from, to }) {
  const [data, setData] = useState(null)
  useEffect(() => { api.realWaste(from, to).then(setData).catch(() => setData(null)) }, [from, to])

  if (!data || data.meals_logged === 0) {
    return (
      <div className="card text-sm text-ink/60">
        No kitchen logs in this period yet. Once the kitchen logs cooked and served portions, real waste and rescue figures appear here.
      </div>
    )
  }

  // one bar per day: served + rescued + wasted adds up to what was cooked
  const byDay = {}
  data.daily.forEach((d) => {
    const row = (byDay[d.date] = byDay[d.date] || { date: d.date.slice(5), served: 0, rescued: 0, wasted: 0 })
    row.served += d.served; row.rescued += d.rescued; row.wasted += d.wasted
  })
  const chart = Object.values(byDay)
  const reasons = Object.entries(data.leftover_by_reason).sort((a, b) => b[1] - a[1])

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg text-forestdark">Real food waste</h2>
        <p className="text-sm text-ink/60">From the kitchen log: what was cooked, what was served, and what happened to the rest.</p>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Stat label="Cooked" value={data.cooked} note="portions" />
        <Stat label="Served" value={data.served} />
        <Stat label="Left over" value={data.leftover} />
        <Stat label="Rescued" value={data.rescued_total} note={`${data.rescued_by_students} students, ${data.rescued_by_ngos} NGOs`} />
        <Stat label="Wasted" value={data.wasted} note={`about Rs ${Math.round(data.waste_cost_inr)}`} />
      </div>
      <div className="grid md:grid-cols-3 gap-6">
        <div className="card md:col-span-2">
          <h3 className="font-medium text-forestdark mb-3">Where the cooked food went, by day</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E4DCC9" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="served" stackId="a" fill="#2F5D50" name="Served" />
              <Bar dataKey="rescued" stackId="a" fill="#7FA98A" name="Rescued" />
              <Bar dataKey="wasted" stackId="a" fill="#C97A3B" name="Wasted" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <h3 className="font-medium text-forestdark mb-3">Why food was left over</h3>
          {reasons.length === 0 ? <p className="text-sm text-ink/50">No leftovers in this period.</p> : (
            <ul className="text-sm space-y-1.5">
              {reasons.map(([k, n]) => <li key={k} className="flex justify-between"><span>{REASON[k] || k}</span><span className="font-medium">{n}</span></li>)}
            </ul>
          )}
          {data.rescue_rate !== null && <p className="text-xs text-ink/50 mt-4">{Math.round(data.rescue_rate * 100)}% of leftovers were rescued. {data.over_production_portions} portions were cooked above the recommendation.</p>}
        </div>
      </div>
    </div>
  )
}
