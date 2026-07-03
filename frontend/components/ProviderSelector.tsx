// frontend/components/ProviderSelector.tsx

import React, {useEffect, useState} from 'react'

export default function ProviderSelector({value,onChange}:{value:string,onChange:(v:string)=>void}){
  const [providers,setProviders] = useState<any[]>([])
  useEffect(()=>{
    fetch('/api/ai/providers').then(r=>r.json()).then(setProviders).catch(()=>setProviders([]))
  },[])
  return (
    <select value={value} onChange={e=>onChange(e.target.value)}>
      {providers.map(p=> <option key={p.id} value={p.id}>{p.name}{p.available? ' (available)':''}</option>)}
    </select>
  )
}
