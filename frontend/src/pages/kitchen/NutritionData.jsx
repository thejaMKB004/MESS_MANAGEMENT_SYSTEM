import React, { useEffect, useState } from 'react'
import { api } from '../../api/client'

const ALLERGENS = ['gluten', 'dairy', 'egg', 'peanuts', 'tree_nuts', 'soy', 'shellfish']
const FIELDS = [['kcal', 'kcal'], ['protein_g', 'Protein g'], ['carbs_g', 'Carbs g'], ['fat_g', 'Fat g'], ['fibre_g', 'Fibre g']]
const blank = { kcal: '', protein_g: '', carbs_g: '', fat_g: '', fibre_g: '', food_type: 'veg', allergens: [] }

export default function NutritionData() {
  const [dishes, setDishes] = useState([])
  const [editing, setEditing] = useState(null)       // dish name
  const [form, setForm] = useState(blank)
  const [newName, setNewName] = useState('')
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const load = () => api.nutritionDishes().then(setDishes).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])

  const edit = (d) => {
    setMsg(''); setError('')
    setEditing(d.dish_name)
    setForm(d.has_data ? { ...blank, ...d } : blank)
  }

  const save = async (e) => {
    e.preventDefault(); setMsg(''); setError('')
    const name = editing === '__new__' ? newName.trim() : editing
    try {
      const body = { food_type: form.food_type, allergens: form.allergens }
      FIELDS.forEach(([k]) => { body[k] = Number(form[k]) || 0 })
      await api.saveDishNutrition(name, body)
      setMsg(`Saved ${name}.`); setEditing(null); setNewName(''); load()
    } catch (err) { setError(err.message) }
  }

  const toggle = (a) => setForm({ ...form, allergens: form.allergens.includes(a) ? form.allergens.filter((x) => x !== a) : [...form.allergens, a] })
  const missing = dishes.filter((d) => !d.has_data).length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl text-forestdark mb-1">Nutrition data</h1>
        <p className="text-sm text-ink/60">Approximate values for one regular portion. Students see these on the menu and in their food log, with warnings based on their own allergy and diet profile.</p>
      </div>
      {missing > 0 && <p className="text-sm text-clay">{missing} dish{missing > 1 ? 'es' : ''} on the menu still need{missing > 1 ? '' : 's'} nutrition data.</p>}
      {error && <p className="text-sm text-clay">{error}</p>}
      {msg && <p className="text-sm text-forest">{msg}</p>}

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2 card !p-0 overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-ink/50 border-b border-sandline"><th className="p-3">Dish</th><th className="p-3">kcal</th><th className="p-3">Protein</th><th className="p-3">Type</th><th className="p-3">Allergens</th><th className="p-3"></th></tr></thead>
            <tbody>
              {dishes.map((d) => (
                <tr key={d.dish_name} className={`border-b border-sandline/60 ${editing === d.dish_name ? 'bg-sand' : ''}`}>
                  <td className="p-3 font-medium">{d.dish_name}</td>
                  {d.has_data ? (
                    <>
                      <td className="p-3">{Math.round(d.kcal)}</td>
                      <td className="p-3">{Math.round(d.protein_g)} g</td>
                      <td className="p-3">{d.food_type.replace('_', '-')}</td>
                      <td className="p-3 text-ink/70">{d.allergens.map((a) => a.replace('_', ' ')).join(', ') || 'none listed'}</td>
                    </>
                  ) : <td className="p-3 text-clay" colSpan={4}>No data yet</td>}
                  <td className="p-3 text-right"><button className="btn-secondary !py-1" onClick={() => edit(d)}>{d.has_data ? 'Edit' : 'Add'}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="p-3 border-t border-sandline"><button className="btn-secondary" onClick={() => { setEditing('__new__'); setForm(blank) }}>Add another dish</button></div>
        </div>

        {editing && (
          <form onSubmit={save} className="card space-y-3 self-start">
            <h2 className="font-medium text-forestdark">{editing === '__new__' ? 'New dish' : editing}</h2>
            {editing === '__new__' && (
              <div>
                <label className="label">Dish name (exactly as on the menu)</label>
                <input className="input" required value={newName} onChange={(e) => setNewName(e.target.value)} />
              </div>
            )}
            <div className="grid grid-cols-2 gap-2">
              {FIELDS.map(([k, label]) => (
                <div key={k}>
                  <label className="label">{label}</label>
                  <input className="input" type="number" min="0" step="any" required={k === 'kcal'} value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
                </div>
              ))}
              <div>
                <label className="label">Type</label>
                <select className="input" value={form.food_type} onChange={(e) => setForm({ ...form, food_type: e.target.value })}>
                  <option value="veg">Vegetarian</option><option value="egg">Contains egg</option><option value="non_veg">Non-vegetarian</option>
                </select>
              </div>
            </div>
            <div>
              <label className="label">Allergens</label>
              <div className="flex flex-wrap gap-2">
                {ALLERGENS.map((a) => (
                  <button type="button" key={a} onClick={() => toggle(a)}
                    className={`text-xs px-3 py-1 rounded-full border ${form.allergens.includes(a) ? 'bg-clay text-white border-clay' : 'border-sandline text-ink/60 hover:border-clay'}`}>
                    {a.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button className="btn-primary flex-1">Save</button>
              <button type="button" className="btn-secondary" onClick={() => setEditing(null)}>Cancel</button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
