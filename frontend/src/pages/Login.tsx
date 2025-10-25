import { FormEvent, useState } from 'react'
import { api } from '@/api'
import toast from 'react-hot-toast'

export default function Login() {
  const [email, setEmail] = useState('admin@example.com')
  const [password, setPassword] = useState('admin123')
  const [error, setError] = useState<string | null>(null)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const res = await api.post('/api/login', { email, password })
      localStorage.setItem('token', res.data.access_token)
      toast.success('Login realizado com sucesso')
      window.location.href = '/'
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Falha ao autenticar')
      toast.error(err?.response?.data?.detail || 'Falha ao autenticar')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-gray-100">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto h-12 w-12 rounded bg-blue-600" />
          <h2 className="mt-3 text-xl font-semibold">Acessar painel</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">Entre com suas credenciais</p>
        </div>
        <form onSubmit={onSubmit} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 p-6 rounded-xl shadow-sm space-y-4">
          {error && <div className="text-red-700 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 px-3 py-2 rounded text-sm">{error}</div>}
          <div>
            <label className="block text-sm">Email</label>
            <input className="mt-1 w-full border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" value={email} onChange={e=>setEmail(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm">Senha</label>
            <input type="password" className="mt-1 w-full border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" value={password} onChange={e=>setPassword(e.target.value)} />
          </div>
          <button className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg transition">Entrar</button>
        </form>
      </div>
    </div>
  )
}
