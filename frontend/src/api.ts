import { useAppStore } from "./store";

const BASE = import.meta.env.VITE_API_URL || "/api/v1";
export async function api<T>(path:string, init:RequestInit={}):Promise<T>{
  const token=useAppStore.getState().token;
  const response=await fetch(`${BASE}${path}`,{...init,headers:{...(init.body instanceof FormData?{}:{"Content-Type":"application/json"}),...(token?{Authorization:`Bearer ${token}`}:{}) ,...init.headers}});
  if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(body.detail||body.error?.message||"Something went wrong");}
  return response.json();
}
export async function streamTutor(body:{session_id?:string;message:string;mode:string}, handlers:{meta:(data:any)=>void;token:(data:any)=>void;done:(data:any)=>void;error:(data:any)=>void}, signal:AbortSignal){
  const token=useAppStore.getState().token;
  const response=await fetch(`${BASE}/tutor/stream`,{method:"POST",headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`},body:JSON.stringify(body),signal});
  if(!response.ok)throw new Error("Tutor is unavailable");
  const reader=response.body!.getReader(),decoder=new TextDecoder();let buffer="";
  while(true){const {done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const events=buffer.split("\n\n");buffer=events.pop()||"";for(const raw of events){const lines=raw.split("\n");const name=lines.find(l=>l.startsWith("event:"))?.slice(6).trim() as keyof typeof handlers;const data=lines.find(l=>l.startsWith("data:"))?.slice(5).trim();if(name&&data&&handlers[name])handlers[name](JSON.parse(data));}}
}

