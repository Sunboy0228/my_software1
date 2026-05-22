"""第七阶段：自动化任务调度器
开盘期间30分钟爬一次，非开盘2小时增量更新，每日全量数据同步
"""

import time
import threading
from datetime import datetime, time as dt_time
from typing import Callable, Optional

from config.settings import SCHEDULE_CONFIG


class TaskScheduler:
    """自动化任务调度器"""

    # A股交易时间
    TRADING_START = dt_time(9, 30)
    TRADING_END = dt_time(15, 0)
    LUNCH_START = dt_time(11, 30)
    LUNCH_END = dt_time(13, 0)

    def __init__(self):
        self.tasks = {}
        self._running = False
        self._thread = None
        
        print("[Scheduler] 任务调度器初始化完成")

    def is_trading_time(self) -> bool:
        """判断当前是否在A股交易时段"""
        now = datetime.now()
        current_time = now.time()
        
        # 周末不交易
        if now.weekday() >= 5:
            return False
        
        # 上午时段 9:30-11:30
        if self.TRADING_START <= current_time <= self.LUNCH_START:
            return True
        
        # 下午时段 13:00-15:00
        if self.LUNCH_END <= current_time <= self.TRADING_END:
            return True
        
        return False

    def add_task(self, name: str, func: Callable, interval_minutes: int, 
                 condition_func: Optional[Callable] = None):
        """
        添加定时任务
        :param name: 任务名称
        :param func: 任务函数
        :param interval_minutes: 执行间隔（分钟）
        :param condition_func: 前置条件函数（返回True才执行）
        """
        self.tasks[name] = {
            'func': func,
            'interval': interval_minutes * 60,  # 转换为秒
            'condition': condition_func,
            'last_run': None,
            'run_count': 0,
            'error_count': 0,
        }
        print(f"[Scheduler] 已注册任务: {name} (每{interval_minutes}分钟)")

    def start(self):
        """启动调度器（后台线程）"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[Scheduler] 调度器已启动")

    def stop(self):
        """停止调度器"""
        self._running = False
        print("[Scheduler] 调度器已停止")

    def _run_loop(self):
        """调度主循环"""
        while self._running:
            now = datetime.now()
            
            for name, task in self.tasks.items():
                # 检查是否需要执行
                should_run = False
                
                if task['last_run'] is None:
                    should_run = True
                else:
                    elapsed = (now - task['last_run']).total_seconds()
                    if elapsed >= task['interval']:
                        should_run = True
                
                # 检查前置条件
                if should_run and task['condition']:
                    should_run = task['condition']()
                
                if should_run:
                    try:
                        print(f"[Scheduler] 执行任务: {name}")
                        task['func']()
                        task['last_run'] = now
                        task['run_count'] += 1
                    except Exception as e:
                        task['error_count'] += 1
                        print(f"[Scheduler] 任务 {name} 执行失败: {e}")
            
            # 每60秒检查一次
            time.sleep(60)

    def get_status(self) -> dict:
        """获取所有任务状态"""
        status = {}
        for name, task in self.tasks.items():
            last = task['last_run'].strftime('%H:%M:%S') if task['last_run'] else '从未'
            status[name] = {
                'last_run': last,
                'run_count': task['run_count'],
                'error_count': task['error_count'],
            }
        return status


# 全局单例
_scheduler_instance: Optional[TaskScheduler] = None

def get_scheduler() -> TaskScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance