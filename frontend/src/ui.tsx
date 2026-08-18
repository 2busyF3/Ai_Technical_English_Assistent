import type {ButtonHTMLAttributes,HTMLAttributes,ReactNode} from "react";
import { LoaderCircle, X } from "lucide-react";

export function cn(...values:(string|false|undefined|null)[]){return values.filter(Boolean).join(" ")}
export function Button({className="",variant="primary",loading,children,...props}:ButtonHTMLAttributes<HTMLButtonElement>&{variant?:"primary"|"secondary"|"ghost"|"danger";loading?:boolean}){return <button className={cn("button",`button-${variant}`,className)} disabled={loading||props.disabled} {...props}>{loading&&<LoaderCircle size={16} className="spin"/>}{children}</button>}
export function Card({className="",...props}:HTMLAttributes<HTMLDivElement>){return <div className={cn("card",className)} {...props}/>}
export function Badge({children,tone="neutral"}:{children:ReactNode;tone?:"neutral"|"green"|"amber"|"blue"}){return <span className={`badge badge-${tone}`}>{children}</span>}
export function Progress({value}:{value:number}){return <div className="progress" role="progressbar" aria-valuenow={value}><span style={{width:`${Math.max(0,Math.min(100,value))}%`}}/></div>}
export function Skeleton({className=""}:{className?:string}){return <div className={`skeleton ${className}`}/>} 
export function Empty({icon,title,description}:{icon:ReactNode;title:string;description:string}){return <Card className="empty">{icon}<h3>{title}</h3><p>{description}</p></Card>}
export function ErrorState({message,retry}:{message:string;retry?:()=>void}){return <Card className="empty"><X/><h3>We hit a snag</h3><p>{message}</p>{retry&&<Button onClick={retry}>Try again</Button>}</Card>}
export function Toast({message,onClose}:{message:string;onClose:()=>void}){return <div className="toast" role="status"><span>{message}</span><button onClick={onClose} aria-label="Close"><X size={16}/></button></div>}
