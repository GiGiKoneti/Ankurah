import { useState, useEffect } from 'react'

export default function AuthLayer({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    setIsLoading(true)
    setTimeout(() => {
      onLogin()
    }, 1200)
  }

  return (
    <div className="min-h-screen bg-[#020408] flex items-center justify-center p-8 overflow-hidden selection:bg-red-500/30">
      {/* Dynamic Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-20">
         <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-red-600/10 blur-[130px] rounded-full animate-pulse" />
         <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] border border-white/5 rounded-full scale-0 opacity-0 animate-in zoom-in-150 fade-in duration-[4000ms]" />
      </div>

      <div className={`w-full max-w-[480px] relative z-10 p-1 bg-gradient-to-br from-white/10 via-transparent to-white/10 rounded-[3rem] shadow-2xl transition-all duration-1000 ${mounted ? 'translate-y-0 opacity-100 scale-100' : 'translate-y-20 opacity-0 scale-95'}`}>
        <div className="bg-black/80 backdrop-blur-3xl p-10 md:p-14 rounded-[2.9rem] flex flex-col items-center gap-12 border border-white/5 relative overflow-hidden group">
          
          {/* Top Logo and Header */}
          <div className="text-center space-y-4">
            <div className="relative inline-flex mb-4">
              <div className="absolute inset-0 bg-red-600/30 blur-[40px] rounded-full group-hover:bg-red-600/60 transition-all duration-1000" />
              <div className="relative w-20 h-20 rounded-[1.5rem] bg-zinc-950 border-2 border-white/10 flex items-center justify-center shadow-xl group-hover:scale-105 transition-transform duration-500">
                 <span className="text-3xl filter drop-shadow-2xl">🛡️</span>
              </div>
            </div>
            <div className="space-y-2">
              <h2 className="text-3xl font-black text-white tracking-tighter italic uppercase drop-shadow-md">Command Access</h2>
              <div className="flex items-center justify-center gap-3">
                 <div className="h-[1px] w-8 bg-gradient-to-r from-transparent to-red-600/50" />
                 <p className="text-zinc-500 text-[10px] font-black uppercase tracking-[0.4em] drop-shadow-sm whitespace-nowrap">Authorized Entry Only</p>
                 <div className="h-[1px] w-8 bg-gradient-to-l from-transparent to-red-600/50" />
              </div>
            </div>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="w-full space-y-6">
            <div className="space-y-2">
              <div className="relative group/input">
                 <input 
                  type="text" 
                  autoFocus
                  placeholder="OFFICER CREDENTIALS"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  className="w-full bg-[#050505] border-2 border-white/5 rounded-2xl px-6 py-5 text-sm font-bold text-white transition-all duration-500 focus:outline-none focus:border-red-600/40 focus:bg-black placeholder:text-zinc-700 placeholder:text-[10px] placeholder:font-black placeholder:tracking-[0.2em] shadow-inner"
                />
                <div className="absolute right-6 top-1/2 -translate-y-1/2 opacity-20 pointer-events-none group-focus-within/input:opacity-100 transition-opacity">👤</div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="relative group/input">
                 <input 
                  type="password" 
                  placeholder="SECURE ACCESS TOKEN"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full bg-[#050505] border-2 border-white/5 rounded-2xl px-6 py-5 text-sm font-bold text-white transition-all duration-500 focus:outline-none focus:border-red-600/40 focus:bg-black placeholder:text-zinc-700 placeholder:text-[10px] placeholder:font-black placeholder:tracking-[0.2em] shadow-inner"
                />
                <div className="absolute right-6 top-1/2 -translate-y-1/2 opacity-20 pointer-events-none group-focus-within/input:opacity-100 transition-opacity">🔑</div>
              </div>
            </div>

            <button 
              type="submit"
              disabled={isLoading}
              className="w-full relative group/btn"
            >
              <div className="absolute inset-0 bg-red-600 blur-[20px] rounded-2xl opacity-0 group-hover/btn:opacity-40 transition-opacity duration-500" />
              <div className="relative bg-red-600 hover:bg-red-500 text-white font-black py-5 rounded-2xl transition-all duration-300 shadow-[0_10px_40px_-10px_rgba(220,38,38,0.5)] active:scale-[0.98] disabled:opacity-50 disabled:grayscale flex items-center justify-center gap-4 text-sm tracking-[0.2em] border border-red-400/20">
                {isLoading ? (
                  <div className="w-5 h-5 border-3 border-white/20 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                     LOGIN_TO_CONSOLE
                     <div className="w-8 h-8 rounded-lg bg-black/10 flex items-center justify-center group-hover/btn:bg-white/10">
                        <span className="text-xs">▶️</span>
                     </div>
                  </>
                )}
              </div>
            </button>
          </form>

          {/* Footer Metadata */}
          <div className="flex flex-col items-center gap-6 pt-4">
             <div className="h-[1px] w-32 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
             <div className="text-center space-y-3 opacity-30 group-hover:opacity-60 transition-opacity duration-1000">
                <p className="text-[9px] text-zinc-500 font-mono font-black tracking-[0.4em] uppercase leading-relaxed">
                  ANKURAH NETWORK • SECURE NODE 0X-82 <br/>
                  ENCRYPTION: AES-256-GCM_ACTIVE
                </p>
                <div className="flex items-center justify-center gap-4 text-[8px] font-black text-zinc-700 tracking-[0.3em] uppercase">
                   <div className="flex items-center gap-2">
                      <div className="w-1 h-1 rounded-full bg-emerald-500" />
                      VPN_UP
                   </div>
                   <div className="flex items-center gap-2">
                      <div className="w-1 h-1 rounded-full bg-emerald-500" />
                      FIREWALL_ACTIVE
                   </div>
                </div>
             </div>
          </div>
        </div>
      </div>

      {/* Extreme Decorative Elements */}
      <div className="fixed top-8 left-8 p-6 border-l-2 border-white/5 hidden xl:block opacity-20 hover:opacity-100 transition-opacity duration-1000">
         <div className="space-y-4">
            <div className="h-10 w-1 bg-red-600" />
            <div className="text-[10px] font-black text-white/50 space-y-1">
               <p>LOC_SYST_OK</p>
               <p>KERN_8.2.1</p>
               <p>USER_ROOT_ACCESS</p>
            </div>
         </div>
      </div>
    </div>
  )
}
