# monitor/web_monitor.py
import threading
from collections import deque
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_dir = os.path.join(BASE_DIR, 'templates')
app = Flask(__name__, template_folder=template_dir)
socketio = SocketIO(app, cors_allowed_origins="*")

# ========== 线程安全快照存储 ==========
MAX_SNAPSHOTS = 200
snapshots = deque(maxlen=MAX_SNAPSHOTS)
snapshots_lock = threading.Lock()

# ========== 全局组件 ==========
_adapter = None
_scheduler = None
_reset_callback = None
_storage = None
_globals_lock = threading.Lock()

# 自动退出回调与客户端追踪
_auto_exit_callback = None
connected_clients = set()

def set_adapter(adapter):
    with _globals_lock:
        global _adapter
        _adapter = adapter

def set_scheduler(scheduler):
    with _globals_lock:
        global _scheduler
        _scheduler = scheduler

def set_reset_callback(callback):
    with _globals_lock:
        global _reset_callback
        _reset_callback = callback

def set_storage(storage):
    with _globals_lock:
        global _storage
        _storage = storage

def set_auto_exit_callback(callback):
    global _auto_exit_callback
    _auto_exit_callback = callback

def _get_adapter():
    with _globals_lock:
        return _adapter

def _get_scheduler():
    with _globals_lock:
        return _scheduler

def _get_storage():
    with _globals_lock:
        return _storage

# ========== 路由 ==========
@app.route('/')
def index():
    return render_template('dashboard.html')

@socketio.on('connect')
def handle_connect():
    connected_clients.add(request.sid)
    with snapshots_lock:
        history = list(snapshots)
    emit('history', history)

@socketio.on('disconnect')
def handle_disconnect():
    connected_clients.discard(request.sid)
    # 所有客户端都断开时触发自动退出
    if not connected_clients and _auto_exit_callback:
        _auto_exit_callback()

# ========== 推送函数（线程安全） ==========
def push_snapshot(data):
    with snapshots_lock:
        snapshots.append(data)
    socketio.emit('update', data)

def push_user_activity(user_id, detail, timestamp=None):
    from datetime import datetime
    if timestamp is None:
        time_str = datetime.now().strftime('%H:%M:%S')
    else:
        mins = int(timestamp)
        time_str = f"{mins//60:02d}:{mins%60:02d}"
    socketio.emit('user_activity', {
        'time': time_str,
        'user_id': user_id,
        'detail': detail
    })

def push_simulation_summary(stats):
    socketio.emit('simulation_end', stats)

def push_final_statistics(stats):
    socketio.emit('final_statistics', stats)

def clear_snapshots():
    with snapshots_lock:
        snapshots.clear()

# ========== 启动监控（后台线程） ==========
def start_monitor(port=5000):
    def run():
        socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
    thread = threading.Thread(target=run, daemon=True)
    thread.start()

# ========== API：食堂与窗口配置 ==========
@app.route('/api/canteens')
def api_list_canteens():
    adapter = _get_adapter()
    if adapter is None:
        return jsonify([])
    canteens = adapter.list_canteens()
    return jsonify(canteens)

@app.route('/api/canteen/add', methods=['POST'])
def api_add_canteen():
    adapter = _get_adapter()
    if adapter is None:
        return jsonify({'error': 'adapter not ready'}), 500
    scheduler = _get_scheduler()
    if scheduler and scheduler.is_running and not getattr(scheduler, 'paused', False):
        return jsonify({'error': 'Simulation is running, please pause or stop first'}), 403

    data = request.get_json()
    name = data.get('name')
    total_seats = data.get('total_seats', 100)
    if not name:
        return jsonify({'error': 'name required'}), 400
    cid = adapter.add_canteen(name, total_seats)
    return jsonify({'canteen_id': cid})

@app.route('/api/window/add', methods=['POST'])
def api_add_window():
    adapter = _get_adapter()
    if adapter is None:
        return jsonify({'error': 'adapter not ready'}), 500
    scheduler = _get_scheduler()
    if scheduler and scheduler.is_running and not getattr(scheduler, 'paused', False):
        return jsonify({'error': 'Simulation is running, please pause or stop first'}), 403

    data = request.get_json()
    canteen_id = data.get('canteen_id')
    name = data.get('name')
    speed = data.get('speed', 1.0)
    window_type = data.get('window_type', 'normal')
    if not canteen_id or not name:
        return jsonify({'error': 'canteen_id and name required'}), 400
    global_id = adapter.add_window(canteen_id, name, speed, window_type)
    if global_id:
        return jsonify({'window_global_id': global_id})
    else:
        return jsonify({'error': 'add window failed'}), 400

@app.route('/api/dish/add', methods=['POST'])
def api_add_dish():
    adapter = _get_adapter()
    if adapter is None:
        return jsonify({'error': 'adapter not ready'}), 500
    scheduler = _get_scheduler()
    if scheduler and scheduler.is_running and not getattr(scheduler, 'paused', False):
        return jsonify({'error': 'Simulation is running, please pause or stop first'}), 403

    data = request.get_json()
    window_global_id = data.get('window_global_id')
    dish_name = data.get('dish_name')
    price = data.get('price')
    if not window_global_id or not dish_name or price is None:
        return jsonify({'error': 'window_global_id, dish_name, price required'}), 400
    success = adapter.add_dish(window_global_id, dish_name, price)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'add dish failed'}), 400

# ========== API：窗口名称列表 ==========
@app.route('/api/windows')
def api_list_window_names():
    adapter = _get_adapter()
    if adapter is None:
        return jsonify([])
    names = set()
    for canteen in adapter.cm.canteens.values():
        for window in canteen.windows.values():
            names.add(window.name)
    return jsonify(sorted(list(names)))

# ========== API：仿真控制 ==========
@app.route('/api/simulation/control', methods=['POST'])
def control_simulation():
    scheduler = _get_scheduler()
    if scheduler is None:
        return jsonify({'error': 'scheduler not ready'}), 500
    data = request.get_json()
    action = data.get('action')
    if action == 'pause':
        scheduler.pause()
    elif action == 'resume':
        scheduler.resume()
    elif action == 'stop':
        scheduler.stop()
    else:
        return jsonify({'error': 'invalid action'}), 400
    return jsonify({'status': 'ok'})

@app.route('/api/simulation/status')
def simulation_status():
    scheduler = _get_scheduler()
    if scheduler is None:
        return jsonify({'running': False, 'paused': False})
    return jsonify({
        'running': scheduler.is_running,
        'paused': getattr(scheduler, 'paused', False),
        'current_time': scheduler.current_time
    })

# ========== API：重置仿真 ==========
@app.route('/api/simulation/reset', methods=['POST'])
def reset_simulation():
    callback = _reset_callback
    if callback is None:
        return jsonify({'error': 'reset callback not registered'}), 500
    callback()
    return jsonify({'status': 'reset initiated'})

# ========== API：获取统计 ==========
@app.route('/api/statistics')
def api_get_statistics():
    storage = _get_storage()
    if storage is None:
        return jsonify({'error': 'storage not available'}), 500
    try:
        from data.statistics import StatisticsAnalyzer
        analyzer = StatisticsAnalyzer(storage)
        stats = analyzer.compute_all()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500