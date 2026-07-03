// backend/src/providers/mock.provider.ts

import { ChatResult } from '../types'

export const mockProvider = {
  id: 'mock',
  name: 'Mock (no-key)',
  requiresKey: false,
  envVar: undefined,
  chat: async (prompt: string) : Promise<any> => {
    // very simple echo behaviour for development/testing
    return { text: `Mock response — you asked: ${prompt.slice(0,400)}` }
  }
}
