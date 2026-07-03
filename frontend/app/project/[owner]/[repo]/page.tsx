import React from 'react'

export default function ProjectPage({params}:{params:{owner:string,repo:string}}) {
  const {owner, repo} = params
  return (
    <div style={{padding:20}}>
      <h2>Project: {owner}/{repo}</h2>
      <p>Files tree and editor will appear here (scaffold).</p>
      <div style={{display:'flex',gap:12}}>
        <div style={{width:320, border:'1px solid #ddd', padding:8}}>Repo Tree (placeholder)</div>
        <div style={{flex:1, border:'1px solid #ddd', padding:8}}>
          <iframe title="Editor" style={{width:'100%',height:400,border:0}} src="about:blank" />
        </div>
      </div>
    </div>
  )
}
