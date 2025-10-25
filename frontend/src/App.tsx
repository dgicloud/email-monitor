import { useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Logs from './pages/Logs'
import Servers from './pages/Servers'

function PrivateRoute({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem('token')
  const location = useLocation()
  if (!token) return <Navigate to="/login" state={{ from: location }} replace />
  return children
}

function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const [theme, setTheme] = useState<string>(() => localStorage.getItem('theme') || 'light')

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    localStorage.setItem('theme', theme)
  }, [theme])

  const logout = () => {
    localStorage.removeItem('token')
    navigate('/login')
  }
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-gray-100">
      <nav className="sticky top-0 z-10 backdrop-blur supports-[backdrop-filter]:bg-white/70 dark:supports-[backdrop-filter]:bg-gray-900/60 bg-white/90 dark:bg-gray-900/80 border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-4">
          <div className="flex items-center gap-2">
            <img src="/favicon.svg" alt="Logo" className="h-7 w-7" />
            <h1 className="font-semibold">Email Monitor</h1>
          </div>
          <div className="flex-1" />
          <Link to="/" className="text-sm px-3 py-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">Dashboard</Link>
          <Link to="/logs" className="text-sm px-3 py-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">Logs</Link>
          <Link to="/servers" className="text-sm px-3 py-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">Servidores</Link>
          <div className="mx-2 h-5 w-px bg-gray-200 dark:bg-gray-800" />
          <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} className="text-sm px-3 py-1.5 rounded border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800 transition">
            {theme === 'dark' ? 'Light' : 'Dark'}
          </button>
          <button onClick={logout} className="ml-2 text-sm px-3 py-1.5 rounded bg-red-600 hover:bg-red-700 text-white transition">Sair</button>
        </div>
      </nav>
      <main className="max-w-6xl mx-auto px-4 py-6">{children}</main>
    </div>
  )
}

export default function App() {
  useEffect(() => {
    document.title = 'Email Monitor'
  }, [])
  
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<PrivateRoute><Layout><Dashboard /></Layout></PrivateRoute>} />
      <Route path="/logs" element={<PrivateRoute><Layout><Logs /></Layout></PrivateRoute>} />
      <Route path="/servers" element={<PrivateRoute><Layout><Servers /></Layout></PrivateRoute>} />
    </Routes>
  )
}
