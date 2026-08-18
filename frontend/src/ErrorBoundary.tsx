import { Component, ErrorInfo, ReactNode } from "react";
import { CircleAlert } from "lucide-react";
import { Button, Card } from "./ui";

export class ErrorBoundary extends Component<{children:ReactNode},{error:Error|null}>{
  state:{error:Error|null}={error:null};
  static getDerivedStateFromError(error:Error){return {error}}
  componentDidCatch(error:Error,info:ErrorInfo){console.error("Application view crashed",error,info)}
  render(){
    if(this.state.error)return <div className="fatal-error"><Card><CircleAlert/><h1>This view hit an error</h1><p>Your account and progress are safe. Try again or return to the dashboard.</p><div><Button onClick={()=>this.setState({error:null})}>Try again</Button><a className="button button-secondary" href="/app">Dashboard</a></div></Card></div>;
    return this.props.children;
  }
}
