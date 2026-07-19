// frontend/app/chat/ChatPanel.tsx

import React, {useState} from 'react'
import ProviderSelector from '../../components/ProviderSelector'

export default function ChatPanel(){
  const [provider,setProvider] = useState('mock')
  const [prompt,setPrompt] = useState('')
  const [messages,setMessages] = useState<any[]>([])
  const [loading,setLoading] = useState(false)

  const send = async ()=>{
    if(!prompt) return
    setLoading(true)
    const res = await fetch('/api/ai/chat',{method:'POST',headers:{'Content-Type':'application/json'},body: JSON.stringify({ provider, prompt })})
    const j = await res.json()
    if(j.ok){
      setMessages(m=>[...m, {from:'user', text:prompt}, {from:'ai', text: j.result.text}])
      setPrompt('')
    }else{
      setMessages(m=>[...m, {from:'system', text: 'Error: '+(j.error||'unknown')}])
    }
    setLoading(false)
  }

  return (
    <div style={{padding:12,border:'1px solid #ddd'}}>
      <div style={{display:'flex',gap:8,alignItems:'center',marginBottom:8}}>
        <ProviderSelector value={provider} onChange={setProvider} />
        <button onClick={send} disabled={loading}>Send</button>
      </div>
      <textarea rows={4} value={prompt} onChange={e=>setPrompt(e.target.value)} style={{width:'100%'}} />
      <div style={{marginTop:12}}>
        {messages.map((m,i)=> (
          <div key={i} style={{padding:8,background:m.from==='ai'? '#eef':'#f7f7f7',marginBottom:8}}>
            <strong>{m.from}</strong>
            <div style={{whiteSpace:'pre-wrap'}}>{m.text}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
