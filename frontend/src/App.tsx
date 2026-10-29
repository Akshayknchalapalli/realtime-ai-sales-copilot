import {useEffect,useRef,useState} from 'react';

type Turn={speaker:'customer'|'sdr';text:string;event_id:string};
type Recommendation={intent:string;suggestion:string;reason:string;next_action:string;source_ids:string[]};
const scenario:{speaker:'customer'|'sdr';text:string}[]=[
{speaker:'sdr',text:'How do you manage your leads today?'},
{speaker:'customer',text:'We use Excel and keep missing follow-ups.'},
{speaker:'sdr',text:'How large is your sales team?'},
{speaker:'customer',text:'About 15 people, but your pricing seems expensive.'},
{speaker:'customer',text:'Can FlowDesk connect to Salesforce?'},
{speaker:'customer',text:'Can we schedule a demo?'}
];
export default function App(){
 const [sessionId]=useState(()=>crypto.randomUUID());
 const ws=useRef<WebSocket|null>(null);
 const [connected,setConnected]=useState(false);
 const [mode,setMode]=useState('connecting');
 const [speaker,setSpeaker]=useState<'sdr'|'customer'>('customer');
 const [text,setText]=useState('');
 const [turns,setTurns]=useState<Turn[]>([]);
 const [recommendation,setRecommendation]=useState<Recommendation|null>(null);
 const [processing,setProcessing]=useState(false);
 const [latency,setLatency]=useState<number|null>(null);
 const [timings,setTimings]=useState<{retrieval_ms:number;generation_ms:number}|null>(null);
 const [dismissed,setDismissed]=useState(false);
 const [error,setError]=useState('');
 const [version,setVersion]=useState(0);
 const [playing,setPlaying]=useState(false);
 const playback=useRef(false);
 useEffect(()=>{
  const socket=new WebSocket(`${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/ws/sessions/${sessionId}`);
  ws.current=socket;
  socket.onopen=()=>{setConnected(true);setError('')};
  socket.onclose=()=>{setConnected(false);playback.current=false;setPlaying(false)};
  socket.onerror=()=>setError('WebSocket connection failed. Start FastAPI on port 8000.');
  socket.onmessage=(message)=>{
   const event=JSON.parse(message.data);
   if(event.type==='session.started')setMode(event.mode);
   if(event.type==='transcript.ack')setVersion(event.conversation_version);
   if(event.type==='recommendation.processing'){setProcessing(true);setRecommendation(null);setDismissed(false)}
   if(event.type==='recommendation.ready'){setRecommendation(event.data);setLatency(event.latency_ms);setTimings(event.timings || null);setDismissed(false);setProcessing(false)}
   if(event.type==='error'){setError(event.message);setProcessing(false)}
  };
  return ()=>{socket.close();ws.current=null};
 },[sessionId]);
 function send(s:'sdr'|'customer',value:string){
  if(!value.trim()||ws.current?.readyState!==WebSocket.OPEN)return;
  const turn={speaker:s,text:value.trim(),event_id:crypto.randomUUID()};
  ws.current.send(JSON.stringify({...turn,type:'transcript.final',session_id:sessionId,timestamp:new Date().toISOString()}));
  setTurns(old=>[...old,turn]);setText('');setError('');
 }
 async function demo(){
  if(playing||!connected)return;
  playback.current=true;setPlaying(true);
  for(const item of scenario){
   if(!playback.current||ws.current?.readyState!==WebSocket.OPEN)break;
   send(item.speaker,item.text);
   await new Promise(resolve=>setTimeout(resolve,2200));
  }
  playback.current=false;setPlaying(false);
 }
 return <div className="app">
  <header><div><div className="eyebrow">FLOWDESK / AI ASSISTANT</div><h1>Real-Time Sales Copilot</h1><p>Actionable suggestions while the customer conversation unfolds.</p></div><div className="status"><span className={connected?'dot online':'dot'}/>{connected?'Connected':'Disconnected'}<small>{mode==='offline-demo'?'Offline demo (no LLM)':'AI mode: '+mode}</small></div></header>
  <div className="toolbar"><span>Session {sessionId.slice(0,8)} · Version {version}</span><button disabled={!connected||playing} onClick={demo}>{playing?'Playing demo…':'▶ Play sample call'}</button><button className="outline" onClick={()=>{playback.current=false;setPlaying(false)}} disabled={!playing}>Stop</button></div>
  {error&&<div className="error">{error}</div>}
  <main><section className="panel"><div className="panel-title"><h2>Live transcript</h2><span>{turns.length} turns</span></div><div className="conversation">{turns.length===0?<div className="empty">Start a demo call or enter a conversation turn below.</div>:turns.map(turn=><article key={turn.event_id} className={turn.speaker==='customer'?'customer':'rep'}><small>{turn.speaker==='customer'?'CUSTOMER':'SALES REP'}</small><p>{turn.text}</p></article>)}</div><div className="composer"><div className="inputs"><select value={speaker} onChange={e=>setSpeaker(e.target.value as 'sdr'|'customer')}><option value="customer">Customer</option><option value="sdr">SDR</option></select><input aria-label="Conversation turn" placeholder="Type a live transcript message…" value={text} onChange={e=>setText(e.target.value)} onKeyDown={e=>{if(e.key==='Enter')send(speaker,text)}}/></div><button disabled={!connected||!text.trim()} onClick={()=>send(speaker,text)}>Send turn →</button></div></section>
  <aside><section className="panel"><div className="panel-title"><h2>✦ Next-best response</h2>{processing&&<span className="pulse">Thinking…</span>}</div>{recommendation&&!dismissed?<div className="recommendation"><div className="label">SAY THIS NEXT</div><blockquote>“{recommendation.suggestion}”</blockquote><div className="suggestion-actions"><button onClick={()=>{setSpeaker('sdr');setText(recommendation.suggestion)}}>Use / Edit suggestion</button><button className="outline" onClick={()=>setDismissed(true)}>Dismiss</button></div><div className="details"><b>Detected intent</b><span>{recommendation.intent.replaceAll('_',' ')}</span><b>Why</b><p>{recommendation.reason}</p><b>Next action</b><p>{recommendation.next_action}</p><b>Knowledge sources</b><div className="sources">{recommendation.source_ids.map(id=><code key={id}>{id}</code>)}</div></div></div>:<div className="empty">{processing?'Generating a grounded response…':'Customer suggestions appear here as each turn finishes.'}</div>}</section><section className="panel metrics"><h2>Live metrics</h2><div><span>Last suggestion latency</span><strong>{latency===null?'—':latency+' ms'}</strong></div><div><span>Retrieval latency</span><strong>{timings?timings.retrieval_ms+' ms':'—'}</strong></div><div><span>LLM generation latency</span><strong>{timings?timings.generation_ms+' ms':'—'}</strong></div><div><span>AI pipeline</span><strong>{mode==='offline-demo'?'Deterministic demo':mode==='ollama'?'Ollama + FAISS':mode==='openai'?'OpenAI + RAG':mode}</strong></div><div><span>Speaker separation</span><strong>Transcript labels</strong></div></section></aside></main>
  <footer>Fictional FlowDesk CRM · Interview prototype · Transcript-based, not live audio · Validate all customer-facing claims</footer>
 </div>;
}
