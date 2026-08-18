import { create } from "zustand";

type User = {id:string; email:string; display_name:string; onboarding_completed:boolean; placement_completed:boolean};
export type TutorBlock = {type:string;payload:Record<string,string>};
export type TutorMessage = {role:"user"|"assistant";content:string;blocks?:TutorBlock[]};
const initialTutorMessages:TutorMessage[]=[{role:"assistant",content:"Hi! Let’s practise the English you need at work. Tell me about a backend task you’ve worked on recently — a deployment, a bug, or a performance improvement."}];
function loadTutorMessages():TutorMessage[]{try{const saved=sessionStorage.getItem("tutor-messages");return saved?JSON.parse(saved):initialTutorMessages}catch{return initialTutorMessages}}
type AppState = {
  token:string|null; user:User|null; sidebarOpen:boolean;
  tutorMessages:TutorMessage[]; tutorSessionId:string|null;
  setSession:(token:string,user:User)=>void; setUser:(user:User)=>void; logout:()=>void; toggleSidebar:()=>void;
  updateTutorMessages:(updater:(messages:TutorMessage[])=>TutorMessage[])=>void; setTutorSessionId:(id:string)=>void; clearTutor:()=>void;
};
const savedToken = localStorage.getItem("tutor-token");
const savedUser = localStorage.getItem("tutor-user");
export const useAppStore = create<AppState>((set)=>({
  token:savedToken, user:savedUser?JSON.parse(savedUser):null, sidebarOpen:false,
  tutorMessages:loadTutorMessages(), tutorSessionId:sessionStorage.getItem("tutor-session"),
  setSession:(token,user)=>{localStorage.setItem("tutor-token",token);localStorage.setItem("tutor-user",JSON.stringify(user));set({token,user});},
  setUser:(user)=>{localStorage.setItem("tutor-user",JSON.stringify(user));set({user});},
  logout:()=>{localStorage.removeItem("tutor-token");localStorage.removeItem("tutor-user");set({token:null,user:null});},
  toggleSidebar:()=>set(s=>({sidebarOpen:!s.sidebarOpen})),
  updateTutorMessages:(updater)=>set(s=>{const tutorMessages=updater(s.tutorMessages);sessionStorage.setItem("tutor-messages",JSON.stringify(tutorMessages));return {tutorMessages};}),
  setTutorSessionId:(id)=>{sessionStorage.setItem("tutor-session",id);set({tutorSessionId:id});},
  clearTutor:()=>{sessionStorage.removeItem("tutor-messages");sessionStorage.removeItem("tutor-session");set({tutorMessages:initialTutorMessages,tutorSessionId:null});},
}));
