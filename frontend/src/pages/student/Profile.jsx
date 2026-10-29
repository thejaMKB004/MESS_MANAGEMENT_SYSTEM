import React, { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { api } from '../../api/client'

const DIET_OPTIONS = ['vegetarian', 'vegan', 'eggetarian', 'jain', 'no_beef', 'no_pork']
const ALLERGY_OPTIONS = ['peanuts', 'tree_nuts', 'gluten', 'dairy', 'egg', 'soy', 'shellfish']

export default function Profile() {
  const { user, refreshUser } = useAuth()
  const [diet, setDiet] = useState(user?.diet_restrictions || [])
  const [allergies, setAllergies] = useState(user?.allergies || [])
  const [status, setStatus] = useState('')

  const toggle = (list, setList, value) => {
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value])
  }

  const save = async () => {
    await api.updateMe({ diet_restrictions: diet, allergies })
    await refreshUser()
    setStatus('Saved.')
    setTimeout(() => setStatus(''), 1500)
  }

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl text-forestdark mb-6">Diet & allergy profile</h1>
      <div className="card space-y-5">
        <div>
          <label className="label">Dietary restrictions</label>
          <div className="flex flex-wrap gap-2">
            {DIET_OPTIONS.map((d) => (
              <button
                key={d}
                onClick={() => toggle(diet, setDiet, d)}
                className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                  diet.includes(d) ? 'bg-forest text-white border-forest' : 'border-sandline text-ink/60 hover:border-forest'
                }`}
              >
                {d.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="label">Allergies</label>
          <div className="flex flex-wrap gap-2">
            {ALLERGY_OPTIONS.map((a) => (
              <button
                key={a}
                onClick={() => toggle(allergies, setAllergies, a)}
                className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                  allergies.includes(a) ? 'bg-clay text-white border-clay' : 'border-sandline text-ink/60 hover:border-clay'
                }`}
              >
                {a.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>
        {status && <p className="text-sm text-forest">{status}</p>}
        <button className="btn-primary" onClick={save}>Save profile</button>
      </div>
    </div>
  )
}
