from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
import jwt

from .db import get_db, init_db
from .models import AuthSession, AuditEvent, Comment, IdempotencyRecord, Membership, Project, Task, User, Workspace
from .security import create_token, decode_token, hash_password, verify_password

app = FastAPI(title="TaskFlow", version="1.0.0", description="Golden Coherence Suite application")
app.add_middleware(CORSMiddleware, allow_origins=[x for x in __import__('os').getenv('CORS_ORIGINS','http://localhost:3000').split(',') if x], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
bearer = HTTPBearer(auto_error=False)

@app.on_event("startup")
def startup():
    init_db()

class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str

class LoginIn(BaseModel):
    email: str
    password: str

class WorkspaceIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)

class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = ""

class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    assignee_id: str | None = None
    status: str = "todo"
    priority: str = "medium"
    due_date: str | None = None

class TaskPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    assignee_id: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: str | None = None
    archived: bool | None = None

class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=5000)

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="authentication-required")
    try:
        user_id, jti = decode_token(credentials.credentials)
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status_code=401, detail="invalid-authentication")
    user = db.get(User, user_id)
    session = db.get(AuthSession, jti)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="inactive-user")
    if not session or session.user_id != user.id or session.revoked:
        raise HTTPException(status_code=401, detail="session-revoked")
    return user

def membership(db: Session, workspace_id: str, user_id: str) -> Membership:
    item = db.scalar(select(Membership).where(Membership.workspace_id == workspace_id, Membership.user_id == user_id))
    if not item:
        raise HTTPException(status_code=403, detail="workspace-access-denied")
    return item

def require_role(item: Membership, *roles: str):
    if item.role not in roles:
        raise HTTPException(status_code=403, detail="insufficient-role")

def audit(db: Session, workspace_id: str, actor_id: str, action: str, resource_type: str, resource_id: str):
    db.add(AuditEvent(workspace_id=workspace_id, actor_id=actor_id, action=action, resource_type=resource_type, resource_id=resource_id))

@app.get('/health')
def health():
    return {"status": "healthy", "service": "taskflow", "version": "1.0.0"}

@app.post('/auth/register')
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="email-already-registered")
    user = User(email=email, password_hash=hash_password(payload.password), name=payload.name.strip())
    db.add(user); db.flush()
    token, jti = create_token(user.id)
    db.add(AuthSession(jti=jti, user_id=user.id)); db.commit(); db.refresh(user)
    return {"user_id": user.id, "token": token}

@app.post('/auth/login')
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid-credentials")
    token, jti = create_token(user.id)
    db.add(AuthSession(jti=jti, user_id=user.id)); db.commit()
    return {"user_id": user.id, "token": token, "name": user.name}

@app.post('/auth/logout')
def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if not credentials: raise HTTPException(status_code=401, detail="authentication-required")
    try: _, jti = decode_token(credentials.credentials)
    except (jwt.InvalidTokenError, ValueError): raise HTTPException(status_code=401, detail="invalid-authentication")
    session = db.get(AuthSession, jti)
    if not session: raise HTTPException(status_code=401, detail="invalid-authentication")
    session.revoked = True; db.commit()
    return {"revoked": True}

@app.get('/me')
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "name": user.name}

@app.post('/workspaces')
def create_workspace(payload: WorkspaceIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    workspace = Workspace(name=payload.name.strip(), owner_id=user.id)
    db.add(workspace); db.flush()
    db.add(Membership(workspace_id=workspace.id, user_id=user.id, role='owner'))
    audit(db, workspace.id, user.id, 'workspace.created', 'workspace', workspace.id)
    db.commit(); db.refresh(workspace)
    return {"id": workspace.id, "name": workspace.name, "role": "owner"}

@app.get('/workspaces')
def list_workspaces(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Workspace, Membership.role).join(Membership, Membership.workspace_id == Workspace.id).where(Membership.user_id == user.id)).all()
    return [{"id": w.id, "name": w.name, "role": role} for w, role in rows]

