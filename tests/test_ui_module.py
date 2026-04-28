import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

import unittest
from unittest.mock import Mock, patch

from ui.common import validate_student_id, validate_teacher_id
from ui.student_ui import StudentUI
from ui.admin_ui import AdminUI


class TestCommon(unittest.TestCase):
    def test_validate_student_id(self):
        # 正确格式
        self.assertTrue(validate_student_id("23010101"))
        # 错误格式
        self.assertFalse(validate_student_id("2301010"))   # 长度不足
        self.assertFalse(validate_student_id("21010101"))  # 年份<22
        self.assertFalse(validate_student_id("26010101"))  # 年份>25
        self.assertFalse(validate_student_id("23510101"))  # 学院>50
        self.assertFalse(validate_student_id("23000101"))  # 班级<1
        self.assertFalse(validate_student_id("23012101"))  # 班级>20
        self.assertFalse(validate_student_id("23a10101"))  # 非数字

    def test_validate_teacher_id(self):
        self.assertTrue(validate_teacher_id("T001"))
        self.assertTrue(validate_teacher_id("T1"))
        self.assertTrue(validate_teacher_id("t001"))   # 不区分大小写
        self.assertFalse(validate_teacher_id("AT001"))
        self.assertFalse(validate_teacher_id("T"))


class TestStudentUI(unittest.TestCase):
    def setUp(self):
        self.mock_cm = Mock()
        self.mock_qe = Mock()
        self.mock_sm = Mock()
        self.mock_storage = Mock()
        self.student_ui = StudentUI(
            self.mock_cm, self.mock_qe, self.mock_sm, self.mock_storage
        )

    def test_show_canteen_overview(self):
        fake_canteens = [
            {"id": 1, "name": "学一", "free_seats": 100, "total_queue": 5,
             "windows": [{"id": "1_1", "name": "窗口1", "type": "普通", "queue_len": 2, "wait_time": 30}]}
        ]
        self.mock_cm.get_all_canteens_status.return_value = fake_canteens
        self.student_ui.current_user_obj = Mock()
        with patch('ui.student_ui.print_header'), patch('ui.student_ui.print_table'):
            self.student_ui.show_canteen_overview()
        self.mock_cm.get_all_canteens_status.assert_called_once_with(user=self.student_ui.current_user_obj)

    def test_check_queue_status(self):
        self.mock_qe.get_user_queue_status.return_value = {
            "window_name": "窗口1", "ahead": 2, "wait_time": 45
        }
        self.student_ui.current_user = {"id": "S001"}
        with patch('ui.student_ui.print_info') as mock_print:
            self.student_ui.check_queue_status()
            mock_print.assert_called_once()
        self.mock_qe.get_user_queue_status.assert_called_once_with("S001")

    def test_leave_canteen(self):
        self.student_ui.current_canteen = {"id": 1, "name": "学一"}
        self.student_ui.current_user = {"id": "S001"}
        self.student_ui.leave_canteen()
        self.mock_sm.release_seat.assert_called_once_with("S001")
        self.mock_storage.log_event.assert_called_once()


class TestAdminUI(unittest.TestCase):
    def setUp(self):
        self.mock_cm = Mock()
        self.mock_storage = Mock()
        self.mock_admin_manager = Mock()
        self.admin_ui = AdminUI(self.mock_cm, self.mock_storage, self.mock_admin_manager)

    def test_view_canteens(self):
        fake_config = [
            {"id": 1, "name": "学一", "total_seats": 100,
             "windows": [{"id": "1_1", "name": "窗口1", "type": "普通", "speed": 1.0, "dishes": ["红烧肉"]}]}
        ]
        self.mock_cm.get_all_canteens_config.return_value = fake_config
        with patch('builtins.print'), patch('builtins.input', return_value=''):
            self.admin_ui.view_canteens()
        self.mock_cm.get_all_canteens_config.assert_called_once()


if __name__ == '__main__':
    unittest.main()