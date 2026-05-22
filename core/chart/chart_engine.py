"""第五阶段：专业K线图表引擎
基于mplfinance + pyqtgraph 实现专业看盘功能
筹码分布、缠论画线、多周期同列、自定义指标
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Tuple

import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import mplfinance as mpf

from config.settings import CHART_CONFIG


class KLineChartEngine:
    """专业K线图表引擎"""

    def __init__(self):
        self.theme = CHART_CONFIG.get("default_theme", "dark")
        self.indicators = CHART_CONFIG.get("indicators", ["MA", "MACD", "RSI", "VOL"])
        self.periods = CHART_CONFIG.get("multi_period_layout", [])
        
        # 内置配色方案
        self.color_schemes = {
            "dark": {
                "bg": "#1a1a2e", "grid": "#2a2a4a", "text": "#cccccc",
                "up": "#ef5350", "down": "#26a69a", "ma5": "#ffeb3b",
                "ma10": "#ff9800", "ma20": "#e040fb", "volume_up": "#ef5350aa",
                "volume_down": "#26a69aaa"
            },
            "light": {
                "bg": "#ffffff", "grid": "#e0e0e0", "text": "#333333",
                "up": "#d32f2f", "down": "#2e7d32", "ma5": "#f57c00",
                "ma10": "#1976d2", "ma20": "#7b1fa2"
            }
        }
        
        print("[ChartEngine] K线图表引擎初始化完成")
        print(f"  主题: {self.theme}")
        print(f"  内置指标: {self.indicators}")

    # ==================== 主K线图 ====================

    def create_kline_figure(
        self,
        df: pd.DataFrame,
        title: str = "",
        show_volume: bool = True,
        show_indicators: bool = True
    ) -> Tuple[Figure, List[FigureCanvas]]:
        """
        创建专业K线图
        返回：(主图figure, 子图canvas列表)
        """
        colors = self.color_schemes[self.theme]
        
        # 确保数据列名正确
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"缺少必要列: {col}")
        
        # 计算技术指标
        df_with_indicators = df.copy()
        df_with_indicators = self._add_ma(df_with_indicators)
        df_with_indicators = self._add_macd(df_with_indicators)
        df_with_indicators = self._add_rsi(df_with_indicators)
        df_with_indicators = self._add_bollinger(df_with_indicators)
        
        # 构建mplfinance面板
        panels = []
        
        # 面板0: K线主图 + MA
        main_panel = []
        for ma in ['MA5', 'MA10', 'MA20']:
            if ma in df_with_indicators.columns:
                main_panel.append(mpf.make_addplot(
                    df_with_indicators[ma],
                    color=colors.get(ma.lower(), '#ff0'),
                    width=1.5, panel=0
                ))
        
        # 面板1: 成交量
        if show_volume:
            volume_colors = [colors['volume_up'] if df_with_indicators['close'].iloc[i] >= df_with_indicators['open'].iloc[i]
                            else colors['volume_down']
                            for i in range(len(df_with_indicators))]
            panels.append(mpf.make_addplot(
                df_with_indicators['volume'],
                type='bar', color=volume_colors, panel=1,
                ylabel='VOL'
            ))
        
        # 面板2: MACD
        if show_indicators and 'MACD' in df_with_indicators.columns:
            panels.extend([
                mpf.make_addplot(df_with_indicators['MACD'], panel=2, color='#2196f3', ylabel='MACD'),
                mpf.make_addplot(df_with_indicators['MACD_Signal'], panel=2, color='#ff9800'),
                mpf.make_addplot(df_with_indicators['MACD_Hist'], type='bar', panel=2, 
                                color=['#ef5350' if v >= 0 else '#26a69a' for v in df_with_indicators['MACD_Hist']]),
            ])
        
        # 面板3: RSI
        if show_indicators and 'RSI' in df_with_indicators.columns:
            panels.append(mpf.make_addplot(
                df_with_indicators['RSI'], panel=3, color='#9c27b0', ylabel='RSI',
                ylim=(0, 100)
            ))
        
        # 样式配置
        mc = mpf.make_marketcolors(
            up=colors['up'], down=colors['down'],
            edge='inherit', wick='inherit', volume='inherit'
        )
        
        style = mpf.make_mpf_style(
            base_mpf_style='charles',
            marketcolors=mc,
            facecolor=colors['bg'],
            gridcolor=colors['grid'],
            figcolor=colors['bg'],
        )
        
        panel_ratios = [4, 1.5, 1.5, 1.5] if show_indicators else [4, 1.5]
        
        fig, axes = mpf.plot(
            df_with_indicators,
            type='candle',
            style=style,
            title=title or 'K线图',
            addplot=panels if panels else None,
            volume=False,
            panel_ratios=panel_ratios,
            returnfig=True,
            figsize=(14, 9),
        )
        
        return fig

    # ==================== 技术指标计算 ====================

    def _add_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        """移动平均线"""
        for period in [5, 10, 20, 60, 120]:
            df[f'MA{period}'] = df['close'].rolling(window=period).mean()
        return df

    def _add_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """MACD指标"""
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        return df

    def _add_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """RSI指标"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-10)
        df['RSI'] = 100 - (100 / (1 + rs))
        return df

    def _add_bollinger(self, df: pd.DataFrame, period: int = 20, std: int = 2) -> pd.DataFrame:
        """布林带"""
        df['BOLL_MID'] = df['close'].rolling(window=period).mean()
        df['BOLL_STD'] = df['close'].rolling(window=period).std()
        df['BOLL_UP'] = df['BOLL_MID'] + std * df['BOLL_STD']
        df['BOLL_DN'] = df['BOLL_MID'] - std * df['BOLL_STD']
        return df

    # ==================== 筹码分布 ====================

    def calc_chip_distribution(self, df: pd.DataFrame) -> Dict:
        """
        计算筹码分布
        基于成交量和价格区间估算持仓成本分布
        """
        if df.empty:
            return {}
        
        current_price = df['close'].iloc[-1]
        
        # 价格区间划分 (100档)
        price_min = df['low'].min()
        price_max = df['high'].max()
        bins = np.linspace(price_min, price_max, 100)
        
        chip_dist = np.zeros(len(bins) - 1)
        
        for i in range(len(df)):
            idx = np.digitize(df['close'].iloc[i], bins) - 1
            if 0 <= idx < len(chip_dist):
                # 成交量加权，近期权重更高
                weight = (i + 1) / len(df)
                chip_dist[idx] += df['volume'].iloc[i] * weight
        
        # 归一化
        if chip_dist.sum() > 0:
            chip_dist = chip_dist / chip_dist.sum()
        
        # 计算筹码集中度
        peak_idx = np.argmax(chip_dist)
        peak_price = (bins[peak_idx] + bins[peak_idx + 1]) / 2
        
        # 获利比例
        profit_ratio = np.sum(chip_dist[bins[:-1] < current_price])
        
        return {
            "current_price": current_price,
            "peak_price": peak_price,
            "profit_ratio": round(profit_ratio * 100, 2),
            "chip_concentration": round(1 - np.std(chip_dist) * 10, 4),
            "bins": bins.tolist(),
            "distribution": chip_dist.tolist()
        }

    # ==================== 缠论分型识别 ====================

    def find_fractals(self, df: pd.DataFrame) -> Tuple[List[int], List[int]]:
        """
        缠论分型识别
        返回：(顶分型索引列表, 底分型索引列表)
        """
        tops = []
        bottoms = []
        
        if len(df) < 5:
            return tops, bottoms
        
        highs = df['high'].values
        lows = df['low'].values
        
        for i in range(2, len(df) - 2):
            # 顶分型：中间高点最高
            if (highs[i] >= highs[i-1] and highs[i] >= highs[i-2] and
                highs[i] >= highs[i+1] and highs[i] >= highs[i+2]):
                tops.append(i)
            
            # 底分型：中间低点最低
            if (lows[i] <= lows[i-1] and lows[i] <= lows[i-2] and
                lows[i] <= lows[i+1] and lows[i] <= lows[i+2]):
                bottoms.append(i)
        
        return tops, bottoms

    # ==================== 多周期图 ====================

    def create_multi_period_view(self, data_dict: Dict[str, pd.DataFrame]) -> Figure:
        """
        多周期同列视图
        data_dict: {"日K": df1, "周K": df2, ...}
        """
        n = len(data_dict)
        if n == 0:
            return None
        
        rows = (n + 1) // 2
        cols = 2 if n > 1 else 1
        
        fig, axes = plt.subplots(rows, cols, figsize=(14, 4*rows))
        fig.patch.set_facecolor('#1a1a2e')
        
        if n == 1:
            axes = [axes]
        else:
            axes = axes.flatten()
        
        colors = self.color_schemes[self.theme]
        
        for ax, (period_name, df_period) in zip(axes, data_dict.items()):
            if df_period.empty:
                ax.set_title(f"{period_name} - 暂无数据", color='gray')
                continue
            
            # 简化K线绘制
            for i in range(len(df_period)):
                row = df_period.iloc[i]
                color = colors['up'] if row['close'] >= row['open'] else colors['down']
                ax.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.8)
                ax.plot([i, i], [row['open'], row['close']], color=color, linewidth=3)
            
            ax.set_title(f"{period_name}", color=colors['text'], fontsize=11)
            ax.set_facecolor(colors['bg'])
            ax.tick_params(colors=colors['text'])
            ax.grid(True, alpha=0.2, color=colors['grid'])
        
        # 隐藏多余的子图
        for j in range(len(data_dict), len(axes)):
            axes[j].set_visible(False)
        
        plt.tight_layout()
        return fig

    # ==================== 指标计算工具 ====================

    def calc_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """平均真实波幅 ATR"""
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.ewm(span=period, adjust=False).mean()

    def calc_kdj(self, df: pd.DataFrame, n: int = 9) -> pd.DataFrame:
        """KDJ指标"""
        low_n = df['low'].rolling(window=n).min()
        high_n = df['high'].rolling(window=n).max()
        
        rsv = (df['close'] - low_n) / (high_n - low_n + 1e-10) * 100
        
        df['K'] = rsv.ewm(com=2, adjust=False).mean()
        df['D'] = df['K'].ewm(com=2, adjust=False).mean()
        df['J'] = 3 * df['K'] - 2 * df['D']
        
        return df


# 全局单例
_chart_engine_instance: Optional[KLineChartEngine] = None

def get_chart_engine() -> KLineChartEngine:
    global _chart_engine_instance
    if _chart_engine_instance is None:
        _chart_engine_instance = KLineChartEngine()
    return _chart_engine_instance