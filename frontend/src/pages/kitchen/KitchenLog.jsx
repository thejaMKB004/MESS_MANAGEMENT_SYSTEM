import React, { useEffect, useState, useCallback } from 'react'
import { api } from '../../api/client'
import { todayISO } from '../../utils/date'

const MEALS = ['breakfast', 'lunch', 'dinner']
const REASONS = [
  { value: '', label: 'No leftover / not applicable' },
  { value: 'over_production', label: 'Cooked more than needed' },
  { value: 'unpopular_dish', label: 'Dish was unpopular' },
  { value: 'low_turnout', label: 'Fewer people came than expected' },
  { value: 'spoilage', label: 'Spoilage' },
  { value: 'other', label: 'Other' },
]

function Row({ label, value }) {
  return <div className="flex justify-between text-sm"><dt className="text-ink/60">{label}</dt><dd className="font-medium">{value}</dd></div>
}

export default function KitchenLog() {
  const [date, setDate] = useState(todayISO())
  const [meal, setMeal] = useState('lunch')
  const [sheet, setSheet] = useState(null)
  const [log, setLog] = useState(null)
  const [form, setForm] = useState({ cooked: '', served: '', reason: '', notes: '' })
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [rescue, setRescue] = useState({ dish: '', portions: '', minutesAgo: 0, heldSafely: false })

  const load = useCallback(async () => {
    setError('')
    const [s, logs] = await Promise.all([api.cookingSheet(date, meal), api.kitchenLogs(date, date)])
    const existing = logs.find((l) => l.meal_type === meal) || null
    setSheet(s)
    setLog(existing)
    setForm({
      cooked: existing ? String(existing.cooked_portions) : '',
      served: existing ? String(existing.served_portions) : '',
      reason: existing?.waste_reason || '',
      notes: existing?.notes || '',
    })
    setRescue((r) => ({
      ...r,
      dish: s.dishes.join(', '),
      portions: existing ? String(Math.max(existing.leftover_portions - existing.listed_portions, 0)) : '',
      heldSafely: false,
    }))
  }, [date, meal])

  useEffect(() => { load().catch((e) => setError(e.message)) }, [load])

  const save = async (e) => {
    e.preventDefault()
    setError(''); setMsg('')
    try {
      const saved = await api.saveKitchenLog({
        date, meal_type: meal, cooked_portions: Number(form.cooked), served_portions: Number(form.served),
        waste_reason: form.reason || null, notes: form.notes || null,
      })
      setMsg(saved.leftover_portions > 0
        ? `Saved. ${saved.leftover_portions} portions left over. You can offer them for rescue below.`
        : 'Saved. Nothing left over.')
      await load()
    } catch (err) { setError(err.message) }
  }

  const createListing = async (e) => {
    e.preventDefault()
    setError(''); setMsg('')
    try {
      await api.createSurplus({
        date, meal_type: meal, dish_description: rescue.dish, portions: Number(rescue.portions),
        held_safely: rescue.heldSafely, cooked_minutes_ago: Number(rescue.minutesAgo) || 0,
      })
      setMsg('Listed. Students have been notified and can claim now. Manage it on the Rescue & donations page.')
      await load()
    } catch (err) { setError(err.message) }
  }

  const unlisted = log ? Math.max(log.leftover_portions - log.listed_portions, 0) : 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl text-forestdark">Kitchen log</h1>
        <div className="flex gap-2">
          <input type="date" className="input w-auto" value={date} max={todayISO()} onChange={(e) => setDate(e.target.value)} />
          <select className="input w-auto capitalize" value={meal} onChange={(e) => setMeal(e.target.value)}>
            {MEALS.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
      </div>

      {error && <p className="text-sm text-clay">{error}</p>}
      {msg && <p className="text-sm text-forest">{msg}</p>}

      <div className="grid md:grid-cols-2 gap-6">
        {sheet && (
          <div className="card">
            <h2 className="text-lg text-forestdark mb-1">Cooking sheet</h2>
            <p className="text-xs text-ink/50 mb-4">
              {sheet.dishes.length ? sheet.dishes.join(', ') : 'No menu published'}.{' '}
              {sheet.deadline_passed ? 'Confirmations are closed.' : 'Confirmations are still open, so this can change.'}
            </p>
            <p className="font-display text-4xl text-forestdark">{sheet.recommended_portions}</p>
            <p className="text-sm text-ink/60 mb-4">portions recommended</p>
            <dl className="space-y-1.5">
              <Row label="Confirmed will eat" value={`${sheet.confirmed_will_eat} students (${sheet.confirmed_portion_units} portion units)`} />
              <Row label="Guest meals" value={sheet.guests} />
              <Row label={`Didn't answer (${sheet.not_responded})`} value={`~${sheet.expected_walkins} expected`} />
              <Row label="Safety buffer" value={`${sheet.buffer_pct}%`} />
              <Row label="Skipped" value={sheet.skipped} />
            </dl>
            {(Object.keys(sheet.diet_counts).length > 0 || Object.keys(sheet.allergy_counts).length > 0) && (
              <div className="mt-4 pt-4 border-t border-sandline text-sm space-y-1">
                {Object.keys(sheet.diet_counts).length > 0 && <p><span className="text-ink/60">Diets: </span>{Object.entries(sheet.diet_counts).map(([k, n]) => `${n} ${k.replace(/_/g, ' ')}`).join(', ')}</p>}
                {Object.keys(sheet.allergy_counts).length > 0 && <p><span className="text-ink/60">Allergies to watch: </span>{Object.entries(sheet.allergy_counts).map(([k, n]) => `${n} ${k.replace(/_/g, ' ')}`).join(', ')}</p>}
              </div>
            )}
          </div>
        )}

        <form onSubmit={save} className="card space-y-4">
          <h2 className="text-lg text-forestdark">What happened at service</h2>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Portions cooked</label>
              <input className="input" type="number" min="0" required value={form.cooked} onChange={(e) => setForm({ ...form, cooked: e.target.value })} />
            </div>
            <div>
              <label className="label">Portions served</label>
              <input className="input" type="number" min="0" required value={form.served} onChange={(e) => setForm({ ...form, served: e.target.value })} />
            </div>
          </div>
          {form.cooked !== '' && form.served !== '' && Number(form.cooked) >= Number(form.served) && (
            <p className="text-sm text-ink/70">Leftover: <span className="font-medium">{Number(form.cooked) - Number(form.served)}</span> portions</p>
          )}
          <div>
            <label className="label">Why was there leftover?</label>
            <select className="input" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })}>
              {REASONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Notes (optional)</label>
            <textarea className="input" rows="2" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
          <button className="btn-primary w-full">{log ? 'Update log' : 'Save log'}</button>
          {log && log.over_production_pct !== null && (
            <p className="text-xs text-ink/50">
              Recommended was {log.recommended_portions}, cooked {log.cooked_portions} ({log.over_production_pct > 0 ? '+' : ''}{log.over_production_pct}%).
            </p>
          )}
        </form>
      </div>

      {log && unlisted > 0 && (
        <form onSubmit={createListing} className="card space-y-4 max-w-2xl">
          <div>
            <h2 className="text-lg text-forestdark">Rescue the leftover</h2>
            <p className="text-sm text-ink/60">{unlisted} portions can be offered. Students get 30 minutes to claim; whatever is left goes to NGO partners.</p>
          </div>
          <div>
            <label className="label">What is it?</label>
            <input className="input" required value={rescue.dish} onChange={(e) => setRescue({ ...rescue, dish: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Portions to offer</label>
              <input className="input" type="number" min="1" max={unlisted} required value={rescue.portions} onChange={(e) => setRescue({ ...rescue, portions: e.target.value })} />
            </div>
            <div>
              <label className="label">Cooked how many minutes ago?</label>
              <input className="input" type="number" min="0" value={rescue.minutesAgo} onChange={(e) => setRescue({ ...rescue, minutesAgo: e.target.value })} />
            </div>
          </div>
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-1 accent-forest" checked={rescue.heldSafely} onChange={(e) => setRescue({ ...rescue, heldSafely: e.target.checked })} />
            <span>This food was kept hot (or properly chilled) the whole time and is safe to eat.</span>
          </label>
          <button className="btn-primary" disabled={!rescue.heldSafely}>Offer to students</button>
        </form>
      )}
    </div>
  )
}
