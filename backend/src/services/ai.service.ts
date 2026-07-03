// backend/src/services/ai.service.ts

type ChatResult = { text: string }

type Provider = {
  id: string
  name: string
  requiresKey: boolean
  envVar?: string
  chat: (prompt: string, context?: any) => Promise<ChatResult>
}

const providers: Record<string, Provider> = {}

export function registerProvider(p: Provider) {
  providers[p.id] = p
}

export function listProviders() {
  return Object.values(providers).map(p => ({ id: p.id, name: p.name, requiresKey: p.requiresKey, envVar: p.envVar }))
}

export async function chatWithProvider(providerId: string, prompt: string, context?: any) {
  const p = providers[providerId]
  if (!p) throw new Error(`unknown provider ${providerId}`)
  return p.chat(prompt, context)
}

export async function detectAvailableProviders(){
  // mark which providers have keys configured by checking process.env
  return listProviders().map(p => ({...p, available: p.envVar ? !!process.env[(p.envVar)] : true}))
}
