from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.models import AuditEvent
from app.db import Base, get_db

engine = create_engine('sqlite:///./test_taskflow.db', connect_args={'check_same_thread': False})
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.drop_all(engine); Base.metadata.create_all(engine)

def override_db():
    db = TestingSession()
    try: yield db
    finally: db.close()

app.dependency_overrides[get_db] = override_db
client = TestClient(app)

def register(email, name):
    r = client.post('/auth/register', json={'email': email, 'password': 'Password123!', 'name': name})
    assert r.status_code == 200
    return r.json()

def auth(token): return {'Authorization': 'Bearer ' + token}

def test_tenant_and_rbac_boundaries():
    alice = register('alice@example.com', 'Alice')
    bob = register('bob@example.com', 'Bob')
    ws = client.post('/workspaces', json={'name': 'Alice Team'}, headers=auth(alice['token'])).json()
    denied = client.get('/workspaces/' + ws['id'] + '/projects', headers=auth(bob['token']))
    assert denied.status_code == 403
    project = client.post('/workspaces/' + ws['id'] + '/projects', json={'name': 'Website'}, headers=auth(alice['token']))
    assert project.status_code == 200
    project_id = project.json()['id']
    assert client.get('/projects/' + project_id + '/tasks', headers=auth(bob['token'])).status_code == 403
    task = client.post('/projects/' + project_id + '/tasks', json={'title': 'Ship homepage', 'assignee_id': bob['user_id']}, headers=auth(alice['token']))
    assert task.status_code == 400

def test_auth_rejection_and_revocation():
    user = register('revoked@example.com', 'Revoked')
    assert client.get('/me', headers=auth(user['token'])).status_code == 200
    assert client.post('/auth/logout', headers=auth(user['token'])).status_code == 200
    assert client.get('/me', headers=auth(user['token'])).status_code == 401
    assert client.get('/me', headers=auth('not-a-real-token')).status_code == 401

def test_idempotent_task_creation():
    user = register('idem@example.com', 'Idempotent')
    ws = client.post('/workspaces', json={'name': 'Idempotency'}, headers=auth(user['token'])).json()
    project = client.post('/workspaces/' + ws['id'] + '/projects', json={'name': 'Idempotent Project'}, headers=auth(user['token'])).json()
    headers = {**auth(user['token']), 'Idempotency-Key': 'task-create-001'}
    first = client.post('/projects/' + project['id'] + '/tasks', json={'title': 'Exactly once'}, headers=headers)
    second = client.post('/projects/' + project['id'] + '/tasks', json={'title': 'Exactly once'}, headers=headers)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()['id'] == second.json()['id']
    db = TestingSession()
    try:
        assert db.query(AuditEvent).filter(AuditEvent.workspace_id == ws['id'], AuditEvent.action == 'task.created').count() == 1
    finally:
        db.close()

def test_task_lifecycle_and_audit_effect():
    user = register('carol@example.com', 'Carol')
    ws = client.post('/workspaces', json={'name': 'Delivery'}, headers=auth(user['token'])).json()
    project = client.post('/workspaces/' + ws['id'] + '/projects', json={'name': 'Release'}, headers=auth(user['token'])).json()
    created = client.post('/projects/' + project['id'] + '/tasks', json={'title': 'Verify build', 'priority': 'high'}, headers=auth(user['token']))
    assert created.status_code == 200
    task_id = created.json()['id']
    updated = client.patch('/tasks/' + task_id, json={'status': 'done'}, headers=auth(user['token']))
    assert updated.status_code == 200 and updated.json()['status'] == 'done'
    dashboard = client.get('/dashboard/' + ws['id'], headers=auth(user['token']))
    assert dashboard.status_code == 200 and dashboard.json()['tasks'] == 1 and dashboard.json()['open_tasks'] == 0
    db = TestingSession()
    try:
        assert db.query(AuditEvent).filter(AuditEvent.workspace_id == ws['id']).count() >= 3
    finally:
        db.close()
