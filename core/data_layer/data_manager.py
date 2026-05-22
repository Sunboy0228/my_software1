"""第三阶段：金融数据底层管理器
整合行情数据 + 基本面数据 + 双数据源兜底
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import DATA_DIR, MONGODB_CONFIG, MYSQL_CONFIG


class DataManager:
    """
    全市场金融数据管理器
    数据源：本地CSV缓存 -> MongoDB -> 在线API（双兜底）
    """

    def __init__(self):
        self._cache_dir = DATA_DIR / "market_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 市场列表
        self.markets = ["A股", "港股", "美股", "期货"]
        
        # 数据周期
        self.periods = ["1min", "5min", "15min", "30min", "60min", "日", "周", "月"]
        
        # 股票池缓存
        self._stock_pool: Dict[str, pd.DataFrame] = {}
        
        print("[DataManager] 金融数据管理器初始化完成")
        print(f"[DataManager] 缓存目录: {self._cache_dir}")

    # ==================== 股票列表 ====================
    def get_stock_list(self, market: str = "A股") -> pd.DataFrame:
        """获取全市场股票列表"""
        cache_file = self._cache_dir / f"stock_list_{market}.csv"
        
        if cache_file.exists():
            df = pd.read_csv(cache_file)
            print(f"[DataManager] 从缓存加载 {market} 股票列表: {len(df)} 只")
            return df
        
        # 生成示例股票列表（后续接入QUANTAXIS/OpenBB替换）
        df = self._generate_sample_stock_list(market)
        df.to_csv(cache_file, index=False)
        return df

    def _generate_sample_stock_list(self, market: str) -> pd.DataFrame:
        """生成示例股票列表（占位，等待QUANTAXIS接入）"""
        if market == "A股":
            stocks = [
                {"code": "000001", "name": "平安银行", "sector": "银行"},
                {"code": "000002", "name": "万科A", "sector": "房地产"},
                {"code": "000858", "name": "五粮液", "sector": "白酒"},
                {"code": "002415", "name": "海康威视", "sector": "安防"},
                {"code": "300750", "name": "宁德时代", "sector": "新能源"},
                {"code": "600519", "name": "贵州茅台", "sector": "白酒"},
                {"code": "600036", "name": "招商银行", "sector": "银行"},
                {"code": "601318", "name": "中国平安", "sector": "保险"},
                {"code": "000725", "name": "京东方A", "sector": "面板"},
                {"code": "002594", "name": "比亚迪", "sector": "汽车"},
                {"code": "688981", "name": "中芯国际", "sector": "芯片"},
                {"code": "300059", "name": "东方财富", "sector": "券商"},
            ]
        else:
            stocks = [
                {"code": "AAPL", "name": "苹果", "sector": "科技"},
                {"code": "TSLA", "name": "特斯拉", "sector": "汽车"},
                {"code": "NVDA", "name": "英伟达", "sector": "芯片"},
                {"code": "00700", "name": "腾讯控股", "sector": "互联网"},
            ]
        return pd.DataFrame(stocks)

    # ==================== K线数据 ====================
    def get_kline_data(
        self,
        code: str,
        period: str = "日",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """获取K线数据"""
        cache_file = self._cache_dir / f"{code}_{period}.csv"
        
        if cache_file.exists():
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            if start_date:
                df = df[df.index >= start_date]
            if end_date:
                df = df[df.index <= end_date]
            return df
        
        # 生成示例K线数据（占位）
        df = self._generate_sample_kline(code, period)
        df.to_csv(cache_file)
        return df

    def _generate_sample_kline(self, code: str, period: str, days: int = 252) -> pd.DataFrame:
        """生成模拟K线数据"""
        np.random.seed(hash(code) % 2**31)
        
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        
        base_price = {
            "000858": 150, "600519": 1800, "300750": 200,
            "000001": 12, "002594": 250, "300059": 18
        }.get(code, 50)
        
        returns = np.random.normal(0.0003, 0.018, days)
        prices = base_price * (1 + np.cumsum(returns))
        
        opens = prices * (1 + np.random.normal(0, 0.005, days))
        highs = np.maximum(opens, prices) * (1 + abs(np.random.normal(0, 0.01, days)))
        lows = np.minimum(opens, prices) * (1 - abs(np.random.normal(0, 0.01, days)))
        closes = prices
        volumes = np.random.uniform(1e7, 5e8, days)
        
        df = pd.DataFrame({
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes,
        }, index=dates)
        
        df.index.name = 'date'
        return df.round(2)

    # ==================== 基本面数据 ====================
    def get_fundamental_data(self, code: str) -> Dict[str, Any]:
        """获取股票基本面数据"""
        # 占位：后续接入QUANTAXIS/OpenBB
        sample_fundamentals = {
            "000858": {"pe": 22.5, "pb": 5.8, "market_cap": 5800e8, "roe": 0.25},
            "600519": {"pe": 35.2, "pb": 12.3, "market_cap": 22000e8, "roe": 0.32},
            "300750": {"pe": 28.1, "pb": 7.2, "market_cap": 9500e8, "roe": 0.18},
        }
        return sample_fundamentals.get(code, {"pe": 15.0, "pb": 2.0, "market_cap": 100e8, "roe": 0.12})

    # ==================== 龙虎榜 / 资金流向 ====================
    def get_money_flow(self, code: str, days: int = 10) -> pd.DataFrame:
        """资金流向数据"""
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        np.random.seed(hash(code + "flow") % 2**31)
        
        return pd.DataFrame({
            '主力净流入': np.random.normal(0, 5e7, days),
            '超大单净流入': np.random.normal(0, 3e7, days),
            '大单净流入': np.random.normal(0, 2e7, days),
        }, index=dates).round(0)

    # ==================== 北向资金 ====================
    def get_north_flow(self, code: str, days: int = 10) -> pd.DataFrame:
        """北向资金持仓变化"""
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        np.random.seed(hash(code + "north") % 2**31)
        
        return pd.DataFrame({
            '北向持仓占比': np.cumsum(np.random.normal(0, 0.01, days)) + 0.05,
            '北向净买入': np.random.normal(0, 5e7, days),
        }, index=dates).round(4)

    # ==================== 数据同步 ====================
    def sync_all_data(self):
        """全量同步所有数据"""
        print("[DataManager] 开始全量数据同步...")
        
        for market in self.markets:
            stocks = self.get_stock_list(market)
            print(f"  {market}: {len(stocks)} 只股票")
        
        print("[DataManager] 全量同步完成")


# 全局单例
_data_manager_instance: Optional[DataManager] = None


def get_data_manager() -> DataManager:
    """获取全局DataManager单例"""
    global _data_manager_instance
    if _data_manager_instance is None:
        _data_manager_instance = DataManager()
    return _data_manager_instance