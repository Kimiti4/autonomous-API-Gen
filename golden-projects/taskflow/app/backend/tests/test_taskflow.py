from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
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
    task = client.post('/projects/' + project.json()['id'] + '/tasks', json={'title': 'Ship homepage', 'assignee_id': bob['user_id']}, headers=auth(alice['token']))
    assert task.status_code == 400

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