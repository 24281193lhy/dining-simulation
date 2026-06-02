import webbrowser

from canteen_sim import simulation
from canteen_sim.admin import AdminManager
from canteen_sim.simulation import (
    load_config, init_simulation_context, reset_simulation,
    start_simulation,
)
from canteen_sim.monitor.web_monitor import (
    start_monitor, push_snapshot, set_adapter, set_scheduler,
    set_reset_callback, set_admin_manager, set_start_callback
)
from canteen_sim.data.statistics import StatisticsAnalyzer
from canteen_sim.utils.display import print_info, print_success, print_warning


def main():
    admin_manager = AdminManager()
    set_admin_manager(admin_manager)

    sim_cfg = load_config()
    sim_duration = sim_cfg["duration"]
    stats_interval = sim_cfg.get("stats_interval", 5)
    if sim_cfg.get("stats_interval_unit") == "minute":
        stats_interval *= 60

    ctx = init_simulation_context()
    set_adapter(ctx.adapter)
    set_scheduler(ctx.scheduler)
    set_reset_callback(reset_simulation)
    set_start_callback(start_simulation)

    start_monitor(port=8082)
    webbrowser.open('http://localhost:8082')

    print_info("[Web] 实时监测仪表盘已启动，请访问 http://localhost:8082")
    print_success("[OK] 自动化食堂仿真系统启动")
    print_info(f"[Config] 仿真时长：{sim_duration} 分钟")
    print_info(f"[Users] 用户总数：{len(ctx.user_manager.get_all_users())}")
    print_info(f"[Canteens] 食堂数量：{len(ctx.canteen_manager.canteens)}")

    try:
        while not simulation.exit_event.is_set():
            if simulation.exit_event.wait(timeout=stats_interval):
                break
            with simulation.ctx_lock:
                active_ctx = simulation.current_ctx
            sched = active_ctx.scheduler
            if sched and sched.is_running:
                if not sched.paused:
                    active_ctx.coordinator.tick_post_process(sched.current_time)
                    snapshot = active_ctx.build_snapshot(sched.current_time)
                    push_snapshot(snapshot)
                    try:
                        analyzer = StatisticsAnalyzer(active_ctx.storage)
                        stats = analyzer.compute_all()
                        print_info(f"[t={sched.current_time:.0f}min] "
                                   f"已服务 {stats['total_served']} 人，"
                                   f"平均等待 {stats['avg_wait_time']:.2f} min")
                    except Exception:
                        pass
    except KeyboardInterrupt:
        print_warning("\n[STOP] 用户中断，正在停止仿真...")
    finally:
        print_warning("正在关闭仿真...")
        with simulation.ctx_lock:
            ctx = simulation.current_ctx
        if ctx.scheduler:
            ctx.scheduler.stop()
        if simulation.sim_thread and simulation.sim_thread.is_alive():
            simulation.sim_thread.join(timeout=2)
        print_success("[OK] 仿真系统正常退出")


if __name__ == "__main__":
    main()
