import React, { useEffect, useState } from 'react'
import { api } from '../../api/client'

function Stat({ label, value, suffix }) {
  return (
    <div className="card text-center">
      <p className="text-3xl text-forestdark font-display">{value}{suffix}</p>
      <p className="text-sm text-ink/60 mt-1">{label}</p>
    </div>
  )
}

export default function MyImpact() {
  const [impact, setImpact] = useState(null)

  useEffect(() => { api.myImpact().then(setImpact) }, [])

  if (!impact) return <p className="text-ink/60">Loading...</p>

  return (
    <div>
      <h1 className="text-2xl text-forestdark mb-2">My impact</h1>
      <p className="text-ink/60 mb-6">A running total of the difference your honest meal confirmations make.</p>
      <div className="grid md:grid-cols-3 gap-4">
        <Stat label="Meals skipped (food saved)" value={impact.meals_skipped} />
        <Stat label="Leftover meals you rescued" value={impact.meals_rescued} />
        <Stat label="Estimated cost saved" value={`₹${impact.estimated_food_cost_saved_inr}`} />
        <Stat label="Current confirmation streak" value={impact.current_streak_days} suffix=" days" />
        <Stat label="Estimated CO₂ saved" value={impact.estimated_co2_saved_kg} suffix=" kg" />
        <Stat label="Estimated water saved" value={impact.estimated_water_saved_litres} suffix=" L" />
        <Stat label="Total meals confirmed" value={impact.total_confirmations} />
      </div>
    </div>
  )
}
