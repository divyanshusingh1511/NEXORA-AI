import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Activity, Bot, ChevronDown, ChevronRight, CircleHelp, Code2, Copy, Cpu, Gauge, Menu, MessageSquarePlus, PanelLeftClose, Plus, Send, Settings2, ShieldCheck, Sparkles, Terminal, Zap } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
type Meta = {resolution_source:string;model:string;latency_ms:number;input_tokens:number;output_tokens:number;key_id:string|null;fallback_attempts:number};
type Message = {role:'user'|'assistant';content:string;metadata?:Meta};
type Session = {id:string;title:string};
const newId = () => 's-' + crypto.randomUUID().slice(0,8);
const prompts = ['Explain how automatic failover works','Design a resilient cloud architecture','Help me debug a Python API'];

export default function App(){
  const [session,setSession]=useState(newId);
  const [sessions,setSessions]=useState<Session[]>([]);
  const [messages,setMessages]=useState<Message[]>([]);
  const [input,setInput]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [panel,setPanel]=useState<'chat'|'reliability'|'playground'>('chat');
  const [systemPrompt,setSystemPrompt]=useState('');
  const [showPrompt,setShowPrompt]=useState(false);
  const [sidebar,setSidebar]=useState(true);
  const [expanded,setExpanded]=useState<number[]>([]);
  const [sim,setSim]=useState('');
  const [health,setHealth]=useState<any>(null);
  const [stats,setStats]=useState({requests:0,cache:0,live:0,latency:0});
  const endRef=useRef<HTMLDivElement>(null);
  useEffect(()=>{fetch(API+'/health').then(r=>r.json()).then(setHealth).catch(()=>setHealth(null));},[]);
  useEffect(()=>{endRef.current?.scrollIntoView({behavior:'smooth'});},[messages,busy]);
  const startNew=()=>{const id=newId();setSession(id);setMessages([]);setError('');setPanel('chat');};
  const loadSession=async(id:string)=>{try{const r=await fetch(`${API}/sessions/${id}/messages`);if(!r.ok)throw new Error('Could not load conversation');const d=await r.json();setSession(id);setMessages(d.messages);setPanel('chat');setError('');}catch(e:any){setError(e.message);}};
  const send=async(text=input,header?:string)=>{
    if(!text.trim()||busy)return;
    setError('');setInput('');setBusy(true);
    setMessages(m=>[...m,{role:'user',content:text}]);
    try{
      const headers:Record<string,string>={'Content-Type':'application/json'};
      if(header)headers['X-Simulate-Failure']=header;
      const r=await fetch(API+'/chat',{method:'POST',headers,body:JSON.stringify({session_id:session,message:text,...(systemPrompt?{system_prompt:systemPrompt}:{})})});
      const d=await r.json();
      if(!r.ok)throw new Error(d.detail||'The request could not be completed.');
      setMessages(m=>[...m,{role:'assistant',content:d.reply,metadata:d.metadata}]);
      setStats(s=>({requests:s.requests+1,cache:s.cache+(d.metadata.resolution_source==='LLM_CACHE'?1:0),live:s.live+(d.metadata.resolution_source==='LIVE_INFERENCE'?1:0),latency:s.latency+d.metadata.latency_ms}));
      setSessions(s=>s.some(x=>x.id===session)?s:[{id:session,title:text.slice(0,28)},...s]);
    }catch(e:any){setError(e.message);setMessages(m=>m.filter((x,i)=>!(i===m.length-1&&x.role==='user')));}
    finally{setBusy(false);}
  };
  const runSimulation=()=>send('Briefly explain why resilient AI systems need provider failover.',sim);
  const copy=(s:string)=>navigator.clipboard?.writeText(s);
  const cacheRate=stats.requests?Math.round(stats.cache/stats.requests*100):0;
  return <div className="app">
    {sidebar&&<aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Sparkles size={19}/></div><div><b>NEXORA</b><small>AI WORKSPACE</small></div><button className="icon-btn side-close" onClick={()=>setSidebar(false)}><PanelLeftClose size={17}/></button></div>
      <button className="new-chat" onClick={startNew}><Plus size={17}/> New conversation <span>⌘ K</span></button>
      <div className="side-label">WORKSPACE</div>
      <button className={`nav-item ${panel==='chat'?'active':''}`} onClick={()=>setPanel('chat')}><MessageSquarePlus size={17}/> Chat workspace</button>
      <button className={`nav-item ${panel==='reliability'?'active':''}`} onClick={()=>setPanel('reliability')}><Activity size={17}/> Reliability center</button>
      <button className={`nav-item ${panel==='playground'?'active':''}`} onClick={()=>setPanel('playground')}><Terminal size={17}/> Developer playground <span className="beta">LAB</span></button>
      <div className="side-label history-label">RECENT CONVERSATIONS</div>
      <div className="session-list">{sessions.map(s=><button key={s.id} className={`session-item ${s.id===session?'selected':''}`} onClick={()=>loadSession(s.id)}><MessageSquarePlus size={14}/><span>{s.title}</span></button>)}</div>
      <div className="sidebar-bottom"><div className="user-avatar">DS</div><div className="user-info"><b>Developer workspace</b><small>Personal environment</small></div><Settings2 size={17} className="muted"/></div>
    </aside>}
    <main className="main">
      <header className="topbar">
        <div className="top-left"><button className="icon-btn" onClick={()=>setSidebar(!sidebar)}><Menu size={18}/></button><span className="crumb">Workspace</span><ChevronRight size={14} className="muted"/><b>{panel==='chat'?'Chat':panel==='reliability'?'Reliability center':'Developer playground'}</b></div>
        <div className="top-right"><span className="status-dot"/><span className="status-text">{health?.status==='ok'?'Systems operational':'Backend not connected'}</span><div className="top-divider"/><button className="help-btn"><CircleHelp size={16}/> Help</button></div>
      </header>
      {panel==='chat'?<section className="chat-shell">
        {messages.length===0?<div className="welcome"><div className="welcome-orb"><Sparkles size={27}/></div><div className="eyebrow"><span/> YOUR INTELLIGENCE WORKSPACE</div><h1>Think clearly.<br/><em>Build without limits.</em></h1><p className="welcome-copy">A dependable AI workspace designed for thoughtful conversations, resilient inference and transparent performance.</p>
          <div className="prompt-grid">{prompts.map((p,i)=><button key={p} className="prompt-card" onClick={()=>send(p)}><span className="prompt-icon">{i===0?<ShieldCheck size={17}/>:i===1?<Cpu size={17}/>:<Code2 size={17}/>}</span><span>{p}</span><ChevronRight size={15}/></button>)}</div>
        </div>:<div className="conversation">{messages.map((m,i)=><div key={i} className={`message-row ${m.role}`}><div className={`message-avatar ${m.role}`}>{m.role==='assistant'?<Sparkles size={16}/>:<span>DS</span>}</div><div className="message-body"><div className="message-author">{m.role==='assistant'?'Nexora AI':'You'} <small>{m.role==='assistant'?'· Response':'· Just now'}</small></div><div className="message-content">{m.role==='assistant'?<ReactMarkdown>{m.content}</ReactMarkdown>:m.content}</div>{m.role==='assistant'&&m.metadata&&<div className="metadata"><div className="meta-top"><span className={`source ${m.metadata.resolution_source==='LLM_CACHE'?'cached':''}`}><span/> {m.metadata.resolution_source}</span><span className="meta-model">{m.metadata.model}</span><span className="meta-latency">{m.metadata.latency_ms} ms</span><button onClick={()=>setExpanded(v=>v.includes(i)?v.filter(x=>x!==i):[...v,i])}>{expanded.includes(i)?'Less':'Details'} <ChevronDown size={13}/></button></div>{expanded.includes(i)&&<div className="meta-details"><span>Input tokens <b data-testid="meta-input-tokens">{m.metadata.input_tokens}</b></span><span>Output tokens <b data-testid="meta-output-tokens">{m.metadata.output_tokens}</b></span><span>Key ID <b>{m.metadata.key_id||'Cache'}</b></span><span>Fallback attempts <b>{m.metadata.fallback_attempts}</b></span></div>}<span className="hidden-test" data-testid="meta-source">{m.metadata.resolution_source}</span><span className="hidden-test" data-testid="meta-model">{m.metadata.model}</span><span className="hidden-test" data-testid="meta-latency">{m.metadata.latency_ms} ms</span></div>}</div><button className="copy-message" onClick={()=>copy(m.content)} title="Copy message"><Copy size={14}/></button></div>)}
          {busy&&<div className="message-row assistant"><div className="message-avatar assistant"><Sparkles size={16}/></div><div className="message-body"><div className="message-author">Nexora AI <small>· Thinking</small></div><div className="typing"><i/><i/><i/></div></div></div>}<div ref={endRef}/></div>}
        <div className="composer-wrap">{error&&<div className="error-banner">{error}</div>}<div className="composer"><textarea data-testid="chat-input" value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}}} placeholder="Ask anything. Nexora is ready to think with you…" rows={2}/><div className="composer-bottom"><div className="composer-tools"><button onClick={()=>setShowPrompt(!showPrompt)}><Settings2 size={14}/> System prompt</button><span className="tool-separator"/><span><Zap size={13}/> Smart routing</span></div><button data-testid="send-button" className="send-btn" disabled={!input.trim()||busy} onClick={()=>send()}><Send size={15}/> Send</button></div></div>{showPrompt&&<div className="system-prompt"><label>SESSION SYSTEM PROMPT</label><textarea data-testid="system-prompt-input" value={systemPrompt} onChange={e=>setSystemPrompt(e.target.value)} placeholder="Define how Nexora should respond…"/></div>}<div className="composer-note">Nexora can make mistakes. Verify important information. <span>·</span> Enter to send, Shift + Enter for new line</div></div>
      </section>:panel==='reliability'?<section className="tool-page"><div className="page-heading"><div className="eyebrow">SYSTEM OBSERVABILITY</div><h1>Reliability <em>center</em></h1><p>Understand how Nexora handles provider availability, caching and inference performance.</p></div><div className="stat-grid"><Stat icon={<Activity/>} label="Requests this session" value={stats.requests}/><Stat icon={<Zap/>} label="Cache hit rate" value={`${cacheRate}%`}/><Stat icon={<Gauge/>} label="Average latency" value={`${stats.requests?Math.round(stats.latency/stats.requests):0} ms`}/><Stat icon={<Cpu/>} label="Live inferences" value={stats.live}/></div><div className="panel-card"><div className="panel-title"><div><h3>Provider configuration</h3><p>Key identifiers only · secrets are never displayed</p></div><span className="live-pill">CONFIGURATION</span></div><div className="provider-row"><div className="provider-icon"><Cpu/></div><div><b>Provider key pool</b><small>{health?.keys_configured??'—'} configured key(s)</small></div><span className="provider-state">{health?.keys_configured>=2?'Configured':'Needs configuration'}</span></div><div className="provider-row"><div className="provider-icon"><Zap/></div><div><b>LiteLLM response cache</b><small>Built-in cache enabled in backend configuration</small></div><span className="provider-state">{health?.cache_enabled?'Enabled':'Unknown'}</span></div></div><div className="panel-card"><div className="panel-title"><div><h3>Session performance</h3><p>Metrics collected from successful requests in this browser session</p></div></div><div className="bar-metrics"><div><span>Cache hits</span><b>{stats.cache}</b></div><div className="bar"><i style={{width:`${cacheRate}%`}}/></div><div><span>Live inference</span><b>{stats.live}</b></div><div className="bar"><i style={{width:`${stats.requests?100-cacheRate:0}%`}}/></div></div></div></section>:<section className="tool-page"><div className="page-heading"><div className="eyebrow">CONTROLLED FAILURE TESTING</div><h1>Developer <em>playground</em></h1><p>Trigger the assignment's failover test hook and inspect the real API response.</p></div><div className="panel-card"><div className="panel-title"><div><h3>Simulate provider failure</h3><p>Simulation must be enabled on the backend with ENABLE_FAILURE_SIMULATION=true.</p></div><span className="live-pill">TEST LAB</span></div><label className="field-label">FAILURE SCENARIO</label><select className="scenario-select" value={sim} onChange={e=>setSim(e.target.value)}><option value="">Choose a scenario…</option><option value="key_1=429">Primary key returns 429 · fallback to key 2</option><option value="key_1=500">Primary key returns 500 · fallback to key 2</option><option value="*=429">All keys return 429 · expect HTTP 503</option></select><div className="scenario-hint"><ShieldCheck size={16}/> Simulated failures apply to this request only. Successful fallback still performs real AI inference.</div><button className="primary-action" disabled={!sim||busy} onClick={runSimulation}><Terminal size={16}/> Run failover test</button><div className="code-preview"><div><span/> REQUEST HEADER</div><code>X-Simulate-Failure: {sim||'select a scenario'}</code></div></div><div className="panel-card"><h3>API quick reference</h3><div className="endpoint"><b>GET</b><code>/health</code><span>Backend health and configuration</span></div><div className="endpoint"><b className="post">POST</b><code>/chat</code><span>Send a message and receive metadata</span></div><div className="endpoint"><b>GET</b><code>/sessions/{'{session_id}'}/messages</code><span>Retrieve persisted conversation history</span></div></div></section>}
      <footer className="footer"><span>© 2026 NEXORA AI</span><span><span className="status-dot"/> Built for reliability <span className="footer-sep">·</span> Powered by LiteLLM</span></footer>
    </main>
  </div>
}
function Stat({icon,label,value}:{icon:any;label:string;value:any}){return <div className="stat-card"><div className="stat-icon">{icon}</div><span>{label}</span><b>{value}</b></div>}
