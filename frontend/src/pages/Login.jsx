import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('student1@mess.local')
  const [password, setPassword] = useState('student123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-sand">
      <div className="card w-full max-w-sm">
        <h1 className="text-2xl text-forestdark mb-1">Welcome back</h1>
        <p className="text-sm text-ink/60 mb-6">Sign in to confirm meals and cut food waste.</p>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="label">Email</label>
            <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
          </div>
          <div>
            <label className="label">Password</label>
            <input className="input" value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
          </div>
          {error && <p className="text-sm text-clay">{error}</p>}
          <button className="btn-primary w-full" disabled={loading}>{loading ? 'Signing in...' : 'Sign in'}</button>
        </form>
        <p className="text-sm text-ink/60 mt-4">
          No account? <Link to="/register" className="text-forest font-medium">Register</Link>
        </p>
        <div className="mt-6 pt-4 border-t border-sandline text-xs text-ink/50 space-y-1">
          <p>Demo logins (seeded):</p>
          <p>Admin — admin@mess.local / admin123</p>
          <p>Kitchen — kitchen@mess.local / kitchen123</p>
          <p>Student — student1@mess.local ... student20@mess.local / student123</p>
        </div>
      </div>
    </div>
  )
}
