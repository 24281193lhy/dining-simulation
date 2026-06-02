# 2.3 座位管理模块
import random
import threading


class SeatManager:
    """座位管理器，负责分配和释放座位（线程安全）"""

    def __init__(self, canteen):
        self.canteen = canteen
        self._lock = threading.Lock()          # 保护所有座位分配操作

    # ──────────────────────────────
    # 座位分配
    # ──────────────────────────────

    def assign_seat(self, user, strategy='nearest'):
        """分配座位，返回 Seat 或 None"""
        with self._lock:
            available = self.canteen.available_seats()
            if not available:
                return None

            if strategy == 'random':
                seat = random.choice(available)
            else:
                seat = available[0]            # 就近

            # 原子占用
            seat.occupy(user)
            user.current_seat = seat
            return seat

    def assign_specific_seat(self, user, seat_id):
        """指定座位号分配"""
        with self._lock:
            seat = self._get_seat(seat_id)
            if seat is None:
                # print(f"❌ 座位{seat_id}不存在")
                return None
            if seat.is_occupied:
                # print(f"❌ 座位{seat_id}已被占用")
                return None

            seat.occupy(user)
            user.current_seat = seat
            return seat

    # ──────────────────────────────
    # 座位释放
    # ──────────────────────────────

    def release_seat(self, user):
        """释放用户当前座位"""
        with self._lock:
            seat = user.current_seat
            if seat is None:
                return False

            # 防御：确认该座位确属该用户（避免释放其他用户的座位）
            if seat.occupant is not user:
                # 可能已被其他线程修改，重置状态
                user.current_seat = None
                return False

            seat.release()
            user.current_seat = None
            return True

    def release_seat_by_id(self, seat_id):
        """按座位 ID 强制释放"""
        with self._lock:
            seat = self._get_seat(seat_id)
            if seat is None:
                return False
            if not seat.is_occupied:
                return False

            user = seat.occupant
            if user:
                user.current_seat = None
            seat.release()
            return True

    # ──────────────────────────────
    # 状态查询（读操作，可加锁也可不加，但建议加锁以保证一致性）
    # ──────────────────────────────

    def get_status(self):
        with self._lock:
            total = len(self.canteen.seats)
            occupied = len(self.canteen.occupied_seats())
            available = total - occupied
            return {
                'total': total,
                'occupied': occupied,
                'available': available,
                'rate': occupied / total * 100 if total > 0 else 0
            }

    def print_status(self):
        s = self.get_status()
        print(f"── {self.canteen.name} 座位状态 ──")
        print(f"  总座位: {s['total']}")
        print(f"  已占用: {s['occupied']}")
        print(f"  空余:   {s['available']}")
        print(f"  占用率: {s['rate']:.1f}%")

    def print_all_seats(self):
        with self._lock:                       # 防止遍历期间状态变化
            print(f"── {self.canteen.name} 全部座位 ──")
            for seat in self.canteen.seats:
                print(f"  {seat}")

    # ──────────────────────────────
    # 内部工具
    # ──────────────────────────────

    def _get_seat(self, seat_id):
        """内部用，不加锁（由上层调用者保证锁）"""
        for seat in self.canteen.seats:
            if seat.seat_id == seat_id:
                return seat
        return None

#A