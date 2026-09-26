import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const studentLinks = [
  { to: '/', label: 'Today' },
  { to: '/menu', label: 'Weekly menu' },
  { to: '/feedback', label: 'Feedback' },
  { to: '/complaints', label: 'Complaints' },
  { to: '/guests', label: 'Guest meals' },
  { to: '/impact', label: 'My impact' },
  { to: '/profile', label: 'Profile' },
]

const adminLinks = [
  { to: '/', label: 'Dashboard' },
  { to: '/menu-planner', label: 'Menu planner' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/optimizer', label: 'Menu optimizer' },
  { to: '/inventory', label: 'Inventory' },
  { to: '/complaints-inbox', label: 'Complaints' },
]

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const links = user?.role === 'student' ? studentLinks : adminLinks

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-sandline bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl text-forestdark">Mess</h1>
            <p className="text-xs text-ink/50 -mt-1">Attendance-first food waste reduction</p>
          </div>
          <nav className="flex items-center gap-1">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.to === '/'}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    isActive ? 'bg-forest text-white' : 'text-ink/70 hover:bg-sand'
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <span className="text-sm text-ink/60">{user?.name} <span className="tag ml-1">{user?.role}</span></span>
            <button
              className="text-sm text-clay hover:underline"
              onClick={() => { logout(); navigate('/login') }}
            >
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">{children}</main>
    </div>
  )
}
