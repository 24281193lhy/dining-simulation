# 2.3 座位管理模块
import random


class SeatManager:
    """座位管理器，负责分配和释放座位"""

    def __init__(self, canteen):
        self.canteen = canteen      # 关联的Canteen对象

    # ──────────────────────────────
    # 座位分配
    # ──────────────────────────────

    def assign_seat(self, user, strategy='nearest'):
        """
        为用户分配座位
        strategy: 'nearest' 就近(取编号最小的空位) / 'random' 随机分配
        返回：分配的Seat对象，或None（无空位）
        """
        available = self.canteen.available_seats()

        if not available:
            print(f"❌ '{self.canteen.name}'已无空余座位")
            return None

        if strategy == 'random':
            seat = random.choice(available)
        else:
            # 默认就近：取编号最小的空位
            seat = available[0]

        seat.occupy(user)
        user.current_seat = seat
        #print(f"✅ {user} 入座 → 座位{seat.seat_id}（{self.canteen.name}）")
        return seat

    def assign_specific_seat(self, user, seat_id):
        """用户自选指定座位"""
        seat = self._get_seat(seat_id)
        if seat is None:
            print(f"❌ 座位{seat_id}不存在")
            return None
        if seat.is_occupied:
            print(f"❌ 座位{seat_id}已被占用")
            return None

        seat.occupy(user)
        user.current_seat = seat
        print(f"✅ {user} 选择入座 → 座位{seat_id}（{self.canteen.name}）")
        return seat

    # ──────────────────────────────
    # 座位释放
    # ──────────────────────────────

    def release_seat(self, user):
        """用户离开，释放座位"""
        seat = user.current_seat
        if seat is None:
            print(f"⚠️ {user} 当前没有座位")
            return False

        seat.release()
        user.current_seat = None
        print(f"🚶 {user} 离座，座位{seat.seat_id}已释放")
        return True

    def release_seat_by_id(self, seat_id):
        """直接通过座位ID释放（管理员操作）"""
        seat = self._get_seat(seat_id)
        if seat is None:
            print(f"❌ 座位{seat_id}不存在")
            return False
        if not seat.is_occupied:
            print(f"⚠️ 座位{seat_id}本来就是空的")
            return False

        user = seat.occupant
        if user:
            user.current_seat = None
        seat.release()
        print(f"🔓 座位{seat_id}已强制释放")
        return True

    # ──────────────────────────────
    # 状态查询
    # ──────────────────────────────

    def get_status(self):
        """返回座位占用情况摘要"""
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
        """打印座位状态"""
        s = self.get_status()
        print(f"── {self.canteen.name} 座位状态 ──")
        print(f"  总座位: {s['total']}")
        print(f"  已占用: {s['occupied']}")
        print(f"  空余:   {s['available']}")
        print(f"  占用率: {s['rate']:.1f}%")

    def print_all_seats(self):
        """打印所有座位详细状态（管理员监控用）"""
        print(f"── {self.canteen.name} 全部座位 ──")
        for seat in self.canteen.seats:
            print(f"  {seat}")

    # ──────────────────────────────
    # 内部工具
    # ──────────────────────────────

    def _get_seat(self, seat_id):
        """通过seat_id获取Seat对象"""
        for seat in self.canteen.seats:
            if seat.seat_id == seat_id:
                return seat
        return None