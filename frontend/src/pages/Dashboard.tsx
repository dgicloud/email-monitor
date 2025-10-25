import { useEffect, useRef, useState } from 'react'
import { api } from '@/api'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

type Summary = {
  total: { all: number; mainlog: number; rejectlog: number; paniclog: number }
  last_hours: number
  since: string
  last: { all: number; mainlog: number; rejectlog: number; paniclog: number }
}

type SeriesPoint = { bucket: string; total: number; mainlog: number; rejectlog: number; paniclog: number }

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [series, setSeries] = useState<SeriesPoint[]>([])
  const [loading, setLoading] = useState(false)
  const timerRef = useRef<number | null>(null)

  const load = async () => {
    setLoading(true)
    const [s, t] = await Promise.all([
      api.get<Summary>('/maillog/kpi/summary?hours=24'),
      api.get<{ last_hours: number; since: string; series: SeriesPoint[] }>(
        '/maillog/kpi/timeseries?hours=24'
      ),
    ])
    setSummary(s.data)
    setSeries(t.data.series)
    setLoading(false)
  }

  useEffect(() => {
    load()
    timerRef.current = window.setInterval(load, 30000)
    return () => { if (timerRef.current) window.clearInterval(timerRef.current) }
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Dashboard</h2>
        <button onClick={load} className="px-3 py-1.5 rounded border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800 transition text-sm">Atualizar</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard title="Total" value={summary?.total.all ?? 0} sub={summary ? `últimas ${summary.last_hours}h: ${summary.last.all}` : ''} />
        <KpiCard title="Mainlog" value={summary?.total.mainlog ?? 0} sub={summary ? `últimas ${summary.last_hours}h: ${summary.last.mainlog}` : ''} />
        <KpiCard title="Rejectlog" value={summary?.total.rejectlog ?? 0} sub={summary ? `últimas ${summary.last_hours}h: ${summary.last.rejectlog}` : ''} />
        <KpiCard title="Paniclog" value={summary?.total.paniclog ?? 0} sub={summary ? `últimas ${summary.last_hours}h: ${summary.last.paniclog}` : ''} />
      </div>

      <div className="overflow-hidden rounded-xl border bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 p-4">
        <h3 className="text-sm font-medium mb-2">Volume (últimas 24h)</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={series} margin={{ left: 12, right: 12 }}>
              <defs>
                <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2563eb" stopOpacity={0.35}/>
                  <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="bucket" tickFormatter={(v)=>new Date(v).toLocaleTimeString()} minTickGap={36} />
              <YAxis allowDecimals={false} />
              <Tooltip labelFormatter={(v)=>new Date(v as string).toLocaleString()} />
              <Area type="monotone" dataKey="total" stroke="#2563eb" fillOpacity={1} fill="url(#colorTotal)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

function KpiCard({ title, value, sub }: { title: string; value: number; sub?: string }) {
  return (
    <div className="rounded-xl border bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 p-4">
      <div className="text-sm text-gray-500 dark:text-gray-400">{title}</div>
      <div className="mt-1 text-2xl font-semibold">{value.toLocaleString()}</div>
      {sub && <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">{sub}</div>}
    </div>
  )
}
