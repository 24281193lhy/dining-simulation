import pytest
import json
from unittest.mock import MagicMock, patch
from monitor import web_monitor


# 每个测试前后重置全局状态
@pytest.fixture(autouse=True)
def reset_globals():
    web_monitor._adapter = None
    web_monitor._scheduler = None
    web_monitor._reset_callback = None
    web_monitor.snapshots.clear()
    yield
    web_monitor._adapter = None
    web_monitor._scheduler = None
    web_monitor._reset_callback = None
    web_monitor.snapshots.clear()


# 辅助函数：构造模拟适配器和调度器
def mock_adapter():
    adapter = MagicMock()
    adapter.list_canteens.return_value = [
        {"canteen_id": 1, "name": "一食堂"},
        {"canteen_id": 2, "name": "二食堂"}
    ]
    adapter.add_canteen.return_value = 3
    adapter.add_window.return_value = "1_2"
    adapter.add_dish.return_value = True
    # 为 api_list_window_names 准备 cm 结构
    cm = MagicMock()
    canteen = MagicMock()
    window1 = MagicMock()
    window1.name = "窗口A"
    window2 = MagicMock()
    window2.name = "窗口B"
    canteen.windows = {1: window1, 2: window2}
    cm.canteens = {1: canteen}
    adapter.cm = cm
    return adapter


def mock_scheduler():
    scheduler = MagicMock()
    scheduler.is_running = False
    scheduler.paused = False
    scheduler.current_time = 100
    return scheduler


# ========== 全局设置函数 ==========
class TestGlobalSetters:
    def test_set_adapter(self):
        obj = object()
        web_monitor.set_adapter(obj)
        assert web_monitor._adapter is obj

    def test_set_scheduler(self):
        obj = object()
        web_monitor.set_scheduler(obj)
        assert web_monitor._scheduler is obj

    def test_set_reset_callback(self):
        cb = lambda: None
        web_monitor.set_reset_callback(cb)
        assert web_monitor._reset_callback is cb

    def test_clear_snapshots(self):
        web_monitor.snapshots.append("test")
        web_monitor.clear_snapshots()
        assert len(web_monitor.snapshots) == 0


# ========== 首页 ==========
class TestIndexRoute:
    @patch('monitor.web_monitor.render_template')
    def test_index(self, mock_render):
        mock_render.return_value = "<html>fake</html>"
        with web_monitor.app.test_client() as client:
            resp = client.get('/')
            assert resp.status_code == 200
            mock_render.assert_called_with('dashboard.html')


# ========== Socket.IO 事件处理 ==========
class TestSocketIOEvents:
    @patch('monitor.web_monitor.emit')
    def test_handle_connect(self, mock_emit):
        web_monitor.snapshots.extend(['snap1', 'snap2'])
        web_monitor.handle_connect()
        mock_emit.assert_called_once_with('history', ['snap1', 'snap2'])

    @patch('monitor.web_monitor.socketio.emit')
    def test_push_snapshot(self, mock_emit):
        data = {'time': 1, 'data': 'x'}
        web_monitor.push_snapshot(data)
        mock_emit.assert_called_once_with('update', data)
        assert len(web_monitor.snapshots) == 1
        assert web_monitor.snapshots[0] == data

    @patch('monitor.web_monitor.socketio.emit')
    def test_push_user_activity(self, mock_emit):
        web_monitor.push_user_activity('U1', '开始打饭', timestamp=125)
        expected_time = '02:05'   # 125分钟 = 2小时5分钟
        mock_emit.assert_called_once_with('user_activity', {
            'time': expected_time,
            'user_id': 'U1',
            'detail': '开始打饭'
        })

    @patch('monitor.web_monitor.socketio.emit')
    def test_push_simulation_summary(self, mock_emit):
        stats = {'total': 100}
        web_monitor.push_simulation_summary(stats)
        mock_emit.assert_called_once_with('simulation_end', stats)

    @patch('monitor.web_monitor.socketio.emit')
    def test_push_final_statistics(self, mock_emit):
        stats = {'avg_wait': 12.3}
        web_monitor.push_final_statistics(stats)
        mock_emit.assert_called_once_with('final_statistics', stats)


# ========== API：食堂列表 ==========
class TestAPICanteens:
    def test_with_adapter(self):
        web_monitor.set_adapter(mock_adapter())
        with web_monitor.app.test_client() as client:
            resp = client.get('/api/canteens')
            data = json.loads(resp.data)
            assert len(data) == 2
            assert data[0]['name'] == '一食堂'

    def test_no_adapter(self):
        with web_monitor.app.test_client() as client:
            resp = client.get('/api/canteens')
            data = json.loads(resp.data)
            assert data == []


# ========== API：添加食堂 ==========
class TestAPICanteenAdd:
    def test_success(self):
        web_monitor.set_adapter(mock_adapter())
        web_monitor.set_scheduler(mock_scheduler())
        with web_monitor.app.test_client() as client:
            resp = client.post('/api/canteen/add',
                               data=json.dumps({"name": "新食堂", "total_seats": 200}),
                               content_type='application/json')
            data = json.loads(resp.data)
            assert data['canteen_id'] == 3

    def test_missing_name(self):
        web_monitor.set_adapter(mock_adapter())
        with web_monitor.app.test_client() as client:
            resp = client.post('/api/canteen/add',
                               data=json.dumps({"total_seats": 200}),
                               content_type='application/json')
            assert resp.status_code == 400

    def test_running_not_paused(self):
        adapter = mock_adapter()
        sched = mock_scheduler()
        sched.is_running = True
        sched.paused = False
        web_monitor.set_adapter(adapter)
        web_monitor.set_scheduler(sched)
        with web_monitor.app.test_client() as client:
            resp = client.post('/api/canteen/add',
                               data=json.dumps({"name": "新食堂"}),
                               content_type='application/json')
            assert resp.status_code == 403

    def test_no_adapter(self):
        with web_monitor.app.test_client() as client:
            resp = client.post('/api/canteen/add',
                               data=json.dumps({"name": "食堂"}),
                               content_type='application/json')
            assert resp.status_code == 500


