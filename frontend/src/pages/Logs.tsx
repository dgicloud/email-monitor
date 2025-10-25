import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '@/api'
import { useSearchParams } from 'react-router-dom'

type LogItem = {
  id: number
  server_id: number
  kind: string
  sender?: string
  recipient?: string
  status?: string
  message?: string
  message_id?: string
  timestamp: string
}

export default function Logs() {
  const [items, setItems] = useState<LogItem[]>([])
  const [servers, setServers] = useState<string[]>([])
  const [searchParams, setSearchParams] = useSearchParams()
  const [server, setServer] = useState(searchParams.get('server') || '')
  const [email, setEmail] = useState(searchParams.get('email') || '')
  const [kind, setKind] = useState(searchParams.get('kind') || '')
  const [status, setStatus] = useState(searchParams.get('status') || '')
  const [limit, setLimit] = useState<number>(parseInt(searchParams.get('limit') || '50') || 50)
  const [page, setPage] = useState<number>(parseInt(searchParams.get('page') || '1') || 1)
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const timerRef = useRef<number | null>(null)
  const [showModal, setShowModal] = useState<LogItem | null>(null)

  const fetchData = async () => {
    setLoading(true)
    const params: any = { limit, offset: (page - 1) * limit }
    if (server) params.server = server
    if (email) params.email = email
    if (kind) params.kind = kind
    if (status) params.status = status
    const res = await api.get<LogItem[]>('/api/maillog', { params })
    setItems(res.data)
    setLoading(false)
  }

  // servers list for dropdown
  useEffect(() => {
    api.get<{ id:number; name:string }[]>('/api/servers').then(r => setServers(r.data.map(s=>s.name)))
  }, [])

  // initial load
  useEffect(() => { fetchData() }, [])

  // auto refresh every 30s
  useEffect(() => {
    if (autoRefresh) {
      timerRef.current = window.setInterval(fetchData, 30000)
    }
    return () => { if (timerRef.current) window.clearInterval(timerRef.current) }
  }, [autoRefresh, server, email, kind, status])

  // sync filters to URL + debounce fetch
  useEffect(() => {
    const params = new URLSearchParams()
    if (server) params.set('server', server)
    if (email) params.set('email', email)
    if (kind) params.set('kind', kind)
    if (status) params.set('status', status)
    params.set('limit', String(limit))
    params.set('page', String(page))
    setSearchParams(params, { replace: true })
    const t = setTimeout(fetchData, 400)
    return () => clearTimeout(t)
  }, [server, email, kind, status, limit, page])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Logs</h2>
        <div className="flex items-center gap-3 text-sm">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={autoRefresh} onChange={e=>setAutoRefresh(e.target.checked)} />
            Auto-refresh 30s
          </label>
          <button onClick={fetchData} className="px-3 py-1.5 rounded border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800 transition">Atualizar</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-6 gap-2">
        <select className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" value={server} onChange={e=>{setPage(1); setServer(e.target.value)}}>
          <option value="">Todos servidores</option>
          {servers.map(s=> <option key={s} value={s}>{s}</option>)}
        </select>
        <input placeholder="Email" className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" value={email} onChange={e=>{setPage(1); setEmail(e.target.value)}} />
        <select className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" value={kind} onChange={e=>{setPage(1); setKind(e.target.value)}}>
          <option value="">Todos tipos</option>
          <option value="mainlog">mainlog</option>
          <option value="rejectlog">rejectlog</option>
          <option value="paniclog">paniclog</option>
        </select>
        <select className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" value={status} onChange={e=>{setPage(1); setStatus(e.target.value)}}>
          <option value="">Todos status</option>
          <option value="accepted">accepted</option>
          <option value="rejected">rejected</option>
          <option value="deferred">deferred</option>
          <option value="failed">failed</option>
        </select>
        <select className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" value={String(limit)} onChange={e=>{setPage(1); setLimit(parseInt(e.target.value))}}>
          <option value="25">25</option>
          <option value="50">50</option>
          <option value="100">100</option>
        </select>
        <button className="bg-blue-600 hover:bg-blue-700 text-white rounded px-4 transition" onClick={()=>{setPage(1); fetchData()}}>Filtrar</button>
      </div>

      <div className="overflow-hidden rounded-xl border bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800">
        <table className="min-w-full">
          <thead className="bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-100 text-sm">
            <tr className="text-left">
              <th className="p-3 font-semibold">Data</th>
              <th className="p-3 font-semibold">Tipo</th>
              <th className="p-3 font-semibold">De</th>
              <th className="p-3 font-semibold">Para</th>
              <th className="p-3 font-semibold">Status</th>
              <th className="p-3 font-semibold">Mensagem</th>
            </tr>
          </thead>
          <tbody className="divide-y dark:divide-gray-800 text-gray-900 dark:text-gray-100">
            {loading && (
              <tr><td className="p-6 text-center text-sm text-gray-500" colSpan={6}>Carregando...</td></tr>
            )}
            {!loading && items.length === 0 && (
              <tr><td className="p-6 text-center text-sm text-gray-500" colSpan={6}>Nenhum registro encontrado</td></tr>
            )}
            {!loading && items.map(i => (
              <tr key={i.id} className="hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer" onClick={()=>setShowModal(i)}>
                <td className="p-3 whitespace-nowrap">{new Date(i.timestamp).toLocaleString()}</td>
                <td className="p-3 uppercase tracking-wide text-xs text-gray-600 dark:text-gray-300">{i.kind}</td>
                <td className="p-3">{i.sender}</td>
                <td className="p-3">{i.recipient}</td>
                <td className="p-3">
                  <span className={
                    `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ` +
                    (i.status === 'accepted' ? 'bg-green-100 text-green-800' :
                     i.status === 'rejected' ? 'bg-red-100 text-red-800' :
                     i.status === 'deferred' ? 'bg-amber-100 text-amber-800' :
                     i.status === 'failed' ? 'bg-red-200 text-red-900' : 'bg-gray-100 text-gray-800')
                  }>
                    {i.status || '—'}
                  </span>
                </td>
                <td className="p-3 max-w-xl truncate">
                  <span className="underline decoration-dotted" title={i.message}>{i.message}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm">
        <div>Página {page}</div>
        <div className="flex items-center gap-2">
          <button disabled={page<=1} onClick={()=>setPage(p=>Math.max(1, p-1))} className="px-3 py-1.5 rounded border border-gray-200 dark:border-gray-800 disabled:opacity-50">Anterior</button>
          <button disabled={items.length < limit} onClick={()=>setPage(p=>p+1)} className="px-3 py-1.5 rounded border border-gray-200 dark:border-gray-800 disabled:opacity-50">Próxima</button>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={()=>setShowModal(null)} />
          <div className="relative w-full max-w-2xl bg-white text-gray-900 rounded-xl border border-gray-200 p-4 shadow-lg">
            <h3 className="text-lg font-semibold mb-3">Log #{showModal.id}</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-gray-600">Data:</span> {new Date(showModal.timestamp).toLocaleString()}</div>
              <div><span className="text-gray-600">Tipo:</span> {showModal.kind}</div>
              <div><span className="text-gray-600">De:</span> {showModal.sender}</div>
              <div><span className="text-gray-600">Para:</span> {showModal.recipient}</div>
              <div><span className="text-gray-600">Status:</span> {showModal.status}</div>
              <div className="col-span-2"><span className="text-gray-600">Message-ID:</span> {showModal.message_id}</div>
              <div className="col-span-2"><span className="text-gray-600">Mensagem:</span>
                <pre className="mt-1 whitespace-pre-wrap break-words bg-gray-50 text-gray-800 p-3 rounded border border-gray-200 text-xs">{showModal.message}</pre>
              </div>
            </div>
            <div className="mt-4 text-right">
              <button onClick={()=>setShowModal(null)} className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white">Fechar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
