import React from 'react'

type TreeItem = {
  name: string
  path: string
  type: string
}

export default function RepoTree({ items, onOpen }:{items:TreeItem[], onOpen:(path:string)=>void }){
  return (
    <div style={{padding:8}}>
      <ul style={{listStyle:'none',padding:0,margin:0}}>
        {items.map(it=> (
          <li key={it.path} style={{padding:'6px 4px',cursor:'pointer',borderBottom:'1px solid #f0f0f0'}} onClick={()=>{ if(it.type==='file') onOpen(it.path) }}>
            <strong style={{marginRight:8}}>{it.type==='dir'? '📁' : '📄'}</strong>
            {it.name}
          </li>
        ))}
      </ul>
    </div>
  )
}
