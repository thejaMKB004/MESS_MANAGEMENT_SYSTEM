import React, { useEffect, useState, useCallback } from 'react'
import { api } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import { countdown, dateTimeLabel } from '../../utils/date'
import Badge from '../../components/Badge'

export default function Surplus() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [listings, setListings] = useState([])
  const [donations, setDonations] = useState([])
  const [ngos, setNgos] = useState([])
  const [fetchedAt, setFetchedAt] = useState(Date.now())
  const [, setTick] = useState(0)
  const [code, setCode] = useState('')
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [ngoForm, setNgoForm] = useState({ name: '', email: '', contact_person: '', phone: '', area: '' })

  const load = useCallback(async () => {
    const [l, d, n] = await Promise.all([api.listSurplus(), api.listDonations(), api.listNgos()])
    setListings(l); setDonations(d); setNgos(n); setFetchedAt(Date.now())
  }, [])

  useEffect(() => {
    load().catch((e) => setError(e.message))
    const poll = setInterval(() => load().catch(() => {}), 20000)
    const clock = setInterval(() => setTick((t) => t + 1), 1000)
    return () => { clearInterval(poll); clearInterval(clock) }
  }, [load])

  const elapsed = Math.floor((Date.now() - fetchedAt) / 1000)
  const run = async (fn, okMsg) => {
    setError(''); setMsg('')
    try { const r = await fn(); setMsg(typeof okMsg === 'function' ? okMsg(r) : okMsg); await load() }
    catch (e) { setError(e.message) }
  }

  const verify = (e) => {
    e.preventDefault()
    run(() => api.pickupClaim(code.trim()), (r) => `Hand over ${r.portions} portion of ${r.dish_description} to ${r.student}.`)
    setCode('')
  }

  const addNgo = (e) => {
    e.preventDefault()
    run(() => api.createNgo(ngoForm), 'Partner added.')
    setNgoForm({ name: '', email: '', contact_person: '', phone: '', area: '' })
  }

  const active = listings.filter((l) => l.status === 'open_students' || l.status === 'offered_ngo')
  const past = listings.filter((l) => !active.includes(l))

  return (
    <div className="space-y-8">
      <h1 className="text-2xl text-forestdark">Rescue & donations</h1>
      {error && <p className="text-sm text-clay">{error}</p>}
      {msg && <p className="text-sm text-forest">{msg}</p>}

      <form onSubmit={verify} className="card max-w-md">
        <h2 className="text-lg text-forestdark mb-1">Student at the counter</h2>
        <p className="text-sm text-ink/60 mb-3">Enter the 6-character code on their phone.</p>
        <div className="flex gap-2">
          <input className="input uppercase tracking-widest" maxLength={6} placeholder="K7M2QX" value={code} onChange={(e) => setCode(e.target.value)} required />
          <button className="btn-primary whitespace-nowrap shrink-0">Hand over</button>
        </div>
      </form>

      <section>
        <h2 className="text-lg text-ink/80 mb-3">Active listings</h2>
        {active.length === 0 ? (
          <div className="card text-sm text-ink/60">Nothing on offer. After you log a meal with leftovers on the Kitchen log page, you can list them here.</div>
        ) : (
          <div className="space-y-3">
            {active.map((l) => (
              <div key={l.id} className="card">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div>
                    <p className="font-medium">{l.dish_description}</p>
                    <p className="text-sm text-ink/60"><span className="capitalize">{l.meal_type}</span>, {l.date}. {l.portions_remaining} of {l.portions_total} portions unclaimed. Safe until {l.safe_until_label} ({countdown(l.safe_seconds_left - elapsed)} left).</p>
                  </div>
                  <Badge value={l.status} />
                </div>
                {l.status === 'open_students' && (
                  <p className="text-sm text-ink/60 mt-2">Students can claim for another {countdown(l.student_seconds_left - elapsed)}. After that the rest is offered to NGO partners automatically.</p>
                )}
                {l.claims.length > 0 && (
                  <p className="text-sm text-ink/70 mt-2">Claims: {l.claims.map((c) => `${c.student} (${c.status.replace('_', ' ')})`).join(', ')}</p>
                )}
                {l.donations.length > 0 && (
                  <p className="text-sm text-ink/70 mt-1">NGOs: {l.donations.map((d) => `${d.ngo} (${d.status.replace('_', ' ')})`).join(', ')}</p>
                )}
                <div className="flex gap-2 mt-3">
                  {l.portions_remaining > 0 && (
                    <button className="btn-secondary" onClick={() => run(() => api.offerToNgos(l.id), (r) => r.detail + '.')}>Offer to NGOs now</button>
                  )}
                  <button className="btn-danger" onClick={() => run(() => api.closeSurplus(l.id), 'Listing closed.')}>Close listing</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg text-ink/80 mb-3">NGO pickups</h2>
        {donations.length === 0 ? <p className="text-sm text-ink/50">No donation offers yet.</p> : (
          <div className="card !p-0 overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-ink/50 border-b border-sandline"><th className="p-3">NGO</th><th className="p-3">Food</th><th className="p-3">Portions</th><th className="p-3">Collect before</th><th className="p-3">Status</th><th className="p-3"></th></tr></thead>
              <tbody>
                {donations.slice(0, 15).map((d) => (
                  <tr key={d.id} className="border-b border-sandline/60">
                    <td className="p-3">{d.ngo}</td><td className="p-3">{d.dish_description}</td>
                    <td className="p-3">{d.portions_picked ?? d.portions}</td><td className="p-3">{d.safe_until_label}</td>
                    <td className="p-3"><Badge value={d.status} /></td>
                    <td className="p-3 text-right">
                      {d.status === 'accepted' && <button className="btn-primary !py-1" onClick={() => run(() => api.donationPickup(d.id), 'Pickup recorded.')}>Record pickup</button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {past.length > 0 && (
        <section>
          <h2 className="text-lg text-ink/80 mb-3">Finished listings</h2>
          <div className="card !p-0 overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-ink/50 border-b border-sandline"><th className="p-3">When</th><th className="p-3">Food</th><th className="p-3">Listed</th><th className="p-3">Students</th><th className="p-3">NGOs</th><th className="p-3">Wasted</th><th className="p-3">Status</th></tr></thead>
              <tbody>
                {past.slice(0, 10).map((l) => (
                  <tr key={l.id} className="border-b border-sandline/60">
                    <td className="p-3 capitalize">{l.date} {l.meal_type}</td><td className="p-3">{l.dish_description}</td>
                    <td className="p-3">{l.portions_total}</td><td className="p-3">{l.outcome.claimed_picked_up}</td>
                    <td className="p-3">{l.outcome.donated_picked_up}</td><td className="p-3">{l.outcome.wasted}</td>
                    <td className="p-3"><Badge value={l.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section>
        <h2 className="text-lg text-ink/80 mb-3">NGO partners</h2>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="space-y-2">
            {ngos.map((n) => (
              <div key={n.id} className="card !p-3 text-sm flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium">{n.name}</p>
                  <p className="text-ink/60">{[n.contact_person, n.phone, n.area].filter(Boolean).join(', ')}</p>
                  <p className="text-ink/50">{n.email}</p>
                </div>
                {isAdmin
                  ? <button className={n.active ? 'btn-secondary !py-1' : 'btn-primary !py-1'} onClick={() => run(() => api.updateNgo(n.id, { active: !n.active }), n.active ? 'Partner paused.' : 'Partner activated.')}>{n.active ? 'Pause' : 'Activate'}</button>
                  : <Badge value={n.active ? 'active' : 'paused'} />}
              </div>
            ))}
          </div>
          {isAdmin && (
            <form onSubmit={addNgo} className="card space-y-3 self-start">
              <h3 className="font-medium text-forestdark">Add a partner</h3>
              <input className="input" placeholder="Organisation name" required value={ngoForm.name} onChange={(e) => setNgoForm({ ...ngoForm, name: e.target.value })} />
              <input className="input" type="email" placeholder="Email for offers" required value={ngoForm.email} onChange={(e) => setNgoForm({ ...ngoForm, email: e.target.value })} />
              <div className="grid grid-cols-2 gap-2">
                <input className="input" placeholder="Contact person" value={ngoForm.contact_person} onChange={(e) => setNgoForm({ ...ngoForm, contact_person: e.target.value })} />
                <input className="input" placeholder="Phone" value={ngoForm.phone} onChange={(e) => setNgoForm({ ...ngoForm, phone: e.target.value })} />
              </div>
              <input className="input" placeholder="Area they serve" value={ngoForm.area} onChange={(e) => setNgoForm({ ...ngoForm, area: e.target.value })} />
              <button className="btn-primary w-full">Add partner</button>
            </form>
          )}
        </div>
      </section>
    </div>
  )
}
