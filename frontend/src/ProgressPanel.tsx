import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BookOpen, CheckCircle2, Flame, Languages, MessageSquareText, Trophy } from "lucide-react";
import { api } from "./api";
import { Badge, Card, Empty, ErrorState, Progress, Skeleton } from "./ui";

type ProgressData={categories:{name:string;progress:number}[];activity:number[];activity_labels:string[];achievements:string[];level:string;target:string;streak:number;completed_lessons:number;vocabulary_reviews:number};

export function RealProgressPage(){
  const query=useQuery({queryKey:["progress"],queryFn:()=>api<ProgressData>("/progress")});
  if(query.isLoading)return <Skeleton className="tall"/>;
  if(query.error)return <ErrorState message={query.error.message}/>;
  const data=query.data!;
  const maxActivity=Math.max(1,...data.activity);
  const levels=["A1","A2","B1","B2","C1","C2"],targetReached=levels.indexOf(data.level)>=levels.indexOf(data.target);
  return <><div className="vocab-page-title"><div><p className="eyebrow">Learning analytics</p><h1>Your progress</h1><p>Everything here comes from completed lessons and vocabulary reviews.</p></div><Badge tone="green"><Flame/>{data.streak} lesson streak</Badge></div><div className="progress-kpis"><Card><strong>{data.completed_lessons}</strong><span>lessons completed</span></Card><Card><strong>{data.vocabulary_reviews}</strong><span>vocabulary recalls</span></Card><Card><strong>{data.level}</strong><span>current estimate</span></Card></div><div className="progress-layout"><Card className="activity-card"><div className="card-heading"><div><small>LAST 7 DAYS</small><h3>Completed lessons</h3></div></div><div className="activity-chart real-activity">{data.activity.map((value,index)=><div key={index}><span style={{height:`${value?Math.max(18,value/maxActivity*100):4}%`}}/><small>{data.activity_labels[index]}</small><em>{value}</em></div>)}</div></Card><Card className="cefr-card"><small>CURRENT ESTIMATE</small><div><strong>{data.level}</strong>{targetReached?<CheckCircle2/>:<ArrowRight/>}<span>{targetReached?`Target ${data.target} reached`:data.target}</span></div><p>Skill mastery updates after every lesson; vocabulary reviews are scheduled separately with spaced repetition.</p></Card></div><div className="skill-section"><h2>Skill areas</h2><div className="skill-grid">{data.categories.map((item,index)=><Card key={item.name}><span className={`attention-icon i${index%3}`}>{[<Languages/>,<BookOpen/>,<MessageSquareText/>][index%3]}</span><div><h3>{item.name}</h3><Progress value={item.progress}/><p>{item.progress>=70?"A growing strength":item.progress>=50?"Developing steadily":"High-impact focus"}</p></div><strong>{item.progress}%</strong></Card>)}</div></div><div className="achievements"><h2>Earned milestones</h2>{data.achievements.length?data.achievements.map((item,index)=><Card key={item}><span>{index===0?<Trophy/>:<CheckCircle2/>}</span><div><b>{item}</b><p>Recorded from your learning activity.</p></div></Card>):<Empty icon={<Trophy/>} title="Your first milestone is close" description="Complete a lesson or a vocabulary review to unlock it."/>}</div></>;
}
