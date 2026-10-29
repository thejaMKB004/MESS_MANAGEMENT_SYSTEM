import React, { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { todayISO, addDaysISO, weekdayLabel } from '../../utils/date'

const MEALS = ['breakfast', 'lunch', 'dinner']

export default function WeeklyMenu() {
  const [menus, setMenus] = useState([])
  const [nutrition, setNutrition] = useState({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const from = addDaysISO(todayISO(), -3)
    const to = addDaysISO(todayISO(), 6)
    api.listMenus(from, to).then((m) => { setMenus(m); setLoading(false) })
    api.mealNutrition(from, to).then((rows) => {
      const byKey = {}
      rows.forEach((r) => { byKey[`${r.date}_${r.meal_type}`] = r })
      setNutrition(byKey)
    }).catch(() => {})
  }, [])

  if (loading) return <p className="text-ink/60">Loading...</p>

  const byDate = {}
  menus.forEach((m) => {
    byDate[m.date] = byDate[m.date] || {}
    byDate[m.date][m.meal_type] = m.dishes
  })
  const dates = Object.keys(byDate).sort()

  return (
    <div>
      <h1 className="text-2xl text-forestdark mb-6">Weekly menu</h1>
      <div className="grid gap-3">
        {dates.map((date) => (
          <div key={date} className="card">
            <h3 className="text-ink/80 mb-2">{weekdayLabel(date)}</h3>
            <div className="grid md:grid-cols-3 gap-4 text-sm">
              {MEALS.map((meal) => (
                <div key={meal}>
                  <p className="font-medium capitalize text-forest">{meal}</p>
                  <p className="text-ink/70">{(byDate[date][meal] || []).join(', ') || '—'}</p>
                  {nutrition[`${date}_${meal}`]?.dishes.length > 0 && (
                    <p className="text-xs text-ink/50">About {Math.round(nutrition[`${date}_${meal}`].totals.kcal)} kcal</p>
                  )}
                  {nutrition[`${date}_${meal}`]?.warnings.length > 0 && (
                    <p className="text-xs text-clay">{nutrition[`${date}_${meal}`].warnings.join('; ')}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
