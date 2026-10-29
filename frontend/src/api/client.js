const BASE_URL = 'http://127.0.0.1:8000'

function getToken() {
  return localStorage.getItem('mess_token')
}

async function request(path, { method = 'GET', body, form, auth = true } = {}) {
  const headers = {}
  let payload = undefined

  if (form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    payload = new URLSearchParams(body).toString()
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  if (auth) {
    const token = getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${path}`, { method, headers, body: payload })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const errBody = await res.json()
      detail = errBody.detail || JSON.stringify(errBody)
    } catch (_) {}
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // auth
  login: (email, password) => request('/auth/login', { method: 'POST', body: { username: email, password }, form: true, auth: false }),
  register: (payload) => request('/auth/register', { method: 'POST', body: payload, auth: false }),

  // users
  me: () => request('/users/me'),
  updateMe: (payload) => request('/users/me', { method: 'PATCH', body: payload }),

  // menus
  listMenus: (from, to) => request(`/menus?from=${from}&to=${to}`),
  createMenu: (payload) => request('/menus', { method: 'POST', body: payload }),
  updateMenu: (id, payload) => request(`/menus/${id}`, { method: 'PATCH', body: payload }),

  // attendance
  confirmAttendance: (payload) => request('/attendance/confirm', { method: 'POST', body: payload }),
  myAttendance: (from, to) => request(`/attendance/mine?from=${from}&to=${to}`),
  todayAttendance: (mealType, forDate) => request(`/attendance/today?meal_type=${mealType}&for_date=${forDate}`),
  attendanceStats: (from, to) => request(`/attendance/stats?from=${from}&to=${to}`),
  checkin: (attendanceId, method = 'qr') => request('/attendance/checkin', { method: 'POST', body: { attendance_id: attendanceId, method } }),

  // feedback
  createFeedback: (payload) => request('/feedback', { method: 'POST', body: payload }),
  dishFeedback: (dishName, from, to) => request(`/feedback/dish/${encodeURIComponent(dishName)}?from=${from || ''}&to=${to || ''}`),

  // complaints
  createComplaint: (payload) => request('/complaints', { method: 'POST', body: payload }),
  listComplaints: (statusFilter) => request(`/complaints${statusFilter ? `?status=${statusFilter}` : ''}`),
  updateComplaintStatus: (id, status) => request(`/complaints/${id}/status`, { method: 'PATCH', body: { status } }),

  // analytics
  attendanceAnalytics: (from, to) => request(`/analytics/attendance?from=${from}&to=${to}`),
  dishRatings: (limit = 5) => request(`/analytics/dish-ratings?limit=${limit}`),
  wasteEstimate: (date, mealType) => request(`/analytics/waste-estimate?date=${date}&meal_type=${mealType}`),
  weeklyReport: (weekStart) => request(`/analytics/weekly-report?week_start=${weekStart}`),
  anomalies: (date) => request(`/analytics/anomalies?date=${date}`),

  // menu optimizer
  optimizerSuggestions: (from, to) => request(`/menu-optimizer/suggestions?from=${from || ''}&to=${to || ''}`),

  // inventory
  listInventory: () => request('/inventory/items'),
  createInventoryItem: (payload) => request('/inventory/items', { method: 'POST', body: payload }),
  linkDishIngredient: (payload) => request('/inventory/dish-ingredients', { method: 'POST', body: payload }),
  inventoryRequirements: (date, mealType) => request(`/inventory/requirements?date=${date}&meal_type=${mealType}`),

  // guest bookings
  createGuestBooking: (payload) => request('/guest-bookings', { method: 'POST', body: payload }),
  myGuestBookings: () => request('/guest-bookings/mine'),

  // impact
  myImpact: () => request('/impact/me'),

  // kitchen production log
  cookingSheet: (date, mealType) => request(`/kitchen/cooking-sheet?date=${date}&meal_type=${mealType}`),
  kitchenLogs: (from, to) => request(`/kitchen/logs?from=${from}&to=${to}`),
  saveKitchenLog: (payload) => request('/kitchen/logs', { method: 'PUT', body: payload }),
  realWaste: (from, to) => request(`/analytics/real-waste?from=${from}&to=${to}`),

  // surplus rescue
  openSurplus: () => request('/surplus/open'),
  claimSurplus: (id, portions = 1) => request(`/surplus/listings/${id}/claim`, { method: 'POST', body: { portions } }),
  myClaims: () => request('/surplus/claims/mine'),
  listSurplus: () => request('/surplus/listings'),
  createSurplus: (payload) => request('/surplus/listings', { method: 'POST', body: payload }),
  offerToNgos: (id) => request(`/surplus/listings/${id}/offer-ngo`, { method: 'POST', body: {} }),
  closeSurplus: (id) => request(`/surplus/listings/${id}/close`, { method: 'POST' }),
  pickupClaim: (code) => request('/surplus/claims/pickup', { method: 'POST', body: { code } }),

  // NGO partners and donations
  listNgos: () => request('/ngos'),
  createNgo: (payload) => request('/ngos', { method: 'POST', body: payload }),
  updateNgo: (id, payload) => request(`/ngos/${id}`, { method: 'PATCH', body: payload }),
  listDonations: () => request('/donations'),
  donationPickup: (id) => request(`/donations/${id}/pickup`, { method: 'POST', body: {} }),
  publicDonation: (token) => request(`/public/donations/${token}`, { auth: false }),
  respondDonation: (token, action) => request(`/public/donations/${token}/respond`, { method: 'POST', body: { action }, auth: false }),

  // notifications
  myNotifications: () => request('/notifications/mine'),
  readNotification: (id) => request(`/notifications/${id}/read`, { method: 'POST' }),
  readAllNotifications: () => request('/notifications/mine/read-all', { method: 'POST' }),
  outbox: () => request('/notifications/outbox'),

  // nutrition
  nutritionDishes: () => request('/nutrition/dishes'),
  saveDishNutrition: (name, payload) => request(`/nutrition/dishes/${encodeURIComponent(name)}`, { method: 'PUT', body: payload }),
  mealNutrition: (from, to) => request(`/nutrition/meals?from=${from}&to=${to}`),
  intakeDay: (date) => request(`/nutrition/intake?date=${date}`),
  addIntake: (payload) => request('/nutrition/intake', { method: 'POST', body: payload }),
  deleteIntake: (id) => request(`/nutrition/intake/${id}`, { method: 'DELETE' }),
  intakeSummary: (days = 7) => request(`/nutrition/summary?days=${days}`),
  setNutritionGoal: (payload) => request('/nutrition/goal', { method: 'PUT', body: payload }),

  // automation
  automationStatus: () => request('/automation/status'),
  automationRuns: () => request('/automation/runs'),
  runAutomation: (job = 'all', force = false) => request(`/automation/run?job=${job}&force=${force}`, { method: 'POST' }),
}

export function setToken(token) {
  localStorage.setItem('mess_token', token)
}
export function clearToken() {
  localStorage.removeItem('mess_token')
}
export { getToken }
