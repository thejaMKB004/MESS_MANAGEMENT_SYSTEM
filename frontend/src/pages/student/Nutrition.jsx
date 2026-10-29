import React, { useEffect, useState, useCallback } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend, ReferenceLine } from 'recharts'
import { api } from '../../api/client'
import { todayISO, addDaysISO, weekdayLabel } from '../../utils/date'

const PORTIONS = ['half', 'regular', 'large']
const r0 = (n) => Math.round(n || 0)

function Totals({ totals, goal }) {
  const share = goal?.kcal_target ? Math.min(totals.kcal / goal.kcal_target, 1) : null
  return (
    <div className="card">
      <p className="font-display text-4xl text-forestdark">{r0(totals.kcal)} <span className="text-lg text-ink/60">kcal</span></p>
      {goal?.kcal_target && (
        <>
          <p className="text-sm text-ink/60">of your {r0(goal.kcal_target)} kcal target</p>
          <div className="h-2 bg-sand rounded-full mt-2 overflow-hidden"><div className="h-full bg-leaf" style={{ width: `${share * 100}%` }} /></div>
        </>
      )}
      <dl className="grid grid-cols-3 gap-3 mt-4 text-sm">
        <div><dt className="text-ink/60">Protein</dt><dd className="font-medium">{r0(totals.protein_g)} g{goal?.protein_target_g ? ` of ${r0(goal.protein_target_g)}` : ''}</dd></div>
        <div><dt className="text-ink/60">Carbs</dt><dd className="font-medium">{r0(totals.carbs_g)} g</dd></div>
        <div><dt className="text-ink/60">Fat</dt><dd className="font-medium">{r0(totals.fat_g)} g</dd></div>
      </dl>
    </div>
  )
}

