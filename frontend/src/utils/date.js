export function toISODate(d) {
  // local calendar date (toISOString would give the UTC date, which is the previous day for IST mornings)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mm}-${dd}`
}
export function todayISO() {
  return toISODate(new Date())
}
export function addDaysISO(baseISO, days) {
  const d = new Date(baseISO + 'T00:00:00')
  d.setDate(d.getDate() + days)
  return toISODate(d)
}
export function weekdayLabel(iso) {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
}

// "12:05" style countdown from a number of seconds
export function countdown(seconds) {
  const s = Math.max(Math.floor(seconds), 0)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
// Wall-clock label for a naive ISO timestamp from the server (already in the mess's local time)
export function clockLabel(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}
export function dateTimeLabel(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString([], { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
}
