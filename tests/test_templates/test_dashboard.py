# tests/test_dashboard.py

import pytest
from flask import render_template
from monitor import web_monitor


class TestDashboardTemplate:
    """测试 dashboard.html 是否能正确渲染并包含必要元素"""

    @pytest.fixture(autouse=True)
    def app_context(self):
        """每个测试都在 Flask 应用上下文中运行"""
        with web_monitor.app.app_context():
            yield

    def test_template_renders_without_error(self):
        """确保 render_template 不会抛出异常"""
        try:
            html = render_template('dashboard.html')
        except Exception as e:
            pytest.fail(f"渲染模板失败: {e}")
        assert isinstance(html, str)
        assert len(html) > 0

    def test_page_title(self):
        html = render_template('dashboard.html')
        assert '北京交通大学食堂仿真' in html
        assert '<title>🍽️ 北京交通大学食堂仿真</title>' in html

    def test_control_buttons_present(self):
        html = render_template('dashboard.html')
        # 四个主要控制按钮
        assert 'id="btn-start"' in html
        assert 'id="btn-pause"' in html
        assert 'id="btn-stop"' in html
        assert 'id="btn-reset"' in html

    def test_chart_canvases_present(self):
        html = render_template('dashboard.html')
        assert 'id="servedChart"' in html
        assert 'id="queueChart"' in html
        assert 'id="barChart"' in html

    def test_activity_feed_present(self):
        html = render_template('dashboard.html')
        assert 'id="activity-feed"' in html
        assert 'id="activity-count"' in html

    def test_config_panel_present(self):
        html = render_template('dashboard.html')
        assert 'id="config-panel"' in html
        assert 'id="canteen-name"' in html
        assert 'id="window-canteen-select"' in html
        assert 'id="dish-name"' in html

    def test_stats_panel_present(self):
        html = render_template('dashboard.html')
        assert 'id="current-time"' in html
        assert 'id="total-served"' in html
        assert 'id="avg-wait"' in html

    def test_debug_panel_present(self):
        html = render_template('dashboard.html')
        assert 'id="conn-status"' in html
        assert 'id="last-data"' in html
        assert 'id="error-msg"' in html

    def test_final_statistics_section(self):
        html = render_template('dashboard.html')
        assert 'id="final-stats"' in html
        assert '等待仿真结束' in html

    def test_cdn_scripts_included(self):
        html = render_template('dashboard.html')
        # 确认引用了 Socket.IO 和 Chart.js CDN
        assert 'socket.io/4.5.0/socket.io.min.js' in html
        assert 'Chart.js/3.9.1/chart.min.js' in html

    def test_inline_script_contains_init(self):
        html = render_template('dashboard.html')
        # 确认内联 JavaScript 中有初始化逻辑
        assert 'const socket = io();' in html
        assert 'async function rebuildCharts()' in html
        assert 'socket.on(' in html