import React, { useEffect, useState, useCallback } from 'react'
import { api } from '../../api/client'
import { todayISO, addDaysISO, weekdayLabel } from '../../utils/date'

const MEALS = ['breakfast', 'lunch', 'dinner']
const SKIP_REASONS = [
  { value: 'dont_like_menu', label: "Don't like today's menu" },
  { value: 'eating_out', label: 'Eating out / outside food' },
  { value: 'not_on_campus', label: 'Not on campus' },
  { value: 'not_hungry_health', label: 'Not hungry / health' },
  { value: 'other', label: 'Other' },
]
const PORTIONS = ['half', 'regular', 'large']

function MealCard({ date, mealType, menuByKey, myAttendance, onConfirm }) {
  const key = `${date}_${mealType}`
  const dishes = menuByKey[key]?.dishes || []
  const existing = myAttendance.find((a) => a.date === date && a.meal_type === mealType)

  const [status, setStatus] = useState(existing?.status || '')
  const [portion, setPortion] = useState(existing?.portion || 'regular')
  const [reason, setReason] = useState(existing?.reason || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setStatus(existing?.status || '')
    setPortion(existing?.portion || 'regular')
    setReason(existing?.reason || '')
  }, [existing?.status, existing?.portion, existing?.reason])

  const submit = async (newStatus) => {
    setError('')
    if (newStatus === 'skip' && !reason) {
      setError('Please choose a skip reason.')
      return
    }
    setSaving(true)
    try {
      await onConfirm({
        date,
        meal_type: mealType,
        status: newStatus,
        portion: newStatus === 'will_eat' ? portion : undefined,
        reason: newStatus === 'skip' ? reason : undefined,
      })
      setStatus(newStatus)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-2">
        <h3 className="capitalize text-lg text-forestdark">{mealType}</h3>
        {status && (
          <span className={`tag ${status === 'skip' ? '!bg-clay/10 !text-clay !border-clay/40' : ''}`}>
            {status === 'will_eat' ? 'Will eat' : 'Skipped'}
          </span>
        )}
      </div>
      <p className="text-sm text-ink/60 mb-3">
        {dishes.length ? dishes.join(', ') : 'Menu not published yet'}
      </p>

      <div className="flex gap-2 mb-3">
        <button
          onClick={() => submit('will_eat')}
          disabled={saving}
          className={`btn-primary flex-1 ${status === 'will_eat' ? '' : 'opacity-90'}`}
        >
          Will eat
        </button>
        <button
          onClick={() => submit('skip')}
          disabled={saving}
          className="btn-danger flex-1"
        >
          Skip
        </button>
      </div>

      {status !== 'skip' && (
        <div className="mb-2">
          <label className="label">Portion</label>
          <select className="input" value={portion} onChange={(e) => { setPortion(e.target.value); if (status === 'will_eat') submit('will_eat') }}>
            {PORTIONS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
      )}

      <div>
        <label className="label">If skipping — reason</label>
        <select
          className="input"
          value={reason}
          onChange={(e) => { setReason(e.target.value) }}
        >
          <option value="">Select a reason</option>
          {SKIP_REASONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
        </select>
      </div>

      {error && <p className="text-sm text-clay mt-2">{error}</p>}
    </div>
  )
}

export default function Today() {
  const [menuByKey, setMenuByKey] = useState({})
  const [myAttendance, setMyAttendance] = useState([])
  const [days] = useState([0, 1, 2].map((n) => addDaysISO(todayISO(), n)))
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    const from = days[0]
    const to = days[days.length - 1]
    const [menus, attendance] = await Promise.all([
      api.listMenus(from, to),
      api.myAttendance(from, to),
    ])
    const byKey = {}
    menus.forEach((m) => { byKey[`${m.date}_${m.meal_type}`] = m })
    setMenuByKey(byKey)
    setMyAttendance(attendance)
    setLoading(false)
  }, [days])

  useEffect(() => { load() }, [load])

  const handleConfirm = async (payload) => {
    await api.confirmAttendance(payload)
    setToast('Saved.')
    setTimeout(() => setToast(''), 1500)
    load()
  }

  if (loading) return <p className="text-ink/60">Loading...</p>

  return (
    <div className="space-y-8">
      {toast && <div className="fixed top-4 right-4 bg-forest text-white px-4 py-2 rounded-md shadow">{toast}</div>}
      {days.map((date) => (
        <section key={date}>
          <h2 className="text-lg mb-3 text-ink/80">{weekdayLabel(date)}</h2>
          <div className="grid md:grid-cols-3 gap-4">
            {MEALS.map((mealType) => (
              <MealCard
                key={mealType}
                date={date}
                mealType={mealType}
                menuByKey={menuByKey}
                myAttendance={myAttendance}
                onConfirm={handleConfirm}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
