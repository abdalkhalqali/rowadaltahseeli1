import React, {useEffect, useRef} from 'react'

export default function Editor({value}:{value?:string}){
  const ref = useRef<HTMLDivElement|null>(null)
  useEffect(()=>{
    // placeholder: in real app we init monaco here
    if(ref.current) ref.current.innerText = value ?? '// editor placeholder'
  },[value])
  return <div ref={ref} style={{minHeight:300,background:'#0b0b0b',color:'#e6e6e6',padding:12,fontFamily:'monospace'}} />
}
