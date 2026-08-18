import { useAppStore } from "./store";

const BASE = import.meta.env.VITE_API_URL || "/api/v1";
type RefreshedSession={access_token:string;user:any};
let refreshPromise:Promise<boolean>|null=null;

async function refreshAccessToken():Promise<boolean>{
  if(refreshPromise)return refreshPromise;
  refreshPromise=(async()=>{
    const response=await fetch(`${BASE}/auth/refresh`,{method:"POST",credentials:"include"});
    if(!response.ok){useAppStore.getState().logout();return false;}
    const session=await response.json() as RefreshedSession;
    useAppStore.getState().setSession(session.access_token,session.user);
    return true;
  })().finally(()=>{refreshPromise=null;});
  return refreshPromise;
}

export async function api<T>(path:string, init:RequestInit={}):Promise<T>{
  let token=useAppStore.getState().token;
  let response=await fetch(`${BASE}${path}`,{...init,credentials:"include",headers:{...(init.body instanceof FormData?{}:{"Content-Type":"application/json"}),...(token?{Authorization:`Bearer ${token}`}:{}) ,...init.headers}});
  if(response.status===401&&!path.startsWith("/auth/")){const refreshed=await refreshAccessToken();if(refreshed){token=useAppStore.getState().token;response=await fetch(`${BASE}${path}`,{...init,credentials:"include",headers:{...(init.body instanceof FormData?{}:{"Content-Type":"application/json"}),...(token?{Authorization:`Bearer ${token}`}:{}) ,...init.headers}});}}
  if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(body.detail||body.error?.message||"Something went wrong");}
  if(response.status===204)return undefined as T;
  return response.json();
}
export async function streamTutor(body:{session_id?:string;message:string;mode:string}, handlers:{meta:(data:any)=>void;token:(data:any)=>void;done:(data:any)=>void;error:(data:any)=>void}, signal:AbortSignal){
  const token=useAppStore.getState().token;
  let response=await fetch(`${BASE}/tutor/stream`,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`},body:JSON.stringify(body),signal});
  if(response.status===401&&await refreshAccessToken()){const refreshedToken=useAppStore.getState().token;response=await fetch(`${BASE}/tutor/stream`,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json",Authorization:`Bearer ${refreshedToken}`},body:JSON.stringify(body),signal});}
  if(!response.ok){const error=await response.json().catch(()=>({}));throw new Error(error.detail||error.error?.message||"Tutor is unavailable");}
  const reader=response.body!.getReader(),decoder=new TextDecoder();let buffer="";
  while(true){const {done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const events=buffer.split("\n\n");buffer=events.pop()||"";for(const raw of events){const lines=raw.split("\n");const name=lines.find(l=>l.startsWith("event:"))?.slice(6).trim() as keyof typeof handlers;const data=lines.find(l=>l.startsWith("data:"))?.slice(5).trim();if(name&&data&&handlers[name])handlers[name](JSON.parse(data));}}
}
