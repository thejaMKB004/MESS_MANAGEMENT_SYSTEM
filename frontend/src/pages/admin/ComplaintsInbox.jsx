import React, { useEffect, useState } from 'react'
import { api } from '../../api/client'

const STATUSES = ['open', 'in_progress', 'resolved']

function sentimentLabel(score) {
  if (score === null || score === undefined) return null
  if (score < -0.3) return { text: 'Negative', cls: 'text-clay' }
  if (score > 0.3) return { text: 'Positive', cls: 'text-forest' }
  return { text: 'Neutral', cls: 'text-ink/50' }
}

export default function ComplaintsInbox() {
  const [complaints, setComplaints] = useState([])
  const [filter, setFilter] = useState('')

  const load = () => api.listComplaints(filter || undefined).then(setComplaints)
  useEffect(() => { load() }, [filter])

  const updateStatus = async (id, status) => {
    await api.updateComplaintStatus(id, status)
    load()
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl text-forestdark">Complaints inbox</h1>
        <select className="input w-auto" value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
      </div>
      <div className="space-y-3">
        {complaints.map((c) => {
          const sentiment = sentimentLabel(c.sentiment_score)
          return (
            <div key={c.id} className="card">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="tag capitalize">{c.category.replace('_', ' ')}</span>
                  <span className="tag ml-2 capitalize !bg-clay/10 !text-clay !border-clay/30">{c.severity}</span>
                  {sentiment && <span className={`ml-2 text-xs font-medium ${sentiment.cls}`}>{sentiment.text} tone</span>}
                </div>
                <select
                  className="input w-auto text-xs !py-1"
                  value={c.status}
                  onChange={(e) => updateStatus(c.id, e.target.value)}
                >
                  {STATUSES.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                </select>
              </div>
              <p className="text-sm text-ink/80">{c.description}</p>
              <p className="text-xs text-ink/40 mt-2">{new Date(c.created_at).toLocaleString()}</p>
            </div>
          )
        })}
        {complaints.length === 0 && <p className="text-sm text-ink/50">No complaints match this filter.</p>}
      </div>
    </div>
  )
}