function MessMealRow({ meal, date, onLogged, setError }) {
  const [portion, setPortion] = useState(meal.confirmed_portion || 'regular')
  const [busy, setBusy] = useState(false)
  const factor = { half: 0.5, regular: 1, large: 1.5 }[portion]

  const log = async () => {
    setBusy(true); setError('')
    try { await api.addIntake({ date, meal_type: meal.meal_type, source: 'mess', portion }); onLogged() }
    catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="card !p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium capitalize">{meal.meal_type}</p>
          <p className="text-sm text-ink/60">{meal.dishes.map((d) => d.dish_name).concat(meal.missing_dishes).join(', ')}</p>
          {meal.dishes.length > 0 && <p className="text-xs text-ink/50 mt-1">About {r0(meal.totals.kcal * factor)} kcal for a {portion} portion</p>}
          {meal.warnings.length > 0 && <p className="text-xs text-clay mt-1">Check before eating: {meal.warnings.join('; ')}</p>}
          {meal.attendance === 'skip' && <p className="text-xs text-ink/50 mt-1">You marked this meal as skipped.</p>}
        </div>
        {meal.already_logged ? (
          <span className="text-sm text-forest whitespace-nowrap">Logged</span>
        ) : (
          <div className="flex gap-2 shrink-0">
            <select className="input !py-1 w-auto" value={portion} onChange={(e) => setPortion(e.target.value)} aria-label="Portion">
              {PORTIONS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
            <button className="btn-primary !py-1" disabled={busy || meal.dishes.length === 0} onClick={log}>I ate this</button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Nutrition() {
  const [date, setDate] = useState(todayISO())
  const [day, setDay] = useState(null)
  const [week, setWeek] = useState(null)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [other, setOther] = useState({ description: '', meal_type: 'snack', kcal: '', protein_g: '', carbs_g: '', fat_g: '' })
  const [goal, setGoal] = useState({ kcal_target: '', protein_target_g: '' })

  const load = useCallback(async () => {
    const [d, w] = await Promise.all([api.intakeDay(date), api.intakeSummary(7)])
    setDay(d); setWeek(w)
    setGoal({ kcal_target: d.goal.kcal_target ?? '', protein_target_g: d.goal.protein_target_g ?? '' })
  }, [date])

  useEffect(() => { load().catch((e) => setError(e.message)) }, [load])

  const addOther = async (e) => {
    e.preventDefault(); setError(''); setMsg('')
    const num = (v) => (v === '' ? undefined : Number(v))
    try {
      await api.addIntake({ date, source: 'other', meal_type: other.meal_type, description: other.description,
        kcal: num(other.kcal), protein_g: num(other.protein_g), carbs_g: num(other.carbs_g), fat_g: num(other.fat_g) })
      setOther({ description: '', meal_type: 'snack', kcal: '', protein_g: '', carbs_g: '', fat_g: '' })
      setMsg('Added.'); load()
    } catch (err) { setError(err.message) }
  }

  const remove = async (id) => {
    setError(''); setMsg('')
    try { await api.deleteIntake(id); load() } catch (err) { setError(err.message) }
  }

  const saveGoal = async (e) => {
    e.preventDefault(); setError(''); setMsg('')
    try {
      await api.setNutritionGoal({
        kcal_target: goal.kcal_target === '' ? null : Number(goal.kcal_target),
        protein_target_g: goal.protein_target_g === '' ? null : Number(goal.protein_target_g),
      })
      setMsg('Target saved.'); load()
    } catch (err) { setError(err.message.includes('greater than or equal') ? 'Targets must be at least 1200 kcal and 10 g protein.' : err.message) }
  }

  if (!day) return error ? <p className="text-sm text-clay">{error}</p> : <p className="text-ink/60">Loading...</p>

  const chart = week.days.map((d) => ({ day: weekdayLabel(d.date).split(',')[0], Mess: r0(d.mess_kcal), Other: r0(d.other_kcal) }))

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl text-forestdark mb-1">Food log</h1>
          <p className="text-sm text-ink/60">Log what you ate to see your calories and nutrients. Mess values are approximate, per portion.</p>
        </div>
        <div>
          <input type="date" className="input w-auto" aria-label="Day" value={date} max={todayISO()} min={addDaysISO(todayISO(), -30)} onChange={(e) => setDate(e.target.value)} />
        </div>
      </div>

      {error && <p className="text-sm text-clay">{error}</p>}
      {msg && <p className="text-sm text-forest">{msg}</p>}

      <div className="grid md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <h2 className="text-lg text-ink/80">{weekdayLabel(date)}</h2>
          <Totals totals={day.totals} goal={day.goal} />
          {day.entries.length === 0 ? (
            <p className="text-sm text-ink/50">Nothing logged for this day yet.</p>
          ) : (
            <div className="card !p-0">
              {day.entries.map((e) => (
                <div key={e.id} className="flex items-center justify-between gap-3 p-3 border-b border-sandline/60 last:border-0 text-sm">
                  <div>
                    <p className="font-medium"><span className="capitalize">{e.meal_type}</span>{e.portion ? ` (${e.portion})` : ''}</p>
                    <p className="text-ink/60">{e.description}</p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="font-medium">{r0(e.kcal)} kcal</span>
                    <button className="text-xs text-clay hover:underline" onClick={() => remove(e.id)}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-4">
          <h2 className="text-lg text-ink/80">Mess meals</h2>
          {day.mess_meals.length === 0 ? <p className="text-sm text-ink/50">No menu was published for this day.</p> :
            day.mess_meals.map((m) => <MessMealRow key={m.meal_type} meal={m} date={date} onLogged={() => { setMsg('Logged.'); load() }} setError={setError} />)}

          <form onSubmit={addOther} className="card space-y-3">
            <h3 className="font-medium text-forestdark">Something else</h3>
            <div className="grid grid-cols-3 gap-2">
              <input className="input col-span-2" placeholder="What did you eat?" required value={other.description} onChange={(e) => setOther({ ...other, description: e.target.value })} />
              <select className="input" value={other.meal_type} onChange={(e) => setOther({ ...other, meal_type: e.target.value })}>
                {['breakfast', 'lunch', 'dinner', 'snack'].map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div className="grid grid-cols-4 gap-2">
              <input className="input" type="number" min="0" placeholder="kcal" required value={other.kcal} onChange={(e) => setOther({ ...other, kcal: e.target.value })} />
              <input className="input" type="number" min="0" placeholder="Protein g" value={other.protein_g} onChange={(e) => setOther({ ...other, protein_g: e.target.value })} />
              <input className="input" type="number" min="0" placeholder="Carbs g" value={other.carbs_g} onChange={(e) => setOther({ ...other, carbs_g: e.target.value })} />
              <input className="input" type="number" min="0" placeholder="Fat g" value={other.fat_g} onChange={(e) => setOther({ ...other, fat_g: e.target.value })} />
            </div>
            <button className="btn-secondary w-full">Add to log</button>
          </form>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="card md:col-span-2">
          <h3 className="font-medium text-forestdark mb-1">Last 7 days</h3>
          <p className="text-xs text-ink/50 mb-3">
            {week.average_kcal_on_logged_days ? `About ${week.average_kcal_on_logged_days} kcal a day on the ${week.days_logged} day${week.days_logged === 1 ? '' : 's'} you logged.` : 'Log a few days to see your pattern.'}
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E4DCC9" />
              <XAxis dataKey="day" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} domain={[0, (max) => Math.max(max, week.goal.kcal_target || 0)]} />
              <Tooltip />
              <Legend />
              <Bar dataKey="Mess" stackId="a" fill="#2F5D50" />
              <Bar dataKey="Other" stackId="a" fill="#7FA98A" />
              {week.goal.kcal_target && <ReferenceLine y={week.goal.kcal_target} stroke="#1B2A2A" strokeDasharray="4 4" label={{ value: 'Target', fontSize: 11, position: 'insideTopRight' }} />}
            </BarChart>
          </ResponsiveContainer>
        </div>
        <form onSubmit={saveGoal} className="card space-y-3 self-start">
          <h3 className="font-medium text-forestdark">Daily target (optional)</h3>
          <div>
            <label className="label">Calories (kcal)</label>
            <input className="input" type="number" min="1200" max="5000" placeholder="e.g. 2200" value={goal.kcal_target} onChange={(e) => setGoal({ ...goal, kcal_target: e.target.value })} />
          </div>
          <div>
            <label className="label">Protein (g)</label>
            <input className="input" type="number" min="10" max="300" placeholder="e.g. 60" value={goal.protein_target_g} onChange={(e) => setGoal({ ...goal, protein_target_g: e.target.value })} />
          </div>
          <button className="btn-secondary w-full">Save target</button>
          <p className="text-xs text-ink/50">Leave blank for no target. For advice about your own needs, talk to a doctor or dietitian.</p>
        </form>
      </div>
    </div>
  )
}
