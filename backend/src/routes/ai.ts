// backend/src/routes/ai.ts

import { FastifyInstance } from 'fastify'
import { registerProvider, listProviders, chatWithProvider, detectAvailableProviders } from '../services/ai.service'
import { mockProvider } from '../providers/mock.provider'
import { openaiProvider } from '../providers/openai.provider'
import { geminiProvider } from '../providers/gemini.provider'

export default async function (fastify: FastifyInstance) {
  // register built-in providers
  try{
    registerProvider(mockProvider as any)
    registerProvider(openaiProvider as any)
    registerProvider(geminiProvider as any)
  }catch(e){ fastify.log.warn('provider register error', e) }

  fastify.get('/api/ai/providers', async (request, reply) => {
    const ps = await detectAvailableProviders()
    return ps
  })

  fastify.post('/api/ai/chat', async (request, reply) => {
    const body = request.body as any
    const provider = body.provider || 'mock'
    const prompt = body.prompt || ''
    const context = body.context || {}
    try{
      const res = await chatWithProvider(provider, prompt, context)
      return { ok:true, result: res }
    }catch(e:any){
      request.log.error(e)
      reply.code(500).send({ ok:false, error: e.message || String(e) })
    }
  })
}
