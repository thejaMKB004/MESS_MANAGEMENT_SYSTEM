import React, { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { todayISO } from '../../utils/date'

export default function Inventory() {
  const [items, setItems] = useState([])
  const [form, setForm] = useState({ name: '', unit: 'kg', cost_per_unit: '', stock_qty: '' })
  const [reqDate, setReqDate] = useState(todayISO())
  const [reqMeal, setReqMeal] = useState('lunch')
  const [requirements, setRequirements] = useState(null)
  const [status, setStatus] = useState('')

  const load = () => api.listInventory().then(setItems)
  useEffect(() => { load() }, [])

  const addItem = async (e) => {
    e.preventDefault()
    try {
      await api.createInventoryItem({ ...form, cost_per_unit: Number(form.cost_per_unit) || 0, stock_qty: Number(form.stock_qty) || 0 })
      setForm({ name: '', unit: 'kg', cost_per_unit: '', stock_qty: '' })
      load()
    } catch (e) {
      setStatus(e.message)
    }
  }

  const fetchRequirements = async () => {
    try {
      setRequirements(await api.inventoryRequirements(reqDate, reqMeal))
    } catch (e) {
      setStatus(e.message)
      setRequirements(null)
    }
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl text-forestdark">Inventory</h1>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="font-medium text-forestdark mb-3">Add inventory item</h3>
          <form onSubmit={addItem} className="space-y-3">
            <input className="input" placeholder="Item name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            <div className="grid grid-cols-3 gap-2">
              <input className="input" placeholder="Unit (kg, L...)" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
              <input className="input" type="number" placeholder="Cost/unit ₹" value={form.cost_per_unit} onChange={(e) => setForm({ ...form, cost_per_unit: e.target.value })} />
              <input className="input" type="number" placeholder="Stock qty" value={form.stock_qty} onChange={(e) => setForm({ ...form, stock_qty: e.target.value })} />
            </div>
            <button className="btn-primary w-full">Add item</button>
          </form>
          {status && <p className="text-sm text-clay mt-2">{status}</p>}

          <div className="mt-4 pt-4 border-t border-sandline">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-ink/50"><th>Item</th><th>Unit</th><th>Cost</th><th>Stock</th></tr></thead>
              <tbody>
                {items.map((it) => (
                  <tr key={it.id} className="border-t border-sandline/60"><td className="py-1">{it.name}</td><td>{it.unit}</td><td>₹{it.cost_per_unit}</td><td>{it.stock_qty}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <h3 className="font-medium text-forestdark mb-3">Ingredient requirements for a meal</h3>
          <p className="text-xs text-ink/50 mb-3">Computed from confirmed attendance × dish-ingredient links.</p>
          <div className="grid grid-cols-2 gap-2 mb-3">
            <input type="date" className="input" value={reqDate} onChange={(e) => setReqDate(e.target.value)} />
            <select className="input" value={reqMeal} onChange={(e) => setReqMeal(e.target.value)}>
              <option value="breakfast">Breakfast</option>
              <option value="lunch">Lunch</option>
              <option value="dinner">Dinner</option>
            </select>
          </div>
          <button className="btn-secondary w-full mb-3" onClick={fetchRequirements}>Compute requirements</button>
          {requirements && (
            <div>
              <p className="text-sm text-ink/70 mb-2">{requirements.total_servings} servings · est. cost ₹{requirements.estimated_total_cost_inr}</p>
              <table className="w-full text-sm">
                <thead><tr className="text-left text-ink/50"><th>Ingredient</th><th>Needed</th><th>Stock</th><th>Shortfall</th></tr></thead>
                <tbody>
                  {Object.entries(requirements.ingredient_requirements).map(([name, v]) => (
                    <tr key={name} className="border-t border-sandline/60">
                      <td className="py-1">{name}</td>
                      <td>{v.qty_needed} {v.unit}</td>
                      <td>{v.current_stock} {v.unit}</td>
                      <td className={v.shortfall > 0 ? 'text-clay font-medium' : ''}>{v.shortfall}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
