import { FormEvent, useEffect, useRef, useState } from "react";
import { BookOpen, Bot, CircleAlert, Languages, MicOff, Send, Sparkles, Square, Target } from "lucide-react";
import { streamTutor } from "./api";
import { TutorMessage, useAppStore } from "./store";
import { Badge, Card } from "./ui";

export function StableTutorPage(){
  const messages=useAppStore(s=>s.tutorMessages);
  const updateMessages=useAppStore(s=>s.updateTutorMessages);
  const sessionId=useAppStore(s=>s.tutorSessionId);
  const setSessionId=useAppStore(s=>s.setTutorSessionId);
  const clearTutor=useAppStore(s=>s.clearTutor);
  const [input,setInput]=useState("");
  const [streaming,setStreaming]=useState(false);
  const [error,setError]=useState("");
  const controller=useRef<AbortController|null>(null);
  const mounted=useRef(true);
  const bottom=useRef<HTMLDivElement>(null);

  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;controller.current?.abort()}},[]);
  useEffect(()=>{bottom.current?.scrollIntoView({behavior:"smooth"});},[messages]);

  const send=async(text?:string)=>{
    const message=(text??input).trim();
    if(!message||streaming)return;
    const userMessage:TutorMessage={role:"user",content:message};
    updateMessages(items=>[...items,userMessage,{role:"assistant",content:""}]);
    setInput("");setStreaming(true);setError("");
    controller.current=new AbortController();
    try{
      await streamTutor(
        {session_id:sessionId??undefined,message,mode:"free_conversation"},
        {
          meta:data=>setSessionId(data.session_id),
          token:data=>updateMessages(items=>{
            const copy=[...items],last=copy[copy.length-1];
            if(last?.role!=="assistant")return copy;
            copy[copy.length-1]={...last,content:last.content+String(data.token??"")};return copy;
          }),
          done:data=>updateMessages(items=>{
            const copy=[...items],last=copy[copy.length-1];
            if(last?.role!=="assistant")return copy;
            copy[copy.length-1]={...last,blocks:Array.isArray(data.ui_blocks)?data.ui_blocks:[]};return copy;
          }),
          error:data=>setError(data.message||"Tutor could not respond"),
        },controller.current.signal,
      );
    }catch(reason){
      if((reason as Error).name!=="AbortError"&&mounted.current)setError(reason instanceof Error?reason.message:"Tutor unavailable");
    }finally{if(mounted.current)setStreaming(false)}
  };
  const retryText=[...messages].reverse().find(message=>message.role==="user")?.content;

  return <div className="tutor-layout"><aside className="tutor-context"><p className="eyebrow">Conversation focus</p><h2>Backend performance</h2><p>Build clear, structured technical explanations.</p><div className="context-section"><small>ACTIVE GOALS</small><span><Target/>Technical interview</span><span><Languages/>Performance vocabulary</span><span><BookOpen/>Past Simple</span></div><div className="context-section"><small>WORDS TO USE</small><div className="skill-chips"><span>latency</span><span>bottleneck</span><span>throughput</span><span>cache</span></div></div><Card><Sparkles/><b>Tutor keeps your context</b><p>Your conversation stays in this browser tab when you visit another section.</p></Card></aside><section className="chat"><header><div><span className="avatar"><Bot/></span><div><h3>Technical English Tutor</h3><span className="online">● {streaming?"Writing…":"Ready to practise"}</span></div></div><div className="chat-head-actions"><button type="button" onClick={clearTutor} disabled={streaming}>New chat</button><Badge tone="green">B1 adaptive</Badge></div></header><div className="messages">{messages.map((message,index)=><div className={`message ${message.role}`} key={`${message.role}-${index}`}>{message.role==="assistant"&&<span className="avatar"><Bot/></span>}<div><div className="bubble">{message.content||<span className="typing"><i/><i/><i/></span>}</div>{message.blocks?.map((block,blockIndex)=>block.type==="VOCAB_CARD"?<Card className="vocab-block" key={blockIndex}><Languages/><div><small>USEFUL COLLOCATION</small><h4>{block.payload.term}</h4><p>{block.payload.meaning}</p><em>{block.payload.example}</em></div></Card>:null)}</div></div>)}{error&&<div className="chat-error"><CircleAlert/>{error}{retryText&&<button type="button" onClick={()=>void send(retryText)}>Retry</button>}</div>}<div ref={bottom}/></div><div className="suggestions">{messages.length<3&&["I reduced API latency","We had a deployment issue","Practise an interview answer"].map(text=><button type="button" onClick={()=>void send(text)} key={text}>{text}</button>)}</div><form className="composer" onSubmit={(event:FormEvent)=>{event.preventDefault();void send()}}><textarea value={input} onChange={event=>setInput(event.target.value)} onKeyDown={event=>{if(event.key==="Enter"&&!event.shiftKey&&!event.nativeEvent.isComposing){event.preventDefault();void send()}}} placeholder="Describe your work in English…" rows={2}/><button type="button" disabled title="Voice practice is not available in this MVP"><MicOff/></button>{streaming?<button type="button" className="send" onClick={()=>controller.current?.abort()} aria-label="Stop generation"><Square fill="currentColor"/></button>:<button type="submit" className="send" disabled={!input.trim()} aria-label="Send message"><Send/></button>}<span>Enter to send · Shift + Enter for a new line</span></form></section></div>
}
