import sys
import os
import uuid
import time
import queue
import threading
from flask import Flask, request, Response, stream_with_context, render_template, session, jsonify
from datetime import timedelta

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from backend import database as db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'qianwen-ai-chat-secret-key-2025')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# Handle URL Prefix /tinghai
class PrefixMiddleware(object):
    def __init__(self, app, prefix=''):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        if environ['PATH_INFO'].startswith(self.prefix):
            environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
            environ['SCRIPT_NAME'] = self.prefix
            return self.app(environ, start_response)
        else:
            # Fallback: Allow direct access if prefix is missing (for testing or misconfig)
            # print(f"[WARN] Prefix mismatch: {environ['PATH_INFO']} does not start with {self.prefix}")
            # start_response('404', [('Content-Type', 'text/plain')])
            # return [b"Not Found (Prefix Mismatch)"]
            return self.app(environ, start_response)

# Apply middleware only if URL_PREFIX env var is set
url_prefix = os.environ.get('URL_PREFIX', '')
if url_prefix:
    print(f"[INFO] Running with URL prefix: {url_prefix}")
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix=url_prefix)

# Global State
conversation_history = {} # session_id -> history list
agents = {}  # agent_id -> {"name": str, "account": str, "last_seen": ts}
pending_tasks = []  # List of tasks
task_waiters = {}  # task_id -> queue.Queue()
queue_lock = threading.RLock()
task_available = threading.Condition(queue_lock)

TASK_TIMEOUT = 900
AGENT_STALE_SEC = 120

def prune_stale_agents():
    """Remove stale agents"""
    now = time.time()
    stale = []
    with queue_lock:
        for aid, info in list(agents.items()):
            if now - info.get("last_seen", 0) > AGENT_STALE_SEC:
                stale.append(aid)
        for aid in stale:
            agents.pop(aid, None)
    if stale:
        print(f"[WARN] Removed stale agents: {stale}", flush=True)

@app.route('/')
def home():
    session.permanent = True
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')

# --- API for Frontend ---

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    account = data.get('account')
    password = data.get('password') # Password hash from frontend? Or plain password? Let's assume frontend sends plain text if HTTPS, or hash. 
    # For now, let's assume frontend sends what client sends (hash) or plain text.
    # Client sends SHA256 hash. Frontend should probably do the same or send plain text and backend hashes it.
    # But wait, frontend is for human. Human types password.
    # Let's simple hash it here if it's plain text, or expect hash.
    # To keep consistent with Client, let's say we expect the hash or hash it ourselves.
    # Client uses hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    if not account:
        return jsonify({'error': 'Account is required'}), 400
    
    # Check password if provided
    # If db.verify_user returns None (user not found), we can't login via Web until Client registers it?
    # OR we allow Web to register users too?
    # Requirement: "Web matches what Client sends". So Client must register first usually?
    # Or simultaneous.
    
    # If password is provided, verify it.
    if password:
        # We need to hash it to match what's stored (which is the hash from Client)
        # Client sends hash_password(password). 
        # So DB stores SHA256.
        # Frontend user types "123456". We should hash it here.
        import hashlib
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        valid = db.verify_user(account, password_hash)
        if valid is False:
            return jsonify({'error': 'Invalid password'}), 401
        elif valid is None:
             # User doesn't exist yet. 
             # Should we create it? 
             # If we create it, we set the password. Then Client must match it.
             # Let's allow registration from Web too.
             db.add_user(account, password_hash)
    else:
        # If no password provided, maybe check if user exists without password? 
        # Or require password.
        # Let's require password for security if we are doing this.
        # But for backward compatibility or ease, if no password in DB, maybe allow?
        pass

    session['account'] = account
    return jsonify({'status': 'ok', 'account': account})

@app.route('/api/groups', methods=['GET'])
def get_groups():
    account = session.get('account')
    if not account:
        return jsonify({'error': 'Not logged in'}), 401
    groups = db.get_groups(account)
    return jsonify(groups)

@app.route('/api/groups', methods=['POST'])
def save_group():
    account = session.get('account')
    if not account:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json() or {}
    group_id = data.get('id') or str(int(time.time()*1000))
    name = data.get('name')
    prompt = data.get('prompt')
    
    if not name:
        return jsonify({'error': 'Name is required'}), 400
        
    # Check if update or create
    existing = [g for g in db.get_groups(account) if g['id'] == group_id]
    if existing:
        db.update_group(group_id, account, name, prompt)
    else:
        db.add_group(group_id, account, name, prompt)
        
    return jsonify({'status': 'ok', 'id': group_id})

@app.route('/api/groups/<group_id>', methods=['DELETE'])
def delete_group(group_id):
    account = session.get('account')
    if not account:
        return jsonify({'error': 'Not logged in'}), 401
    db.delete_group(group_id, account)
    return jsonify({'status': 'ok'})

# --- Agent Protocol ---

