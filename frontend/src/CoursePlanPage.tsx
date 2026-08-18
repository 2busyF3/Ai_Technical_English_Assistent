import { useQuery } from "@tanstack/react-query";
import { Check, Clock3, WandSparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "./api";
import { Badge, Card, ErrorState, Skeleton, cn } from "./ui";

type CoursePlan={title:string;week:number;level:string;completed:number;total:number;focus:string[];days:{day:string;topic:string;mode:string;minutes:number;done:boolean}[]};

export function CoursePlanPage(){
  const query=useQuery({queryKey:["plan"],queryFn:()=>api<CoursePlan>("/learning-plan")});
  if(query.isLoading)return <Skeleton className="tall"/>;
  if(query.error)return <ErrorState message={query.error.message}/>;
  const plan=query.data!,nextIndex=plan.days.findIndex(day=>!day.done);
  return <><div className="vocab-page-title"><div><p className="eyebrow">{plan.level} core course · {plan.completed}/{plan.total} modules</p><h1>{plan.title}</h1><p>Complete each module once. Failed patterns return at the end of the same lesson.</p></div><Badge tone={plan.completed===plan.total?"green":"blue"}>{plan.completed===plan.total?"Course complete":"In progress"}</Badge></div><Card className="focus-banner"><span><WandSparkles/></span><div><small>COURSE OUTCOME</small><h3>Communicate clearly in a backend team</h3><p>{plan.focus.join(" · ")}</p></div></Card><div className="plan-days">{plan.days.map((day,index)=><Card key={day.day} className={cn(day.done&&"done")}><div className="day-index">{day.done?<Check/>:index+1}</div><div><small>{day.day.toUpperCase()}</small><h3>{day.topic}</h3><span>{day.mode}</span></div><div className="day-time"><Clock3/>{day.minutes} min</div>{day.done?<Badge tone="green">Completed</Badge>:index===nextIndex?<Link className="button button-primary" to="/app/learn">Start</Link>:<Badge>Locked</Badge>}</Card>)}</div></>;
}
