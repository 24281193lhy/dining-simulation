# 文件路径: monitor/web_monitor.py
import threading
from collections import deque
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os

# 获取模板文件夹路径
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates')
app = Flask(__name__, template_folder=template_dir)
socketio = SocketIO(app, cors_allowed_origins="*")

# 存储最近 200 个快照
MAX_SNAPSHOTS = 200
snapshots = deque(maxlen=MAX_SNAPSHOTS)

# 全局适配器（用于配置操作）
_adapter = None
# 全局调度器（用于控制仿真）
_scheduler = None
# 重置回调函数（由 main.py 设置）
_reset_callback = None

def set_adapter(adapter):
    global _adapter
    _adapter = adapter

def set_scheduler(scheduler):
    global _scheduler
    _scheduler = scheduler

def set_reset_callback(callback):
    global _reset_callback
    _reset_callback = callback

@app.route('/')
def index():
    return render_template('dashboard.html')

@socketio.on('connect')
def handle_connect():
    emit('history', list(snapshots))

def push_snapshot(data):
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
    """推送仿真结束摘要到所有客户端"""
    socketio.emit('simulation_end', stats)

def start_monitor(port=5000):
    def run():
        socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
    thread = threading.Thread(target=run, daemon=True)
    thread.start()

# ========== API：食堂与窗口配置 ==========
@app.route('/api/canteens')
def api_list_canteens():
    if _adapter is None:
        return jsonify([])
    canteens = _adapter.list_canteens()
    return jsonify(canteens)

@app.route('/api/canteen/add', methods=['POST'])
def api_add_canteen():
    if _adapter is None:
        return jsonify({'error': 'adapter not ready'}), 500
    data = request.get_json()
    name = data.get('name')
    total_seats = data.get('total_seats', 100)
    if not name:
        return jsonify({'error': 'name required'}), 400
    # 如果仿真正在运行且未暂停，禁止添加
    if _scheduler and _scheduler.is_running and not _scheduler.paused:
        return jsonify({'error': 'Simulation is running, please pause or stop first'}), 403
    cid = _adapter.add_canteen(name, total_seats)
    return jsonify({'canteen_id': cid})

@app.route('/api/window/add', methods=['POST'])
def api_add_window():
    if _adapter is None:
        return jsonify({'error': 'adapter not ready'}), 500
    data = request.get_json()
    canteen_id = data.get('canteen_id')
    name = data.get('name')
    speed = data.get('speed', 1.0)
    window_type = data.get('window_type', 'normal')
    if not canteen_id or not name:
        return jsonify({'error': 'canteen_id and name required'}), 400
    if _scheduler and _scheduler.is_running and not _scheduler.paused:
        return jsonify({'error': 'Simulation is running, please pause or stop first'}), 403
    global_id = _adapter.add_window(canteen_id, name, speed, window_type)
    if global_id:
        return jsonify({'window_global_id': global_id})
    else:
        return jsonify({'error': 'add window failed'}), 400

@app.route('/api/dish/add', methods=['POST'])
def api_add_dish():
    if _adapter is None:
        return jsonify({'error': 'adapter not ready'}), 500
    data = request.get_json()
    window_global_id = data.get('window_global_id')
    dish_name = data.get('dish_name')
    price = data.get('price')
    if not window_global_id or not dish_name or price is None:
        return jsonify({'error': 'window_global_id, dish_name, price required'}), 400
    if _scheduler and _scheduler.is_running and not _scheduler.paused:
        return jsonify({'error': 'Simulation is running, please pause or stop first'}), 403
    success = _adapter.add_dish(window_global_id, dish_name, price)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'add dish failed'}), 400

# ========== API：窗口名称列表（用于动态图表） ==========
@app.route('/api/windows')
def api_list_window_names():
    if _adapter is None:
        return jsonify([])
    names = set()
    for canteen in _adapter.cm.canteens.values():
        for window in canteen.windows.values():
            names.add(window.name)
    return jsonify(sorted(list(names)))

# ========== API：仿真控制 ==========
@app.route('/api/simulation/control', methods=['POST'])
def control_simulation():
    if _scheduler is None:
        return jsonify({'error': 'scheduler not ready'}), 500
    data = request.get_json()
    action = data.get('action')
    if action == 'pause':
        _scheduler.pause()
    elif action == 'resume':
        _scheduler.resume()
    elif action == 'stop':
        _scheduler.stop()
    else:
        return jsonify({'error': 'invalid action'}), 400
    return jsonify({'status': 'ok'})

@app.route('/api/simulation/status')
def simulation_status():
    if _scheduler is None:
        return jsonify({'running': False, 'paused': False})
    return jsonify({
        'running': _scheduler.is_running,
        'paused': _scheduler.paused,
        'current_time': _scheduler.current_time
    })

# ========== API：重置仿真 ==========
@app.route('/api/simulation/reset', methods=['POST'])
def reset_simulation():
    if _reset_callback is None:
        return jsonify({'error': 'reset callback not registered'}), 500
    _reset_callback()
    return jsonify({'status': 'reset initiated'})

# 在 web_monitor.py 添加路由
@app.route('/api/statistics')
def api_get_statistics():
    if _adapter is None:
        return jsonify({'error': 'adapter not ready'}), 500
    # 从存储中获取最终统计
    # 需要访问 storage，但 _adapter 没有直接暴露 storage
    # 简便方法：在 main.py 中设置全局 storage 引用，或通过 _adapter 获取
    # 这里假设我们已经在 main.py 中设置了全局 storage 引用
    # 为了简单，我们直接让 main.py 在仿真结束时将统计结果推送到前端，而不是轮询
    pass

def push_final_statistics(stats):
    """仿真结束时向所有连接的客户端推送最终统计结果"""
    socketio.emit('final_statistics', stats)

def clear_snapshots():
    """清空快照历史，用于重置"""
    snapshots.clear()