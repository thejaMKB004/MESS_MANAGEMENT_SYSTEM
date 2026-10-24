import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import Badge from '../components/Badge'

// Public page: the secret token in the emailed link is the only credential an NGO needs.
export default function NgoRespond() {
  const { token } = useParams()
  const [offer, setOffer] = useState(null)
  const [error, setError] = useState('')
  const [result, setResult] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.publicDonation(token).then(setOffer).catch((e) => setError(e.message)) }, [token])

  const respond = async (action) => {
    setBusy(true)
    setError('')
    try {
      const r = await api.respondDonation(token, action)
      setResult(r.detail)
      setOffer({ ...offer, status: r.status })
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-sand px-4">
      <div className="card w-full max-w-md">
        <h1 className="text-2xl text-forestdark mb-1">Food available for pickup</h1>
        {!offer && !error && <p className="text-ink/60">Loading...</p>}
        {error && <p className="text-clay text-sm mt-2">{error}</p>}
        {offer && (
          <>
            <p className="text-sm text-ink/60 mb-4">For {offer.ngo}</p>
            <dl className="text-sm space-y-2 mb-5">
              <div className="flex justify-between"><dt className="text-ink/60">Food</dt><dd className="font-medium text-right">{offer.dish_description}</dd></div>
              <div className="flex justify-between"><dt className="text-ink/60">Portions</dt><dd className="font-medium">{offer.portions}</dd></div>
              <div className="flex justify-between"><dt className="text-ink/60">Collect before</dt><dd className="font-medium">{offer.safe_until_label}</dd></div>
              <div className="flex justify-between"><dt className="text-ink/60">Status</dt><dd><Badge value={offer.status} /></dd></div>
            </dl>
            {result && <p className="text-sm text-forest mb-3">{result}</p>}
            {offer.status === 'offered' && !offer.expired && (
              <div className="flex gap-2">
                <button className="btn-primary flex-1" disabled={busy} onClick={() => respond('accept')}>Accept, we'll collect</button>
                <button className="btn-secondary flex-1" disabled={busy} onClick={() => respond('decline')}>Decline</button>
              </div>
            )}
            {offer.status === 'offered' && offer.expired && <p className="text-sm text-ink/60">This offer has expired because the food is past its safe time.</p>}
            <p className="text-xs text-ink/40 mt-4">The first partner to accept gets the food. Please bring your own containers.</p>
          </>
        )}
      </div>
    </div>
  )
}
