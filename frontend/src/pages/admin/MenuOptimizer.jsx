import React, { useEffect, useState } from 'react'
import { api } from '../../api/client'

export default function MenuOptimizer() {
  const [data, setData] = useState(null)

  useEffect(() => { api.optimizerSuggestions().then(setData) }, [])

  if (!data) return <p className="text-ink/60">Loading...</p>

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl text-forestdark mb-1">Menu optimizer</h1>
        <p className="text-ink/60 text-sm">Advisory only — reads ratings & skip reasons. You decide what actually changes.</p>
      </div>

      {data.rotate_out_suggestions.length > 0 ? (
        <div className="card !border-clay/50 bg-clay/5">
          <h3 className="text-clay font-medium mb-3">Suggested to rotate out</h3>
          <div className="space-y-3">
            {data.rotate_out_suggestions.map((s) => (
              <div key={s.dish_name} className="text-sm border-t border-clay/20 pt-3 first:border-0 first:pt-0">
                <p className="font-medium">{s.dish_name} — avg {s.avg_rating}★ ({s.feedback_count} ratings)</p>
                <p className="text-ink/60">{s.reason}</p>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="text-sm text-ink/50">No dishes currently meet the rotate-out threshold.</p>
      )}

      <div className="card">
        <h3 className="font-medium text-forestdark mb-3">All dishes</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-ink/50 border-b border-sandline">
              <th className="py-2">Dish</th>
              <th className="py-2">Avg rating</th>
              <th className="py-2">Feedback count</th>
              <th className="py-2">"Don't like menu" skips</th>
            </tr>
          </thead>
          <tbody>
            {data.other_dishes.map((d) => (
              <tr key={d.dish_name} className="border-b border-sandline/60">
                <td className="py-2">{d.dish_name}</td>
                <td className="py-2">{d.avg_rating}</td>
                <td className="py-2">{d.feedback_count}</td>
                <td className="py-2">{d.dont_like_menu_skips}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
