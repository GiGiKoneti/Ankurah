import { useState, useEffect } from 'react'
import BrandingLayer from './components/BrandingLayer'
import AuthLayer from './components/AuthLayer'
import Dashboard from './components/Dashboard'

export default function App() {
  const [layer, setLayer] = useState('BRANDING') // BRANDING, AUTH, MAIN

  useEffect(() => {
    if (layer === 'BRANDING') {
      const timer = setTimeout(() => setLayer('AUTH'), 3500)
      return () => clearTimeout(timer)
    }
  }, [layer])

  if (layer === 'BRANDING') return <BrandingLayer />
  if (layer === 'AUTH') return <AuthLayer onLogin={() => setLayer('MAIN')} />
  return <Dashboard />
}
