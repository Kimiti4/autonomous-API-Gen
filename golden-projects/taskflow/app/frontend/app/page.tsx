'use client';
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const [name, setName] = useState('');
  const [message, setMessage] = useState('');
  useEffect(() => setToken(localStorage.getItem('taskflow_token')), []);
  if (token) return <Dashboard token={token} onLogout={() => { localStorage.removeItem('taskflow_token'); setToken(null); }} />;
  async function login() {
    const r = await fetch(API + '/auth/login', {method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({email,password})});
    const data = await r.json(); if (!r.ok) return setMessage(data.detail || 'Login failed'); localStorage.setItem('taskflow_token',data.token); setToken(data.token);
  }
  async function register() {
    const r = await fetch(API + '/auth/register', {method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({email,password,name})});
    const data = await r.json(); if (!r.ok) return setMessage(data.detail || 'Registration failed'); localStorage.setItem('taskflow_token',data.token); setToken(data.token);
  }
  return <main className="shell"><div className="card" style={{maxWidth:520,margin:'80px auto'}}><h1>TaskFlow</h1><p className="muted">Golden Coherence Suite application.</p><input placeholder="Name (registration)" value={name} onChange={e=>setName(e.target.value)}/><input placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)}/><input placeholder="Password" type="password" value={password} onChange={e=>setPassword(e.target.value)}/><div className="row"><button onClick={login}>Sign in</button><button onClick={register}>Create account</button></div>{message && <p>{message}</p>}</div></main>;
}

function Dashboard({token,onLogout}:{token:string,onLogout:()=>void}) {
 const [workspaces,setWorkspaces]=useState<any[]>([]); const [selected,setSelected]=useState<any>(null); const [projects,setProjects]=useState<any[]>([]); const [projectName,setProjectName]=useState(''); const [taskName,setTaskName]=useState('');
 async function load() { const r=await fetch(API+'/workspaces',{headers:{Authorization:'Bearer '+token}}); const d=await r.json(); setWorkspaces(d); if(d[0]) {setSelected(d[0]); const p=await fetch(API+'/workspaces/'+d[0].id+'/projects',{headers:{Authorization:'Bearer '+token}}); setProjects(await p.json());} }
 useEffect(()=>{load()},[]);
 async function createWorkspace(){const name=prompt('Workspace name');if(!name)return;await fetch(API+'/workspaces',{method:'POST',headers:{'content-type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({name})});load();}
 async function createProject(){if(!selected||!projectName)return;await fetch(API+'/workspaces/'+selected.id+'/projects',{method:'POST',headers:{'content-type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({name:projectName})});setProjectName('');load();}
 async function createTask(id:string){if(!taskName)return;await fetch(API+'/projects/'+id+'/tasks',{method:'POST',headers:{'content-type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({title:taskName})});setTaskName('');load();}
 return <main className="shell"><div className="row"><div><h1>TaskFlow</h1><p className="muted">Workspace and delivery dashboard</p></div><button onClick={onLogout}>Sign out</button></div><div className="grid"><section className="card"><h2>Workspaces</h2>{workspaces.map(w=><p key={w.id}><button onClick={async()=>{setSelected(w);const r=await fetch(API+'/workspaces/'+w.id+'/projects',{headers:{Authorization:'Bearer '+token}});setProjects(await r.json())}}>{w.name}</button></p>)}<button onClick={createWorkspace}>+ Workspace</button></section><section className="card"><h2>{selected?.name || 'Select a workspace'}</h2><input placeholder="New project" value={projectName} onChange={e=>setProjectName(e.target.value)}/><button onClick={createProject}>Add project</button>{projects.map(p=><div key={p.id} style={{marginTop:16,paddingTop:12,borderTop:'1px solid #eee'}}><b>{p.name}</b><input placeholder="New task" value={taskName} onChange={e=>setTaskName(e.target.value)}/><button onClick={()=>createTask(p.id)}>Add task</button></div>)}</section></div></main>;
}