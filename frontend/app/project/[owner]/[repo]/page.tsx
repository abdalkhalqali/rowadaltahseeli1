import React, {useEffect, useState} from 'react'
import Editor from '../../../components/Editor'
import RepoTree from '../../../components/RepoTree'

export default function ProjectPage({params}:{params:{owner:string,repo:string}}) {
  const {owner, repo} = params
  const [items, setItems] = useState<any[]>([])
  const [path, setPath] = useState<string | null>(null)
  const [content, setContent] = useState<string>('')
  const [sha, setSha] = useState<string | undefined>(undefined)
  const [status, setStatus] = useState<string>('')

  useEffect(()=>{
    fetch(`/api/tree?owner=${owner}&repo=${repo}`)
      .then(r=>r.json()).then(data=>{
        if(data.items) setItems(data.items)
      }).catch(err=>console.error(err))
  },[owner,repo])

  const openFile = async (p:string)=>{
    setStatus('loading')
    const res = await fetch(`/api/file?owner=${owner}&repo=${repo}&path=${encodeURIComponent(p)}`)
    const j = await res.json()
    if(j.content!==undefined){
      setPath(p)
      setContent(j.content)
      setSha(j.sha)
      setStatus('ready')
    }else{
      setStatus('error')
    }
  }

  const saveFile = async ()=>{
    if(!path) return
    setStatus('saving')
    const body = { owner, repo, path, content, message: `Edit ${path} via AI assistant`, sha }
    const res = await fetch('/api/file', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)})
    const j = await res.json()
    if(j.ok){ setStatus('saved'); setSha(j.commit?.sha ?? sha) }
    else { setStatus('save-error') }
  }

  return (
    <div style={{padding:20}}>
      <h2>Project: {owner}/{repo}</h2>
      <div style={{display:'flex',gap:12}}>
        <div style={{width:320, border:'1px solid #ddd', padding:8}}>
          <h4>Files</h4>
          <RepoTree items={items} onOpen={openFile} />
        </div>
        <div style={{flex:1, border:'1px solid #ddd', padding:8}}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:8}}>
            <div>{path ?? 'No file opened'}</div>
            <div>
              <button onClick={saveFile} disabled={!path} style={{padding:'6px 10px',marginRight:8}}>Save</button>
              <span>{status}</span>
            </div>
          </div>
          <Editor value={content} onChange={v=>setContent(v)} />
        </div>
      </div>
    </div>
  )
}
