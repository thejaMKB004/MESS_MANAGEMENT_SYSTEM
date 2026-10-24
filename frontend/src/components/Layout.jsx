import React, { useEffect, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

const studentLinks = [
  { to: '/', label: 'Today' },
  { to: '/menu', label: 'Weekly menu' },
  { to: '/rescue', label: 'Rescue meals' },
  { to: '/feedback', label: 'Feedback' },
  { to: '/complaints', label: 'Complaints' },
  { to: '/guests', label: 'Guest meals' },
  { to: '/impact', label: 'My impact' },
  { to: '/profile', label: 'Profile' },
]

const kitchenLinks = [
  { to: '/', label: 'Dashboard' },
  { to: '/kitchen', label: 'Kitchen log' },
  { to: '/surplus', label: 'Rescue & donations' },
]

const adminLinks = [
  { to: '/', label: 'Dashboard' },
  { to: '/kitchen', label: 'Kitchen log' },
  { to: '/surplus', label: 'Rescue & donations' },
  { to: '/menu-planner', label: 'Menu planner' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/optimizer', label: 'Menu optimizer' },
  { to: '/inventory', label: 'Inventory' },
  { to: '/complaints-inbox', label: 'Complaints' },
  { to: '/automation', label: 'Automation' },
]

function useUnread() {
  const [unread, setUnread] = useState(0)
  useEffect(() => {
    let alive = true
    const load = () => api.myNotifications().then((r) => alive && setUnread(r.unread)).catch(() => {})
    load()
    const id = setInterval(load, 30000)
    window.addEventListener('notifications-changed', load)
    return () => { alive = false; clearInterval(id); window.removeEventListener('notifications-changed', load) }
  }, [])
  return unread
}

const linkClass = ({ isActive }) =>
  `px-3 py-1.5 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${
    isActive ? 'bg-forest text-white' : 'text-ink/70 hover:bg-sand'
  }`

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const unread = useUnread()
  const links = user?.role === 'student' ? studentLinks : user?.role === 'kitchen' ? kitchenLinks : adminLinks

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-sandline bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-start justify-between gap-4">
          <div className="shrink-0">
            <h1 className="text-xl text-forestdark">Mess</h1>
            <p className="text-xs text-ink/50 -mt-1">Cook what's needed, rescue what's left</p>
          </div>
          <nav className="flex flex-wrap items-center gap-1 justify-center">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.to === '/'} className={linkClass}>{l.label}</NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3 shrink-0">
            <NavLink to="/notifications" className={linkClass} aria-label={`Notifications, ${unread} unread`}>
              Notifications
              {unread > 0 && <span className="ml-1.5 inline-block min-w-[1.25rem] text-center text-xs rounded-full bg-clay text-white px-1">{unread}</span>}
            </NavLink>
            <span className="text-sm text-ink/60">{user?.name} <span className="tag ml-1">{user?.role}</span></span>
            <button className="text-sm text-clay hover:underline" onClick={() => { logout(); navigate('/login') }}>Log out</button>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">{children}</main>
    </div>
  )
}