@app.post('/workspaces/{workspace_id}/projects')
def create_project(workspace_id: str, payload: ProjectIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member = membership(db, workspace_id, user.id); require_role(member, 'owner', 'manager')
    project = Project(workspace_id=workspace_id, name=payload.name.strip(), description=payload.description)
    db.add(project); db.flush(); audit(db, workspace_id, user.id, 'project.created', 'project', project.id); db.commit(); db.refresh(project)
    return project_dict(project)

@app.get('/workspaces/{workspace_id}/projects')
def list_projects(workspace_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    membership(db, workspace_id, user.id)
    rows = db.scalars(select(Project).where(Project.workspace_id == workspace_id, Project.archived.is_(False)).order_by(Project.created_at.desc())).all()
    return [project_dict(x) for x in rows]

@app.post('/projects/{project_id}/tasks')
def create_task(project_id: str, payload: TaskIn, idempotency_key: str | None = Header(None, alias='Idempotency-Key'), user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project or project.archived: raise HTTPException(status_code=404, detail='project-not-found')
    member = membership(db, project.workspace_id, user.id); require_role(member, 'owner', 'manager', 'member')
    if idempotency_key:
        existing = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.actor_id == user.id, IdempotencyRecord.key == idempotency_key))
        if existing:
            existing_task = db.get(Task, existing.task_id)
            if existing_task: return task_dict(existing_task)
            db.delete(existing); db.flush()
    if payload.assignee_id and not db.scalar(select(Membership).where(Membership.workspace_id == project.workspace_id, Membership.user_id == payload.assignee_id)):
        raise HTTPException(status_code=400, detail='assignee-not-in-workspace')
    task = Task(project_id=project.id, workspace_id=project.workspace_id, assignee_id=payload.assignee_id, title=payload.title, description=payload.description, status=payload.status, priority=payload.priority, due_date=payload.due_date)
    db.add(task); db.flush()
    if idempotency_key: db.add(IdempotencyRecord(actor_id=user.id, key=idempotency_key, task_id=task.id))
    audit(db, project.workspace_id, user.id, 'task.created', 'task', task.id); db.commit(); db.refresh(task)
    return task_dict(task)

@app.get('/projects/{project_id}/tasks')
def list_tasks(project_id: str, status_filter: str | None = Query(None, alias='status'), priority: str | None = None, assignee_id: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project: raise HTTPException(status_code=404, detail='project-not-found')
    membership(db, project.workspace_id, user.id)
    stmt = select(Task).where(Task.project_id == project_id, Task.archived.is_(False))
    if status_filter: stmt = stmt.where(Task.status == status_filter)
    if priority: stmt = stmt.where(Task.priority == priority)
    if assignee_id: stmt = stmt.where(Task.assignee_id == assignee_id)
    return [task_dict(x) for x in db.scalars(stmt.order_by(Task.created_at.desc())).all()]

@app.patch('/tasks/{task_id}')
def update_task(task_id: str, payload: TaskPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task: raise HTTPException(status_code=404, detail='task-not-found')
    member = membership(db, task.workspace_id, user.id)
    if member.role == 'member' and task.assignee_id != user.id: raise HTTPException(status_code=403, detail='member-cannot-edit-unassigned-task')
    if payload.assignee_id and not db.scalar(select(Membership).where(Membership.workspace_id == task.workspace_id, Membership.user_id == payload.assignee_id)): raise HTTPException(status_code=400, detail='assignee-not-in-workspace')
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(task, key, value)
    audit(db, task.workspace_id, user.id, 'task.updated', 'task', task.id); db.commit(); db.refresh(task)
    return task_dict(task)

@app.post('/tasks/{task_id}/comments')
def add_comment(task_id: str, payload: CommentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task: raise HTTPException(status_code=404, detail='task-not-found')
    membership(db, task.workspace_id, user.id)
    comment = Comment(task_id=task.id, author_id=user.id, body=payload.body)
    db.add(comment); db.flush(); audit(db, task.workspace_id, user.id, 'comment.created', 'comment', comment.id); db.commit(); db.refresh(comment)
    return {"id": comment.id, "body": comment.body, "author_id": comment.author_id, "created_at": comment.created_at}

@app.get('/dashboard/{workspace_id}')
def dashboard(workspace_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    membership(db, workspace_id, user.id)
    projects = db.scalar(select(func.count(Project.id)).where(Project.workspace_id == workspace_id, Project.archived.is_(False))) or 0
    tasks = db.scalar(select(func.count(Task.id)).where(Task.workspace_id == workspace_id, Task.archived.is_(False))) or 0
    open_tasks = db.scalar(select(func.count(Task.id)).where(Task.workspace_id == workspace_id, Task.archived.is_(False), Task.status != 'done')) or 0
    return {"projects": projects, "tasks": tasks, "open_tasks": open_tasks}

def project_dict(p: Project): return {"id": p.id, "name": p.name, "description": p.description, "workspace_id": p.workspace_id, "archived": p.archived}
def task_dict(t: Task): return {"id": t.id, "project_id": t.project_id, "title": t.title, "description": t.description, "assignee_id": t.assignee_id, "status": t.status, "priority": t.priority, "due_date": t.due_date, "archived": t.archived}