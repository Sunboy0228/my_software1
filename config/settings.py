"""全局配置文件 - 统一管理所有模块配置"""

import os
from pathlib import Path

# ==================== 项目根目录 ====================
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
LOG_DIR = ROOT_DIR / "logs"

# 自动创建必要目录
for d in [DATA_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ==================== 数据库配置 ====================
# MongoDB - 存储舆情、评论、海量数据
MONGODB_CONFIG = {
    "host": os.getenv("MONGODB_HOST", "127.0.0.1"),
    "port": int(os.getenv("MONGODB_PORT", 27017)),
    "db": "stock_terminal",
    "username": os.getenv("MONGODB_USER", ""),
    "password": os.getenv("MONGODB_PASS", ""),
}

# MySQL - 存储交易记录、选股结果、策略日志
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASS", ""),
    "database": "stock_terminal",
    "charset": "utf8mb4",
}

# Redis - 定时任务、缓存、防重复爬取
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "127.0.0.1"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "db": 0,
    "password": os.getenv("REDIS_PASS", ""),
}

# ==================== 爬虫配置 ====================
CRAWLER_SOURCES = [
    "eastmoney",      # 东方财富（股吧 + 研报）
    "xueqiu",         # 雪球（大V观点）
    "tonghuashun",    # 同花顺（问答 + 快讯）
    "sina",           # 新浪财经
    "stcn",           # 证券之星
    "yicai",          # 第一财经
]

CRAWLER_CONFIG = {
    "request_delay": (2, 5),        # 随机延迟范围(秒)
    "max_retries": 3,               # 最大重试次数
    "timeout": 30,                  # 请求超时
    "batch_size": 50,               # 每批爬取股票数
    "enable_proxy": False,          # 是否启用代理
    "proxy_pool": [],               # 代理IP池（后续扩展）
}

# ==================== 定时任务配置 ====================
SCHEDULE_CONFIG = {
    "trading_crawl_interval": 30,       # 开盘期间爬取间隔(分钟)
    "off_trading_crawl_interval": 120,  # 非开盘爬取间隔(分钟)
    "daily_data_update": "02:00",        # 每日全量数据更新时间
}

# ==================== AI配置 ====================
AI_CONFIG = {
    "model_dir": DATA_DIR / "models",
    "feature_window": 60,            # 特征窗口(天)
    "prediction_horizon": 5,         # 预测天数
    "train_interval_days": 7,        # 重训练间隔
}
AI_CONFIG["model_dir"].mkdir(parents=True, exist_ok=True)

# ==================== K线图表配置 ====================
CHART_CONFIG = {
    "default_theme": "dark",
    "indicators": ["MA", "MACD", "RSI", "BOLL", "VOL"],
    "multi_period_layout": ["日K", "周K", "月K", "60分", "30分", "15分"],
}

# ==================== 交易配置 ====================
TRADE_CONFIG = {
    "market": ["A股", "港股", "美股", "期货"],
    "default_capital": 1000000,      # 默认资金
    "slippage": 0.001,               # 滑点
    "commission_rate": 0.0003,       # 佣金率
}
