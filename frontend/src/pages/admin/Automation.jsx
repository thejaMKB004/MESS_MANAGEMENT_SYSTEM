import React, { useEffect, useState, useCallback } from 'react'
import { api } from '../../api/client'
import { dateTimeLabel } from '../../utils/date'
import Badge from '../../components/Badge'

function summarize(details) {
  if (!details) return ''
  return Object.entries(details).map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`).join(', ')
}

export default function Automation() {
  const [status, setStatus] = useState(null)
  const [runs, setRuns] = useState([])
  const [outbox, setOutbox] = useState([])
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')

  const load = useCallback(async () => {
    const [s, r, o] = await Promise.all([api.automationStatus(), api.automationRuns(), api.outbox()])
    setStatus(s); setRuns(r); setOutbox(o)
  }, [])

  useEffect(() => {
    load().catch((e) => setError(e.message))
    const poll = setInterval(() => load().catch(() => {}), 20000)
    return () => clearInterval(poll)
  }, [load])

  const run = async (job, force) => {
    setError(''); setMsg(''); setBusy(job + force)
    try {
      const res = await api.runAutomation(job, force)
      const ran = Object.keys(res).filter((k) => res[k] && (!Array.isArray(res[k]) || res[k].length))
      setMsg(ran.length ? `Ran: ${ran.map((k) => k.replace(/_/g, ' ')).join(', ')}.` : 'Nothing was due right now. Use "Run now" to run a job regardless of the time.')
      await load()
    } catch (e) { setError(e.message) } finally { setBusy('') }
  }

  if (!status) return error ? <p className="text-clay text-sm">{error}</p> : <p className="text-ink/60">Loading...</p>

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl text-forestdark mb-1">Automation</h1>
        <p className="text-sm text-ink/60">
          Background jobs check the clock every {status.tick_seconds} seconds and run when they are due, at most once per meal or day.
          {!status.enabled && ' Automation is switched off on this server, so only manual runs work.'}
        </p>
      </div>
      {error && <p className="text-sm text-clay">{error}</p>}
      {msg && <p className="text-sm text-forest">{msg}</p>}

      <section className="card !p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-ink/50 border-b border-sandline"><th className="p-3">Job</th><th className="p-3">What it does</th><th className="p-3"></th></tr></thead>
          <tbody>
            {status.jobs.map((j) => (
              <tr key={j.name} className="border-b border-sandline/60">
                <td className="p-3 font-medium capitalize">{j.name.replace(/_/g, ' ')}</td>
                <td className="p-3 text-ink/70">{j.description}</td>
                <td className="p-3 text-right"><button className="btn-secondary !py-1" disabled={busy === j.name + true} onClick={() => run(j.name, true)}>Run now</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="p-3 flex gap-2 border-t border-sandline">
          <button className="btn-secondary" onClick={() => run('all', false)}>Run what's due</button>
          <button className="btn-primary" onClick={() => run('all', true)}>Run every job now</button>
        </div>
      </section>

      <section>
        <h2 className="text-lg text-ink/80 mb-3">Recent runs</h2>
        {runs.length === 0 ? <p className="text-sm text-ink/50">No jobs have run yet.</p> : (
          <div className="card !p-0 overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-ink/50 border-b border-sandline"><th className="p-3">When</th><th className="p-3">Job</th><th className="p-3">Result</th><th className="p-3">Status</th></tr></thead>
              <tbody>
                {runs.slice(0, 20).map((r) => (
                  <tr key={r.id} className="border-b border-sandline/60">
                    <td className="p-3 whitespace-nowrap">{dateTimeLabel(r.ran_at)}</td>
                    <td className="p-3 capitalize">{r.job.replace(/_/g, ' ')}</td>
                    <td className="p-3 text-ink/70">{summarize(r.details)}</td>
                    <td className="p-3"><Badge value={r.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg text-ink/80 mb-1">Outbox</h2>
        <p className="text-sm text-ink/60 mb-3">Everything the system has sent. Set the SMTP_* environment variables to also deliver these by email.</p>
        {outbox.length === 0 ? <p className="text-sm text-ink/50">Nothing sent yet.</p> : (
          <div className="space-y-2">
            {outbox.slice(0, 15).map((n) => (
              <div key={n.id} className="card !p-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-medium">{n.title}</p>
                  <Badge value={n.email_status === 'none' ? 'in_app' : n.email_status} />
                </div>
                <p className="text-ink/50 text-xs mb-1">To {n.recipient} on {dateTimeLabel(n.created_at)}</p>
                <p className="text-ink/70 whitespace-pre-line">{n.body}</p>
                {n.link && n.link.startsWith('http') && <a className="text-forest underline text-sm" href={n.link} target="_blank" rel="noreferrer">Open the response link</a>}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
