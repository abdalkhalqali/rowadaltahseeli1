import React, { useEffect, useRef } from 'react'

type Props = {
  value?: string
  language?: string
  onChange?: (v: string) => void
}

export default function Editor({ value = '', language = 'javascript', onChange }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const editorRef = useRef<any>(null)

  useEffect(() => {
    let mounted = true
    let monacoInstance: any
    const init = async () => {
      if (!containerRef.current) return
      // dynamic import so this doesn't run during SSR
      const monaco = await import('monaco-editor')
      if (!mounted) return
      monacoInstance = monaco
      editorRef.current = monaco.editor.create(containerRef.current!, {
        value: value,
        language: language,
        automaticLayout: true,
        theme: 'vs-dark',
        minimap: { enabled: false },
      })

      editorRef.current.getModel()?.onDidChangeContent(() => {
        const v = editorRef.current.getValue()
        onChange && onChange(v)
      })
    }

    init().catch((err) => {
      // fallback: render plain text into div
      if (containerRef.current) containerRef.current.innerText = value
      console.error('Failed to load monaco editor', err)
    })

    return () => {
      mounted = false
      try {
        if (editorRef.current) {
          editorRef.current.dispose()
          // dispose models if any
          const models = monacoInstance?.editor?.getModels() || []
          models.forEach((m: any) => m.dispose && m.dispose())
        }
      } catch (e) {
        // ignore
      }
    }
  }, [])

  useEffect(() => {
    // update value programmatically if editor exists and it's different
    try {
      if (editorRef.current) {
        const cur = editorRef.current.getValue()
        if (value !== undefined && value !== cur) editorRef.current.setValue(value)
      } else if (containerRef.current) {
        containerRef.current.innerText = value
      }
    } catch (e) {
      // ignore
    }
  }, [value])

  return (
    <div style={{ height: '100%', minHeight: 300, display: 'flex', flexDirection: 'column' }}>
      <div ref={containerRef} style={{ flex: 1, borderRadius: 6, overflow: 'hidden', border: '1px solid #2b2b2b' }} />
    </div>
  )
}
