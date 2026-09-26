import React, { useState } from 'react'
import { api } from '../../api/client'

const CATEGORIES = ['hygiene', 'food_quality', 'service', 'billing', 'suggestion', 'other']
const SEVERITIES = ['low', 'medium', 'high']

export default function Complaints() {
  const [category, setCategory] = useState('food_quality')
  const [severity, setSeverity] = useState('medium')
  const [description, setDescription] = useState('')
  const [status, setStatus] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    try {
      await api.createComplaint({ category, severity, description })
      setStatus('Submitted — the mess team will review it.')
      setDescription('')
    } catch (e) {
      setStatus(e.message)
    }
  }

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl text-forestdark mb-6">Complaints & suggestions</h1>
      <form onSubmit={submit} className="card space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Category</label>
            <select className="input" value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace('_', ' ')}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Severity</label>
            <select className="input" value={severity} onChange={(e) => setSeverity(e.target.value)}>
              {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="label">Description</label>
          <textarea className="input" rows="5" value={description} onChange={(e) => setDescription(e.target.value)} required />
        </div>
        {status && <p className="text-sm text-forest">{status}</p>}
        <button className="btn-primary w-full">Submit</button>
      </form>
    </div>
  )
}
