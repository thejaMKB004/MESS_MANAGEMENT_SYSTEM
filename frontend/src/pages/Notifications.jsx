import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { dateTimeLabel } from '../utils/date'

const KIND = {
  last_call: 'Last call', reminder: 'Reminder', cooking_sheet: 'Cooking sheet', anomaly: 'Attendance alert',
  low_stock: 'Low stock', weekly_report: 'Weekly report', donation_accepted: 'Donation accepted',
}

export default function Notifications() {
  const [data, setData] = useState(null)
  const navigate = useNavigate()
  const refreshBell = () => window.dispatchEvent(new Event('notifications-changed'))
  const load = () => api.myNotifications().then(setData)

  useEffect(() => { load() }, [])

  const markAll = async () => { await api.readAllNotifications(); refreshBell(); load() }
  const open = async (n) => {
    if (!n.is_read) { await api.readNotification(n.id); refreshBell() }
    if (n.link) navigate(n.link); else load()
  }

  if (!data) return <p className="text-ink/60">Loading...</p>

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl text-forestdark">Notifications</h1>
        {data.unread > 0 && <button className="btn-secondary" onClick={markAll}>Mark all as read</button>}
      </div>
      {data.items.length === 0 ? (
        <div className="card text-sm text-ink/60">You're all caught up. Reminders, last calls and alerts will appear here.</div>
      ) : (
        <div className="space-y-2">
          {data.items.map((n) => (
            <button key={n.id} onClick={() => open(n)} className={`card w-full text-left !p-4 hover:border-forest transition-colors ${n.is_read ? '' : '!border-forest/60'}`}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-ink/50">{KIND[n.kind] || n.kind}</span>
                <span className="text-xs text-ink/40">{dateTimeLabel(n.created_at)}</span>
              </div>
              <p className={`text-sm ${n.is_read ? 'text-ink/70' : 'font-semibold'}`}>{n.title}</p>
              <p className="text-sm text-ink/60 whitespace-pre-line mt-1">{n.body}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
