import React from 'react'

const STYLES = {
  open_students: 'bg-leaf/20 text-forestdark border-leaf/50',
  offered_ngo: 'bg-clay/10 text-clay border-clay/40',
  closed: 'bg-sand text-ink/60 border-sandline',
  expired: 'bg-sand text-ink/50 border-sandline',
  reserved: 'bg-leaf/20 text-forestdark border-leaf/50',
  picked_up: 'bg-forest text-white border-forest',
  offered: 'bg-clay/10 text-clay border-clay/40',
  accepted: 'bg-leaf/20 text-forestdark border-leaf/50',
  declined: 'bg-sand text-ink/50 border-sandline',
  active: 'bg-leaf/20 text-forestdark border-leaf/50',
  paused: 'bg-sand text-ink/50 border-sandline',
  in_app: 'bg-sand text-ink/60 border-sandline',
  ok: 'bg-leaf/20 text-forestdark border-leaf/50',
  error: 'bg-clay/10 text-clay border-clay/40',
  sent: 'bg-leaf/20 text-forestdark border-leaf/50',
  skipped: 'bg-sand text-ink/50 border-sandline',
  failed: 'bg-clay/10 text-clay border-clay/40',
}
const LABELS = {
  open_students: 'Open to students', offered_ngo: 'Offered to NGOs', picked_up: 'Collected',
  skipped: 'Not emailed (no SMTP)', in_app: 'In-app only',
}

export default function Badge({ value }) {
  const cls = STYLES[value] || 'bg-sand text-ink/60 border-sandline'
  const label = LABELS[value] || String(value).replace(/_/g, ' ')
  return <span className={`inline-block text-xs px-2 py-0.5 rounded-full border ${cls}`}>{label}</span>
}
