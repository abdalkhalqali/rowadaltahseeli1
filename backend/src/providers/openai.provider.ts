// backend/src/providers/openai.provider.ts

import fetch from 'node-fetch'

export const openaiProvider = {
  id: 'openai',
  name: 'OpenAI',
  requiresKey: true,
  envVar: 'OPENAI_API_KEY',
  chat: async (prompt: string, _context?: any) => {
    const key = process.env.OPENAI_API_KEY
    if(!key) throw new Error('OPENAI_API_KEY not configured')
    // Minimal ChatCompletion request to OpenAI v1 (gpt-4/3.5). You may adjust model.
    const model = process.env.OPENAI_MODEL || 'gpt-4o-mini'
    const resp = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
      body: JSON.stringify({ model, messages: [{ role: 'user', content: prompt }], max_tokens: 1000 })
    })
    if(!resp.ok){
      const txt = await resp.text()
      throw new Error(`OpenAI error: ${resp.status} ${txt}`)
    }
    const j = await resp.json()
    const text = j.choices?.[0]?.message?.content ?? ''
    return { text }
  }
}
