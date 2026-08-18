import { create } from "zustand";

type User = {id:string; email:string; display_name:string; onboarding_completed:boolean; placement_completed:boolean};
type AppState = {
  token:string|null; user:User|null; sidebarOpen:boolean;
  setSession:(token:string,user:User)=>void; setUser:(user:User)=>void; logout:()=>void; toggleSidebar:()=>void;
};
const savedToken = localStorage.getItem("tutor-token");
const savedUser = localStorage.getItem("tutor-user");
export const useAppStore = create<AppState>((set)=>({
  token:savedToken, user:savedUser?JSON.parse(savedUser):null, sidebarOpen:false,
  setSession:(token,user)=>{localStorage.setItem("tutor-token",token);localStorage.setItem("tutor-user",JSON.stringify(user));set({token,user});},
  setUser:(user)=>{localStorage.setItem("tutor-user",JSON.stringify(user));set({user});},
  logout:()=>{localStorage.removeItem("tutor-token");localStorage.removeItem("tutor-user");set({token:null,user:null});},
  toggleSidebar:()=>set(s=>({sidebarOpen:!s.sidebarOpen})),
}));

