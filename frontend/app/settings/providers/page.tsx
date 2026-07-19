// frontend/app/settings/providers/page.tsx

import React, {useEffect, useState} from 'react'

export default function ProvidersSettings(){
  const [providers, setProviders] = useState<any[]>([])

  useEffect(()=>{
    fetch('/api/ai/providers').then(r=>r.json()).then(setProviders).catch(()=>setProviders([]))
  },[])

  return (
    <div style={{padding:20}}>
      <h2>AI Providers</h2>
      <p>Manage AI providers. For security, add provider API keys as repository / deployment secrets (not here). This UI shows which providers are available on the server.</p>
      <ul>
        {providers.map((p:any)=> (
          <li key={p.id} style={{marginBottom:8}}>
            <strong>{p.name}</strong> — {p.id} — requiresKey: {String(p.requiresKey)} — env: {p.envVar || '-'} — available: {String(p.available)}
          </li>
        ))}
      </ul>
      <p>To add a key, go to your repository Settings → Secrets and add the environment variable the provider needs (see env column).</p>
    </div>
  )
}
