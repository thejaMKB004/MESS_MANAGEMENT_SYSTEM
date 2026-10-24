import React, { useEffect, useState, useCallback } from 'react'
import { api } from '../../api/client'
import { countdown } from '../../utils/date'
import Badge from '../../components/Badge'

export default function Rescue() {
  const [listings, setListings] = useState([])
  const [claims, setClaims] = useState([])
  const [fetchedAt, setFetchedAt] = useState(Date.now())
  const [, setTick] = useState(0)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(null)
  const [loaded, setLoaded] = useState(false)

  const load = useCallback(async () => {
    const [open, mine] = await Promise.all([api.openSurplus(), api.myClaims()])
    setListings(open)
    setClaims(mine)
    setFetchedAt(Date.now())
    setLoaded(true)
  }, [])

  useEffect(() => {
    load().catch((e) => setError(e.message))
    const poll = setInterval(() => load().catch(() => {}), 15000)   // new last calls appear without a refresh
    const clock = setInterval(() => setTick((t) => t + 1), 1000)
    return () => { clearInterval(poll); clearInterval(clock) }
  }, [load])

  const elapsed = Math.floor((Date.now() - fetchedAt) / 1000)

  const claim = async (id) => {
    setError('')
    setBusy(id)
    try {
      await api.claimSurplus(id, 1)
      await load()
    } catch (e) {
      setError(e.message)
      load().catch(() => {})
    } finally {
      setBusy(null)
    }
  }

  const active = claims.filter((c) => c.status === 'reserved' && c.seconds_left - elapsed > 0)
  const history = claims.filter((c) => !active.includes(c))

  if (!loaded && !error) return <p className="text-ink/60">Loading...</p>

  return (
    <div className="space-y-8 max-w-3xl">
      <div>
        <h1 className="text-2xl text-forestdark mb-1">Rescue meals</h1>
        <p className="text-ink/60 text-sm">Food left over after service is offered here first, free, one portion each. Show your code at the counter.</p>
      </div>

      {error && <p className="text-sm text-clay">{error}</p>}

      {active.length > 0 && (
        <section>
          <h2 className="text-lg text-ink/80 mb-3">Your codes</h2>
          <div className="space-y-3">
            {active.map((c) => (
              <div key={c.id} className="card !border-forest flex items-center justify-between">
                <div>
                  <p className="font-medium">{c.dish_description}</p>
                  <p className="text-sm text-ink/60">Collect within {countdown(c.seconds_left - elapsed)} minutes or the portion goes to someone else.</p>
                </div>
                <p className="font-display text-3xl tracking-widest text-forestdark">{c.code}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="text-lg text-ink/80 mb-3">Available now</h2>
        {listings.length === 0 ? (
          <div className="card text-sm text-ink/60">
            Nothing is on offer right now. When the kitchen has leftovers you'll get a notification, and they'll show up here.
          </div>
        ) : (
          <div className="space-y-3">
            {listings.map((l) => {
              const left = l.student_seconds_left - elapsed
              const mine = claims.some((c) => c.dish_description === l.dish_description && c.status === 'reserved')
              return (
                <div key={l.id} className="card flex items-center justify-between gap-4">
                  <div>
                    <p className="font-medium">{l.dish_description}</p>
                    <p className="text-sm text-ink/60">
                      <span className="capitalize">{l.meal_type}</span> leftovers, {l.portions_remaining} of {l.portions_total} portions left. Claim within {countdown(left)}.
                    </p>
                  </div>
                  <button className="btn-primary shrink-0" disabled={busy === l.id || left <= 0 || mine} onClick={() => claim(l.id)}>
                    {mine ? 'Claimed' : busy === l.id ? 'Claiming...' : 'Claim a portion'}
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </section>

      {history.length > 0 && (
        <section>
          <h2 className="text-lg text-ink/80 mb-3">Earlier claims</h2>
          <div className="space-y-2">
            {history.map((c) => (
              <div key={c.id} className="card !p-3 text-sm flex items-center justify-between">
                <span>{c.dish_description}</span>
                <Badge value={c.status} />
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
