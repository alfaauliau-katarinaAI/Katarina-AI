'use strict';
const express = require('express');
const crypto = require('node:crypto');
const fs = require('node:fs');
if (!globalThis.crypto) globalThis.crypto = crypto.webcrypto;
const {McpServer} = require('@modelcontextprotocol/sdk/server/mcp.js');
const {StreamableHTTPServerTransport} = require('@modelcontextprotocol/sdk/server/streamableHttp.js');
const {z} = require('zod');

const PORT = Number(process.env.PORT || 47832);
const HOST = process.env.MCP_BIND_HOST || '127.0.0.1';
function secret(name) {
  if (process.env[name]) return process.env[name].trim();
  const file = process.env[name+'_FILE'];
  return file ? fs.readFileSync(file,'utf8').trim() : '';
}
const CONNECTOR_KEY = secret('CONNECTOR_KEY');
const OPENAI_API_KEY = secret('OPENAI_API_KEY');
const OPENAI_MODEL = (process.env.OPENAI_MODEL || 'gpt-5-mini').trim();
if (!/^[a-fA-F0-9]{64}$/.test(CONNECTOR_KEY)) {
  console.error('STARTUP_ERROR: CONNECTOR_KEY must be a random 64-character hex secret');
  process.exit(1);
}

const app = express();
app.disable('x-powered-by');
app.use(express.json({limit:'48kb'}));
app.use((req,res,next)=>{res.set('Cache-Control','no-store');res.set('X-Content-Type-Options','nosniff');next();});

let active = 0;
const recentCalls = [];
function allowed(req) {
  const incoming = String(req.get('X-Connector-Key') || '');
  const received = Buffer.from(incoming,'utf8');
  const expected = Buffer.from(CONNECTOR_KEY,'utf8');
  return received.length === expected.length && crypto.timingSafeEqual(received,expected);
}
function authenticate(req,res,next) {
  if (!allowed(req)) return res.status(401).json({error:'AUTH_REQUIRED'});
  next();
}
function result(text,isError=false) {
  return {content:[{type:'text',text:String(text).slice(0,16000)}],isError};
}
function makeServer() {
  const server = new McpServer(
    {name:'katarina-claude-openai-bridge',version:'1.0.0'},
    {instructions:'Use this to request an independent answer from an OpenAI API model, NOT the current ChatGPT conversation or saved memory. This connector does not control the VPS or execute code.'}
  );
  server.tool('connector_status',
    'Check whether the OpenAI API connector is configured. No API call or charges.',
    {},
    async()=>result(JSON.stringify({
      bridge:'online', openai_api_configured:!!OPENAI_API_KEY,
      model:OPENAI_MODEL, capabilities:['ask_openai'], current_chatgpt_session_access:false
    }))
  );
  server.tool('ask_openai',
    'Ask a separate OpenAI API model to analyze technical questions, Katarina trading code snippets or test results. This does not access ChatGPT history, VPS files or trading accounts. API billing may apply.',
    {
      question:z.string().min(1).max(12000).describe('Specific question to ask the OpenAI model'),
      context:z.string().max(16000).optional().describe('Optional supporting context, sanitized code or test output. Do not send secrets.'),
    },
    async({question,context})=>{
      if (!OPENAI_API_KEY) return result('OPENAI_API_KEY_NOT_CONFIGURED: The owner must add OPENAI_API_KEY in Render environment settings.',true);
      const now=Date.now();
      while (recentCalls.length && now-recentCalls[0]>60000) recentCalls.shift();
      if (active>=2 || recentCalls.length>=8) return result('RATE_LIMITED: Try again shortly.',true);
      active++;
      recentCalls.push(now);
      const controller=new AbortController();
      const timer=setTimeout(()=>controller.abort(),65000);
      try{
        const response=await fetch('https://api.openai.com/v1/responses',{
          method:'POST',
          headers:{
            'Authorization': 'Bearer '+OPENAI_API_KEY,
            'Content-Type':'application/json'
          },
          signal:controller.signal,
          body:JSON.stringify({
            model:OPENAI_MODEL,
            store:false,
            max_output_tokens:2400,
            instructions:'Provide an accurate, concise independent technical answer. Explain uncertainty and limitations. Never claim to have inspected the user VPS, broker or GitHub unless evidence is supplied in the input. Do not disclose secrets. Do not recommend enabling live trading without explicit owner authorization.',
            input:context ? 'Context:\n'+context+'\n\nQuestion:\n'+question : question
          })
        });
        const payload=await response.json().catch(()=>null);
        if(!response.ok) return result(JSON.stringify({
          error:'OPENAI_API_REQUEST_FAILED',http_status:response.status,
          code:payload?.error?.code || null,
          message:String(payload?.error?.message || 'Check model access, API key and billing.').slice(0,400)
        }),true);
        const parts=[];
        if(typeof payload?.output_text==='string') parts.push(payload.output_text);
        if(!parts.length) for(const item of payload?.output||[]) {
          for(const piece of item.content||[]) if(piece.type==='output_text' && typeof piece.text==='string') parts.push(piece.text);
        }
        return result(JSON.stringify({
          model:payload?.model || OPENAI_MODEL,
          response:parts.join('\n').slice(0,14000) || '[No text returned]',
          source:'OpenAI API (separate from this ChatGPT conversation)',
          response_id:payload?.id || null
        }));
      }catch(e){
        return result(JSON.stringify({error:e?.name==='AbortError'?'OPENAI_TIMEOUT':'OPENAI_NETWORK_ERROR'}),true);
      }finally{
        clearTimeout(timer);
        active--;
      }
    }
  );
  return server;
}
app.get('/health',(req,res)=>res.json({status:'ok',transport:'MCP Streamable HTTP',openai_ready:!!OPENAI_API_KEY}));
app.use('/mcp',authenticate);
app.post('/mcp',async(req,res)=>{
  const server=makeServer();
  const transport=new StreamableHTTPServerTransport({sessionIdGenerator:undefined,enableJsonResponse:true});
  res.on('close',()=>{transport.close().catch(()=>{});server.close().catch(()=>{});});
  try {
    await server.connect(transport);
    await transport.handleRequest(req,res,req.body);
  }catch(e) {
    console.error('MCP_TRANSPORT_ERROR',e?.name||'unknown');
    if(!res.headersSent) res.status(500).json({error:'MCP_TRANSPORT_ERROR'});
  }
});
app.get('/mcp',(req,res)=>res.status(405).set('Allow','POST').end());
app.delete('/mcp',(req,res)=>res.status(405).set('Allow','POST').end());
app.all('*',(req,res)=>res.status(404).end());
app.listen(PORT,HOST,()=>console.log('MCP connector running on configured port'));
