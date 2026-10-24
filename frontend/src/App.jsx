import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'

import Login from './pages/Login'
import Register from './pages/Register'
import Notifications from './pages/Notifications'
import NgoRespond from './pages/NgoRespond'

import Today from './pages/student/Today'
import WeeklyMenu from './pages/student/WeeklyMenu'
import Feedback from './pages/student/Feedback'
import Complaints from './pages/student/Complaints'
import GuestBooking from './pages/student/GuestBooking'
import MyImpact from './pages/student/MyImpact'
import Profile from './pages/student/Profile'
import Rescue from './pages/student/Rescue'

import Dashboard from './pages/admin/Dashboard'
import MenuPlanner from './pages/admin/MenuPlanner'
import Analytics from './pages/admin/Analytics'
import MenuOptimizer from './pages/admin/MenuOptimizer'
import Inventory from './pages/admin/Inventory'
import ComplaintsInbox from './pages/admin/ComplaintsInbox'
import Automation from './pages/admin/Automation'

import KitchenLog from './pages/kitchen/KitchenLog'
import Surplus from './pages/kitchen/Surplus'

// roles: which roles may open the page (omit = any signed-in user)
function Protected({ children, roles }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="min-h-screen flex items-center justify-center text-ink/50">Loading...</div>
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />
  return <Layout>{children}</Layout>
}

const STAFF = ['admin', 'kitchen']
const ADMIN = ['admin']
const STUDENT = ['student']

export default function App() {
  const { user, loading } = useAuth()
  if (loading) return <div className="min-h-screen flex items-center justify-center text-ink/50">Loading...</div>

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/register" element={user ? <Navigate to="/" replace /> : <Register />} />
      {/* public: NGOs answer a donation offer from their emailed link, no account needed */}
      <Route path="/ngo/respond/:token" element={<NgoRespond />} />

      <Route path="/" element={<Protected>{user?.role === 'student' ? <Today /> : <Dashboard />}</Protected>} />
      <Route path="/notifications" element={<Protected><Notifications /></Protected>} />

      {/* student */}
      <Route path="/menu" element={<Protected roles={STUDENT}><WeeklyMenu /></Protected>} />
      <Route path="/rescue" element={<Protected roles={STUDENT}><Rescue /></Protected>} />
      <Route path="/feedback" element={<Protected roles={STUDENT}><Feedback /></Protected>} />
      <Route path="/complaints" element={<Protected roles={STUDENT}><Complaints /></Protected>} />
      <Route path="/guests" element={<Protected roles={STUDENT}><GuestBooking /></Protected>} />
      <Route path="/impact" element={<Protected roles={STUDENT}><MyImpact /></Protected>} />
      <Route path="/profile" element={<Protected roles={STUDENT}><Profile /></Protected>} />

      {/* kitchen + admin */}
      <Route path="/kitchen" element={<Protected roles={STAFF}><KitchenLog /></Protected>} />
      <Route path="/surplus" element={<Protected roles={STAFF}><Surplus /></Protected>} />

      {/* admin only */}
      <Route path="/menu-planner" element={<Protected roles={ADMIN}><MenuPlanner /></Protected>} />
      <Route path="/analytics" element={<Protected roles={ADMIN}><Analytics /></Protected>} />
      <Route path="/optimizer" element={<Protected roles={ADMIN}><MenuOptimizer /></Protected>} />
      <Route path="/inventory" element={<Protected roles={ADMIN}><Inventory /></Protected>} />
      <Route path="/complaints-inbox" element={<Protected roles={ADMIN}><ComplaintsInbox /></Protected>} />
      <Route path="/automation" element={<Protected roles={ADMIN}><Automation /></Protected>} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