@app.route('/agent/register', methods=['POST'])
def agent_register():
    data = request.get_json(silent=True) or {}
    name = data.get("name") or f"agent-{uuid.uuid4().hex[:6]}"
    account = data.get("account")
    password_hash = data.get("password")
    
    if not account:
        return jsonify({"error": "account required"}), 400
        
    # 1. Register/Verify User in DB
    if password_hash:
        valid = db.verify_user(account, password_hash)
        if valid is False: # Password mismatch
            print(f"[WARN] Agent register failed: Password mismatch for {account}", flush=True)
            return jsonify({"error": "Invalid password"}), 409
        elif valid is None: # New user
            db.add_user(account, password_hash)
            print(f"[INFO] Created new user from Agent: {account}", flush=True)
        # valid is True: password matches, proceed
    else:
        # Legacy agent without password? Or allow non-password?
        # Let's enforce password if the new client sends it.
        # If client sends no password, but DB has one, fail?
        pass

    agent_id = uuid.uuid4().hex
    now = time.time()
    with queue_lock:
        agents[agent_id] = {"name": name, "account": account, "last_seen": now}
    
    print(f"[INFO] Agent registered: {agent_id} ({name}) for account {account}", flush=True)
    return jsonify({"agent_id": agent_id, "name": name})

@app.route('/agent/heartbeat', methods=['POST'])
def agent_heartbeat():
    data = request.get_json(silent=True) or {}
    agent_id = data.get("agent_id")
    if not agent_id:
        return jsonify({"error": "agent_id required"}), 400
    with queue_lock:
        if agent_id not in agents:
            return jsonify({"error": "unknown agent"}), 404
        agents[agent_id]["last_seen"] = time.time()
    return jsonify({"status": "ok"})

@app.route('/agent/poll', methods=['POST'])
def agent_poll():
    data = request.get_json(silent=True) or {}
    agent_id = data.get("agent_id")
    if not agent_id:
        return jsonify({"error": "agent_id required"}), 400
        
    with queue_lock:
        if agent_id not in agents:
            return jsonify({"error": "unknown agent"}), 404
        agents[agent_id]["last_seen"] = time.time()
        agent_account = agents[agent_id]["account"]

        timeout_sec = 25
        end = time.time() + timeout_sec
        task = None
        
        while task is None:
            prune_stale_agents()
            
            # Find a task for this agent's account
            # We need to iterate pending_tasks and find one that matches or is generic?
            # For now, let's assume tasks are tagged with account.
            
            # Optimization: pending_tasks could be a list of dicts.
            # We search for the first task that matches the agent's account.
            match_index = -1
            for i, t in enumerate(pending_tasks):
                if t.get('account') == agent_account:
                    match_index = i
                    break
            
            if match_index != -1:
                task = pending_tasks.pop(match_index)
                break
                
            remaining = end - time.time()
            if remaining <= 0:
                break
            task_available.wait(timeout=remaining)

    if not task:
        return jsonify({"status": "no_task"}), 204

    return jsonify({
        "task_id": task["task_id"],
        "message": task["message"],
        "mentions": task["mentions"],
        "history": task["history"],
    })

@app.route('/agent/result', methods=['POST'])
def agent_result():
    data = request.get_json(silent=True) or {}
    agent_id = data.get("agent_id")
    task_id = data.get("task_id")
    result = data.get("result", "")
    
    if not agent_id or not task_id:
        return jsonify({"error": "args missing"}), 400
        
    with queue_lock:
        if agent_id not in agents:
            return jsonify({"error": "unknown agent"}), 404
        agents[agent_id]["last_seen"] = time.time()
        waiter = task_waiters.pop(task_id, None)
        
    if waiter:
        waiter.put(result)
        return jsonify({"status": "ok"})
    return jsonify({"error": "task_not_found"}), 404

# --- Chat Interface ---

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_msg = data.get('message', '')
    mentions = data.get('mentions', [])
    
    session_id = session.get('session_id', 'default')
    account = session.get('account')
    
    if not account:
        return jsonify({'error': 'Please login first'}), 401

    if session_id not in conversation_history:
        conversation_history[session_id] = []
    history = conversation_history[session_id]

    def generate():
        task_id = uuid.uuid4().hex
        waiter = queue.Queue(maxsize=1)
        
        # Check if agent online for this account
        with queue_lock:
            # Check if any agent is online for this account
            # Improvements: Could support multiple agents per account if needed (load balancing)
            online = any(a['account'] == account for a in agents.values())
        
        if not online:
            yield f"[Error: No Parse Client connected for account '{account}'. Please start your client.]"
            return

        with queue_lock:
            task_waiters[task_id] = waiter
            pending_tasks.append({
                "task_id": task_id,
                "account": account, # Bind task to account
                "message": user_msg,
                "mentions": mentions,
                "history": history,
            })
            task_available.notify_all()

        try:
            result = waiter.get(timeout=TASK_TIMEOUT)
            
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": result})
            
            # Trim history
            if len(history) > 20:
                history[:] = history[-20:]
            
            conversation_history[session_id] = history
            yield result
            
        except queue.Empty:
            yield "\n\n[Error: Timeout waiting for agent response]"
        finally:
            with queue_lock:
                task_waiters.pop(task_id, None)

    return Response(stream_with_context(generate()), mimetype='text/plain')

@app.route('/clear_history', methods=['POST'])
def clear_history():
    session_id = session.get('session_id', 'default')
    if session_id in conversation_history:
        count = len(conversation_history[session_id])
        del conversation_history[session_id]
        return jsonify({'status': 'ok', 'removed': count})
    return jsonify({'status': 'ok', 'removed': 0})

@app.route('/history_info', methods=['GET'])
def history_info():
    session_id = session.get('session_id', 'default')
    history = conversation_history.get(session_id, [])
    return jsonify({
        'session_id': session_id,
        'message_count': len(history),
        'conversation_rounds': len(history) // 2
    })

if __name__ == '__main__':
    db.init_db()
    print("Starting Server at http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
