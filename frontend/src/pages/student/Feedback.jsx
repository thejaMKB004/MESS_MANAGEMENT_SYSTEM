import React, { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { todayISO } from '../../utils/date'

const TAG_OPTIONS = ['too salty', 'too spicy', 'bland', 'cold', 'undercooked', 'great taste', 'good portion']

export default function Feedback() {
  const [menus, setMenus] = useState([])
  const [date, setDate] = useState(todayISO())
  const [mealType, setMealType] = useState('lunch')
  const [dishName, setDishName] = useState('')
  const [rating, setRating] = useState(5)
  const [tags, setTags] = useState([])
  const [comment, setComment] = useState('')
  const [status, setStatus] = useState('')

  useEffect(() => {
    api.listMenus(date, date).then(setMenus).catch(() => setMenus([]))
  }, [date])

  const dishesForMeal = menus.find((m) => m.meal_type === mealType)?.dishes || []

  const toggleTag = (t) => {
    setTags((prev) => prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t])
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!dishName) { setStatus('Pick a dish first.'); return }
    try {
      await api.createFeedback({ date, meal_type: mealType, dish_name: dishName, rating, tags, comment: comment || undefined })
      setStatus('Thanks for the feedback!')
      setComment(''); setTags([])
    } catch (e) {
      setStatus(e.message)
    }
  }

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl text-forestdark mb-6">Dish feedback</h1>
      <form onSubmit={submit} className="card space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Date</label>
            <input type="date" className="input" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div>
            <label className="label">Meal</label>
            <select className="input" value={mealType} onChange={(e) => { setMealType(e.target.value); setDishName('') }}>
              <option value="breakfast">Breakfast</option>
              <option value="lunch">Lunch</option>
              <option value="dinner">Dinner</option>
            </select>
          </div>
        </div>
        <div>
          <label className="label">Dish</label>
          <select className="input" value={dishName} onChange={(e) => setDishName(e.target.value)}>
            <option value="">Select a dish</option>
            {dishesForMeal.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Rating: {rating} / 5</label>
          <input type="range" min="1" max="5" value={rating} onChange={(e) => setRating(Number(e.target.value))} className="w-full accent-forest" />
        </div>
        <div>
          <label className="label">Tags</label>
          <div className="flex flex-wrap gap-2">
            {TAG_OPTIONS.map((t) => (
              <button
                type="button"
                key={t}
                onClick={() => toggleTag(t)}
                className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                  tags.includes(t) ? 'bg-forest text-white border-forest' : 'border-sandline text-ink/60 hover:border-forest'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="label">Comment (optional)</label>
          <textarea className="input" rows="3" value={comment} onChange={(e) => setComment(e.target.value)} />
        </div>
        {status && <p className="text-sm text-forest">{status}</p>}
        <button className="btn-primary w-full">Submit feedback</button>
      </form>
    </div>
  )
}
