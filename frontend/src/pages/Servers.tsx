import { useEffect, useState } from 'react'
import { api } from '@/api'

type Server = { id: number; name: string; api_key: string; created_at: string }

export default function Servers() {
  const [servers, setServers] = useState<Server[]>([])
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  const fetchServers = async () => {
    const res = await api.get<Server[]>('/servers')
    setServers(res.data)
  }
  useEffect(() => { fetchServers() }, [])

  const register = async () => {
    setError(null)
    try {
      const res = await api.get<Server>('/servers/register', { params: { name } })
      setName('')
      await fetchServers()
      alert(`Servidor criado. api_key: ${res.data.api_key}`)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao registrar')
    }
  }

  const remove = async (id: number) => {
    if (!confirm('Remover este servidor? Os logs associados serão excluídos.')) return
    try {
      await api.delete(`/servers/${id}`)
      await fetchServers()
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Erro ao remover')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Servidores</h2>
        <div className="flex gap-2">
          <input placeholder="Nome do servidor" value={name} onChange={e=>setName(e.target.value)} className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <button onClick={register} className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white rounded px-4 py-2 transition">Registrar</button>
        </div>
      </div>
      {error && <div className="text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded text-sm">{error}</div>}
      <div className="overflow-hidden rounded-xl border bg-white">
        <table className="min-w-full">
          <thead className="bg-gray-50 text-gray-600 text-sm">
            <tr>
              <th className="p-3 font-medium text-left">ID</th>
              <th className="p-3 font-medium text-left">Nome</th>
              <th className="p-3 font-medium text-left">API Key</th>
              <th className="p-3 font-medium text-left">Criado em</th>
              <th className="p-3 font-medium text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {servers.map(s => (
              <tr key={s.id} className="hover:bg-gray-50">
                <td className="p-3">{s.id}</td>
                <td className="p-3 font-medium">{s.name}</td>
                <td className="p-3 font-mono text-xs break-all">{s.api_key}</td>
                <td className="p-3">{new Date(s.created_at).toLocaleString()}</td>
                <td className="p-3 text-right">
                  <button onClick={()=>remove(s.id)} className="inline-flex items-center gap-1 px-3 py-1.5 rounded border border-red-200 text-red-700 hover:bg-red-50 transition">Remover</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
