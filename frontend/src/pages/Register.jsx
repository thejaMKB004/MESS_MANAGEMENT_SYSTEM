import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '', roll_no: '', hostel: '', role: 'student' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(form)
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
        <h1 className="text-2xl text-forestdark mb-1">Create an account</h1>
        <p className="text-sm text-ink/60 mb-6">Join your mess's attendance system.</p>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="label">Full name</label>
            <input className="input" value={form.name} onChange={update('name')} required />
          </div>
          <div>
            <label className="label">Email</label>
            <input className="input" type="email" value={form.email} onChange={update('email')} required />
          </div>
          <div>
            <label className="label">Password</label>
            <input className="input" type="password" value={form.password} onChange={update('password')} required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Roll no.</label>
              <input className="input" value={form.roll_no} onChange={update('roll_no')} />
            </div>
            <div>
              <label className="label">Hostel</label>
              <input className="input" value={form.hostel} onChange={update('hostel')} />
            </div>
          </div>
          {error && <p className="text-sm text-clay">{error}</p>}
          <button className="btn-primary w-full" disabled={loading}>{loading ? 'Creating...' : 'Create account'}</button>
        </form>
        <p className="text-sm text-ink/60 mt-4">
          Already have an account? <Link to="/login" className="text-forest font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
