export function toISODate(d) {
  return d.toISOString().slice(0, 10)
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
