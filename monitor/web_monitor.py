# 文件路径: monitor/web_monitor.py
import threading
from collections import deque
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# 获取当前文件所在目录的绝对路径，确保能找到 templates 文件夹
import os
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates')
app = Flask(__name__, template_folder=template_dir)
socketio = SocketIO(app, cors_allowed_origins="*")

# 存储最近 200 个快照，用于新客户端连接时回放历史数据
MAX_SNAPSHOTS = 200
snapshots = deque(maxlen=MAX_SNAPSHOTS)

@app.route('/')
def index():
    """仪表盘主页"""
    return render_template('dashboard.html')

@socketio.on('connect')
def handle_connect():
    """当浏览器客户端连接时，发送所有历史快照"""
    emit('history', list(snapshots))

def push_snapshot(data):
    """
    供仿真主线程调用的接口，将最新统计数据推送给所有连接的浏览器。
    data 应该是一个字典，例如：
    {
        "time": 15,
        "total_served": 120,
        "avg_wait": 3.5,
        "windows": {
            "快餐窗口": {"total_served": 50, "queue_length": 3},
            ...
        }
    }
    """
    snapshots.append(data)
    socketio.emit('update', data)

def start_monitor(port=5000):
    """在独立线程中启动 Flask + SocketIO 服务"""
    def run():
        # use_reloader=False 防止开启双进程
        socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
    thread = threading.Thread(target=run, daemon=True)
    thread.start()

def push_user_activity(user_id, detail, timestamp=None):
    """推送用户活动到前端活动流"""
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