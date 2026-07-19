// backend/src/index.ts

import Fastify from 'fastify'
import cors from 'fastify-cors'
import dotenv from 'dotenv'
import {Octokit} from '@octokit/rest'

dotenv.config()

const fastify = Fastify({logger:true})
fastify.register(cors, {origin:true})

const GITHUB_TOKEN = process.env.GITHUB_TOKEN || ''
const octokit = new Octokit({auth: GITHUB_TOKEN})

fastify.get('/health', async ()=>({ok:true}))

// List public repos for the authenticated user
fastify.get('/api/repos', async (request, reply)=>{
  try{
    const resp = await octokit.rest.repos.listForAuthenticatedUser({per_page:100})
    return resp.data.map(r=>({name:r.name,full_name:r.full_name,private:r.private}))
  }catch(e){
    request.log.error(e)
    reply.code(500).send({error:'github list failed'})
  }
})

// Get tree (list files/directories) for a path
fastify.get('/api/tree', async (request, reply)=>{
  const query = request.query as any
  const {owner, repo, path} = query
  try{
    const resp = await octokit.rest.repos.getContent({owner, repo, path: path || ''})
    // @ts-ignore
    if(!Array.isArray(resp.data)){
      // single file
      return reply.code(400).send({error:'path is a file'})
    }
    // @ts-ignore
    const items = resp.data.map((item:any)=>({
      name: item.name,
      path: item.path,
      type: item.type, // file or dir
      size: item.size || 0,
    }))
    return {items}
  }catch(e:any){
    request.log.error(e)
    reply.code(404).send({error:e.message||'not found'})
  }
})

// Get file content
fastify.get('/api/file', async (request, reply)=>{
  const query = request.query as any
  const {owner, repo, path, ref} = query
  try{
    const resp = await octokit.rest.repos.getContent({owner, repo, path})
    // handle file content (base64)
    // For scaffold: return raw if possible
    // @ts-ignore
    if(Array.isArray(resp.data)) return reply.code(400).send({error:'path is a directory'})
    // @ts-ignore
    const content = Buffer.from(resp.data.content,'base64').toString('utf8')
    // @ts-ignore
    return {content, sha: resp.data.sha, encoding: resp.data.encoding}
  }catch(e:any){
    request.log.error(e)
    reply.code(404).send({error:e.message||'not found'})
  }
})

// Update file (single-file commit via GitHub Contents API)
fastify.post('/api/file', async (request, reply)=>{
  const body = request.body as any
  const {owner, repo, path, content, message, branch, sha} = body
  try{
    const resp = await octokit.rest.repos.createOrUpdateFileContents({
      owner, repo, path,
      message: message || 'update via ai-assistant',
      content: Buffer.from(content,'utf8').toString('base64'),
      branch: branch || undefined,
      sha: sha || undefined
    })
    return {ok:true,commit:resp.data.commit}
  }catch(e:any){
    request.log.error(e)
    reply.code(500).send({error:e.message||'write failed'})
  }
})

// register AI routes (providers, chat)
import aiRoutes from './routes/ai'
fastify.register(aiRoutes)

const start = async ()=>{
  try{ await fastify.listen({port:4000,host:'0.0.0.0'}) }catch(e){
    fastify.log.error(e); process.exit(1)
  }
}
start()
