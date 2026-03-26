import { useState } from 'react'

export default function AuthLayer({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    setIsLoading(true)
    setTimeout(() => {
      onLogin()
    }, 1500)
  }

  return (
    <div className="min-h-screen bg-neutral-950 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(185,28,28,0.05),transparent_50%)]" />
      
      <div className="w-full max-w-[400px] relative">
        {/* Header */}
        <div className="text-center mb-10 space-y-2">
          <div className="inline-flex p-3 rounded-2xl bg-red-600/10 border border-red-500/20 mb-4">
             <span className="text-2xl">🛡️</span>
          </div>
          <h2 className="text-2xl font-black text-white tracking-tight italic">COMMAND ACCESS</h2>
          <p className="text-zinc-500 text-xs font-bold uppercase tracking-widest">Authorized Personnel Only</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest ml-1">Officer Credentials</label>
            <input 
              type="text" 
              placeholder="Username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full bg-zinc-900/50 border border-white/5 rounded-xl px-5 py-4 text-white focus:outline-none focus:border-red-500/50 transition-all placeholder:text-zinc-700"
            />
          </div>
          <div className="space-y-1.5">
            <input 
              type="password" 
              placeholder="Secure Token"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full bg-zinc-900/50 border border-white/5 rounded-xl px-5 py-4 text-white focus:outline-none focus:border-red-500/50 transition-all placeholder:text-zinc-700"
            />
          </div>

          <button 
            type="submit"
            disabled={isLoading}
            className="w-full bg-red-600 hover:bg-red-500 text-white font-black py-4 rounded-xl transition-all shadow-xl shadow-red-950/20 active:scale-[0.98] disabled:opacity-50 disabled:grayscale flex items-center justify-center gap-3"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            ) : (
              'INITIALIZE LINK'
            )}
          </button>
        </form>

        <p className="mt-12 text-center text-[9px] text-zinc-600 font-mono uppercase tracking-[0.3em] leading-relaxed">
          ANKURAH NETWORK • SECURE NODE 082<br/>
          ENCRYPTION ACTIVE: AES-256-GCM
        </p>
      </div>
    </div>
  )
}