# ========== API：添加窗口 ==========
class TestAPIWindowAdd:
    def test_success(self):
        web_monitor.set_adapter(mock_adapter())
        with web_monitor.app.test_client() as client:
            resp = client.post('/api/window/add',
                               data=json.dumps({"canteen_id": 1, "name": "新窗口", "speed": 1.5}),
                               content_type='application/json')
            data = json.loads(resp.data)
            assert data['window_global_id'] == "1_2"

    def test_missing_params(self):
        web_monitor.set_adapter(mock_adapter())
        with web_monitor.app.test_client() as client:
            resp = client.post('/api/window/add',
                               data=json.dumps({"name": "新窗口"}),
                               content_type='application/json')
            assert resp.status_code == 400

    def test_running(self):
        web_monitor.set_adapter(mock_adapter())
        sched = mock_scheduler()
        sched.is_running = True
        sched.paused = False
        web_monitor.set_scheduler(sched)
        with web_monitor.app.test_client() as client:
            resp = client.post('/api/window/add',
                               data=json.dumps({"canteen_id": 1, "name": "窗口"}),
                               content_type='application/json')
            assert resp.status_code == 403


# ========== API：添加菜品 ==========
class TestAPIDishAdd:
    def test_success(self):
        web_monitor.set_adapter(mock_adapter())
        with web_monitor.app.test_client() as client:
            resp = client.post('/api/dish/add',
                               data=json.dumps({"window_global_id": "1_2", "dish_name": "红烧肉", "price": 12.5}),
                               content_type='application/json')
            data = json.loads(resp.data)
            assert data['success'] == True

    def test_missing_params(self):
        web_monitor.set_adapter(mock_adapter())
        with web_monitor.app.test_client() as client:
            resp = client.post('/api/dish/add',
                               data=json.dumps({"window_global_id": "1_2", "price": 12.5}),
                               content_type='application/json')
            assert resp.status_code == 400

    def test_running(self):
        web_monitor.set_adapter(mock_adapter())
        sched = mock_scheduler()
        sched.is_running = True
        sched.paused = False
        web_monitor.set_scheduler(sched)
        with web_monitor.app.test_client() as client:
            resp = client.post('/api/dish/add',
                               data=json.dumps({"window_global_id": "1_2", "dish_name": "红烧肉", "price": 12.5}),
                               content_type='application/json')
            assert resp.status_code == 403


# ========== API：窗口名称列表 ==========
class TestAPIWindowsList:
    def test_list(self):
        web_monitor.set_adapter(mock_adapter())
        with web_monitor.app.test_client() as client:
            resp = client.get('/api/windows')
            data = json.loads(resp.data)
            assert set(data) == {"窗口A", "窗口B"}


# ========== API：仿真控制 ==========
class TestSimulationControl:
    def test_pause(self):
        sched = mock_scheduler()
        web_monitor.set_scheduler(sched)
        with web_monitor.app.test_client() as client:
            resp = client.post('/api/simulation/control',
                               data=json.dumps({"action": "pause"}),
                               content_type='application/json')
            sched.pause.assert_called_once()
            assert json.loads(resp.data)['status'] == 'ok'

    def test_invalid_action(self):
        web_monitor.set_scheduler(mock_scheduler())
        with web_monitor.app.test_client() as client:
            resp = client.post('/api/simulation/control',
                               data=json.dumps({"action": "jump"}),
                               content_type='application/json')
            assert resp.status_code == 400

    def test_no_scheduler(self):
        with web_monitor.app.test_client() as client:
            resp = client.post('/api/simulation/control',
                               data=json.dumps({"action": "pause"}),
                               content_type='application/json')
            assert resp.status_code == 500


# ========== API：仿真状态 ==========
class TestSimulationStatus:
    def test_status(self):
        sched = MagicMock()
        sched.is_running = True
        sched.paused = False
        sched.current_time = 42
        web_monitor.set_scheduler(sched)
        with web_monitor.app.test_client() as client:
            resp = client.get('/api/simulation/status')
            data = json.loads(resp.data)
            assert data == {'running': True, 'paused': False, 'current_time': 42}

    def test_no_scheduler(self):
        with web_monitor.app.test_client() as client:
            resp = client.get('/api/simulation/status')
            data = json.loads(resp.data)
            assert data == {'running': False, 'paused': False}


# ========== API：重置仿真 ==========
class TestResetSimulation:
    def test_with_callback(self):
        cb = MagicMock()
        web_monitor.set_reset_callback(cb)
        with web_monitor.app.test_client() as client:
            resp = client.post('/api/simulation/reset')
            cb.assert_called_once()
            assert json.loads(resp.data)['status'] == 'reset initiated'

    def test_no_callback(self):
        with web_monitor.app.test_client() as client:
            resp = client.post('/api/simulation/reset')
            assert resp.status_code == 500