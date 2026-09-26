import React, { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { todayISO, addDaysISO, weekdayLabel } from '../../utils/date'

const MEALS = ['breakfast', 'lunch', 'dinner']

export default function MenuPlanner() {
  const [menus, setMenus] = useState([])
  const [date, setDate] = useState(todayISO())
  const [mealType, setMealType] = useState('lunch')
  const [dishesText, setDishesText] = useState('')
  const [status, setStatus] = useState('')

  const load = async () => {
    const from = addDaysISO(todayISO(), -2)
    const to = addDaysISO(todayISO(), 7)
    setMenus(await api.listMenus(from, to))
  }
  useEffect(() => { load() }, [])

  const existing = menus.find((m) => m.date === date && m.meal_type === mealType)

  useEffect(() => {
    setDishesText(existing ? existing.dishes.join(', ') : '')
  }, [date, mealType, existing?.id])

  const submit = async (e) => {
    e.preventDefault()
    const dishes = dishesText.split(',').map((d) => d.trim()).filter(Boolean)
    try {
      if (existing) {
        await api.updateMenu(existing.id, { dishes })
      } else {
        await api.createMenu({ date, meal_type: mealType, dishes })
      }
      setStatus('Menu saved.')
      load()
    } catch (e) {
      setStatus(e.message)
    }
  }

  return (
    <div className="grid md:grid-cols-2 gap-8">
      <div>
        <h1 className="text-2xl text-forestdark mb-6">Menu planner</h1>
        <form onSubmit={submit} className="card space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Date</label>
              <input type="date" className="input" value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <div>
              <label className="label">Meal</label>
              <select className="input" value={mealType} onChange={(e) => setMealType(e.target.value)}>
                {MEALS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="label">Dishes (comma-separated)</label>
            <textarea className="input" rows="3" value={dishesText} onChange={(e) => setDishesText(e.target.value)} placeholder="e.g. Rice & Dal, Curd Rice" />
          </div>
          {status && <p className="text-sm text-forest">{status}</p>}
          <button className="btn-primary w-full">{existing ? 'Update menu' : 'Create menu'}</button>
        </form>
      </div>
      <div>
        <h2 className="text-lg text-ink/80 mb-3">Upcoming menus</h2>
        <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
          {menus.map((m) => (
            <div key={m.id} className="card !p-3 text-sm flex justify-between items-start">
              <div>
                <p className="font-medium">{weekdayLabel(m.date)} · <span className="capitalize">{m.meal_type}</span></p>
                <p className="text-ink/60">{m.dishes.join(', ')}</p>
              </div>
              <button className="text-xs text-forest hover:underline" onClick={() => { setDate(m.date); setMealType(m.meal_type) }}>Edit</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
