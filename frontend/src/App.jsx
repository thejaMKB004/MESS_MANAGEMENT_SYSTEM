import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'

import Login from './pages/Login'
import Register from './pages/Register'

import Today from './pages/student/Today'
import WeeklyMenu from './pages/student/WeeklyMenu'
import Feedback from './pages/student/Feedback'
import Complaints from './pages/student/Complaints'
import GuestBooking from './pages/student/GuestBooking'
import MyImpact from './pages/student/MyImpact'
import Profile from './pages/student/Profile'

import Dashboard from './pages/admin/Dashboard'
import MenuPlanner from './pages/admin/MenuPlanner'
import Analytics from './pages/admin/Analytics'
import MenuOptimizer from './pages/admin/MenuOptimizer'
import Inventory from './pages/admin/Inventory'
import ComplaintsInbox from './pages/admin/ComplaintsInbox'

function Protected({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="min-h-screen flex items-center justify-center text-ink/50">Loading...</div>
  if (!user) return <Navigate to="/login" replace />
  return <Layout>{children}</Layout>
}

export default function App() {
  const { user, loading } = useAuth()

  if (loading) return <div className="min-h-screen flex items-center justify-center text-ink/50">Loading...</div>

  const isAdmin = user?.role === 'admin' || user?.role === 'kitchen'

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/register" element={user ? <Navigate to="/" replace /> : <Register />} />

      <Route path="/" element={<Protected>{isAdmin ? <Dashboard /> : <Today />}</Protected>} />

      {/* student-only */}
      <Route path="/menu" element={<Protected><WeeklyMenu /></Protected>} />
      <Route path="/feedback" element={<Protected><Feedback /></Protected>} />
      <Route path="/complaints" element={<Protected>{isAdmin ? <ComplaintsInbox /> : <Complaints />}</Protected>} />
      <Route path="/guests" element={<Protected><GuestBooking /></Protected>} />
      <Route path="/impact" element={<Protected><MyImpact /></Protected>} />
      <Route path="/profile" element={<Protected><Profile /></Protected>} />

      {/* admin-only */}
      <Route path="/menu-planner" element={<Protected><MenuPlanner /></Protected>} />
      <Route path="/analytics" element={<Protected><Analytics /></Protected>} />
      <Route path="/optimizer" element={<Protected><MenuOptimizer /></Protected>} />
      <Route path="/inventory" element={<Protected><Inventory /></Protected>} />
      <Route path="/complaints-inbox" element={<Protected><ComplaintsInbox /></Protected>} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
