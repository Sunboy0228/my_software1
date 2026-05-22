"""Stock Terminal Pro - 专业全功能股票终端
启动入口文件

启动前请确保已安装依赖：
    pip install -r requirements.txt

数据库准备（可选，软件有兜底方案）：
    - MongoDB (存储舆情数据)
    - MySQL (存储交易记录)
    - Redis (缓存与定时任务)
"""

import sys
import os

# 将项目根目录加入Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    print("=" * 60)
    print("  Stock Terminal Pro - 加载中...")
    print("=" * 60)
    
    # 先初始化集成器（在UI线程之前）
    from core.app_integrator import AppIntegrator
    integrator = AppIntegrator()
    
    # 启动主窗口（集成器作为参数传入）
    from core.main_window import run_main_window
    run_main_window()