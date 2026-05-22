"""第六阶段：AI智能决策引擎
基于机器学习的选股预测、因子挖掘、涨跌概率预测
"""

import json
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import AI_CONFIG, DATA_DIR


class AIPredictor:
    """AI量化预测引擎"""

    def __init__(self):
        self.model_dir = AI_CONFIG["model_dir"]
        self.feature_window = AI_CONFIG["feature_window"]
        self.prediction_horizon = AI_CONFIG["prediction_horizon"]
        self.train_interval = AI_CONFIG["train_interval_days"]
        
        # 模型存储
        self._models: Dict[str, any] = {}  # 股票代码 -> 模型
        self._feature_importance: Dict[str, float] = {}
        
        # 预测结果缓存
        self._prediction_cache: Dict[str, dict] = {}
        
        # 因子库
        self._factor_library = self._init_factor_library()
        
        self._load_models()
        
        print("[AIPredictor] AI决策引擎初始化完成")
        print(f"  因子数量: {len(self._factor_library)}")
        print(f"  特征窗口: {self.feature_window}天")
        print(f"  预测周期: {self.prediction_horizon}天")

    # ==================== 因子库 ====================
    def _init_factor_library(self) -> Dict[str, callable]:
        """初始化技术因子库"""
        return {
            "momentum_5d": self._factor_momentum_5d,
            "momentum_20d": self._factor_momentum_20d,
            "volatility_10d": self._factor_volatility_10d,
            "volume_ratio_5d": self._factor_volume_ratio,
            "rsi_14": self._factor_rsi,
            "ma_divergence": self._factor_ma_divergence,
            "price_position": self._factor_price_position,
            "turnover_rate": self._factor_turnover,
            "max_drawdown_20d": self._factor_max_drawdown,
            "sharpe_20d": self._factor_sharpe,
        }

    # ----- 因子计算函数 -----
    def _factor_momentum_5d(self, df: pd.DataFrame) -> float:
        if len(df) < 5: return 0
        return (df['close'].iloc[-1] / df['close'].iloc[-5] - 1)

    def _factor_momentum_20d(self, df: pd.DataFrame) -> float:
        if len(df) < 20: return 0
        return (df['close'].iloc[-1] / df['close'].iloc[-20] - 1)

    def _factor_volatility_10d(self, df: pd.DataFrame) -> float:
        if len(df) < 10: return 0
        returns = df['close'].pct_change().dropna()
        return returns.iloc[-10:].std()

    def _factor_volume_ratio(self, df: pd.DataFrame) -> float:
        if len(df) < 5: return 0
        vol_5d_avg = df['volume'].iloc[-5:].mean()
        vol_20d_avg = df['volume'].iloc[-20:].mean()
        return vol_5d_avg / (vol_20d_avg + 1)

    def _factor_rsi(self, df: pd.DataFrame) -> float:
        if len(df) < 14: return 50
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean().iloc[-1]
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
        rs = gain / (loss + 1e-10)
        return 100 - (100 / (1 + rs))

    def _factor_ma_divergence(self, df: pd.DataFrame) -> float:
        if len(df) < 20: return 0
        ma5 = df['close'].rolling(5).mean().iloc[-1]
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        return (ma5 - ma20) / (ma20 + 1e-10)

    def _factor_price_position(self, df: pd.DataFrame) -> float:
        if len(df) < 60: return 0.5
        high_60 = df['high'].rolling(60).max().iloc[-1]
        low_60 = df['low'].rolling(60).min().iloc[-1]
        current = df['close'].iloc[-1]
        if high_60 == low_60: return 0.5
        return (current - low_60) / (high_60 - low_60)

    def _factor_turnover(self, df: pd.DataFrame) -> float:
        return df['volume'].iloc[-5:].mean() if len(df) >= 5 else 0

    def _factor_max_drawdown(self, df: pd.DataFrame) -> float:
        if len(df) < 20: return 0
        rolling_max = df['close'].rolling(20, min_periods=1).max()
        drawdown = (df['close'] - rolling_max) / rolling_max
        return abs(drawdown.min())

    def _factor_sharpe(self, df: pd.DataFrame) -> float:
        if len(df) < 20: return 0
        returns = df['close'].pct_change().dropna().iloc[-20:]
        if returns.std() == 0: return 0
        return (returns.mean() / returns.std()) * np.sqrt(252)

    # ==================== 特征提取 ====================
    def extract_features(self, df: pd.DataFrame) -> np.ndarray:
        """从K线数据提取机器学习特征"""
        features = []
        
        for factor_name, factor_func in self._factor_library.items():
            try:
                value = factor_func(df)
                features.append(float(value))
            except Exception as e:
                features.append(0.0)
                print(f"  [AIPredictor] 因子 {factor_name} 计算失败: {e}")
        
        return np.array(features)

    # ==================== 涨跌预测 ====================
    def predict(self, df: pd.DataFrame, stock_code: str = "") -> Dict:
        """
        AI涨跌预测
        返回：预测涨跌概率、置信度、关键因子
        """
        features = self.extract_features(df)
        
        # 基于因子打分（简化版，实际应接入LightGBM/XGBoost模型）
        scores = self._rule_based_score(features)
        
        # 尝试加载已训练的ML模型
        if stock_code in self._models:
            try:
                model = self._models[stock_code]
                ml_pred = model.predict_proba(features.reshape(1, -1))[0]
                scores['ml_up_prob'] = float(ml_pred[1]) if len(ml_pred) > 1 else 0.5
            except Exception:
                scores['ml_up_prob'] = scores['up_probability']
        else:
            scores['ml_up_prob'] = scores['up_probability']
        
        # 缓存结果
        result = {
            "stock_code": stock_code,
            "prediction_time": datetime.now().isoformat(),
            "up_probability": round(scores['ml_up_prob'] * 100, 2),
            "down_probability": round((1 - scores['ml_up_prob']) * 100, 2),
            "confidence": round(scores.get('confidence', 0.6) * 100, 2),
            "top_factors": scores.get('top_factors', []),
            "overall_signal": "看涨" if scores['ml_up_prob'] > 0.55 
                              else ("看跌" if scores['ml_up_prob'] < 0.45 else "震荡"),
            "recommended_position": max(0, min(100, int((scores['ml_up_prob'] - 0.4) * 200))),
        }
        
        self._prediction_cache[stock_code] = result
        return result

    def _rule_based_score(self, features: np.ndarray) -> dict:
        """基于规则的打分（ML模型未训练时的fallback）"""
        factor_names = list(self._factor_library.keys())
        
        # 因子权重（可被ML学习替换）
        weights = {
            "momentum_5d": 0.06, "momentum_20d": 0.04,
            "volatility_10d": 0.03, "volume_ratio_5d": 0.05,
            "rsi_14": 0.04, "ma_divergence": 0.05,
            "price_position": 0.03, "turnover_rate": 0.03,
            "max_drawdown_20d": -0.04, "sharpe_20d": 0.03,
        }
        
        total_score = 0.5  # 基准0.5
        factor_scores = {}
        
        for i, name in enumerate(factor_names):
            if i < len(features):
                w = weights.get(name, 0.02)
                # 标准化因子值到 [-1, 1] 范围
                normalized = np.tanh(features[i] * 2)
                factor_scores[name] = normalized * w
                total_score += normalized * w
        
        # 限制概率范围
        total_score = max(0.1, min(0.9, total_score))
        
        # 找出贡献最大的因子 Top3
        top_factors = sorted(factor_scores.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
        
        return {
            "up_probability": total_score,
            "confidence": 0.6 + abs(total_score - 0.5) * 0.4,
            "top_factors": [(name, round(score, 4)) for name, score in top_factors],
            "factor_scores": factor_scores,
        }

    # ==================== AI选股 ====================
    def screen_stocks(
        self,
        stock_data: Dict[str, pd.DataFrame],
        top_k: int = 20,
        min_up_prob: float = 0.55
    ) -> List[Dict]:
        """
        AI智能选股
        从全市场筛选出最具上涨潜力的股票
        """
        results = []
        
        for code, df in stock_data.items():
            if len(df) < self.feature_window:
                continue
            
            prediction = self.predict(df, code)
            
            if prediction['up_probability'] >= min_up_prob * 100:
                results.append(prediction)
        
        # 按上涨概率排序
        results.sort(key=lambda x: x['up_probability'], reverse=True)
        
        # 返回Top K
        top_results = results[:top_k]
        
        print(f"[AIPredictor] AI选股完成: 从{len(stock_data)}只筛选出{len(top_results)}只")
        
        return top_results

    # ==================== 市场情绪评分 ====================
    def market_sentiment_score(self, predictions: List[Dict]) -> Dict:
        """综合市场情绪评分"""
        if not predictions:
            return {"score": 50, "label": "中性", "bias": 0}
        
        up_probs = [p['up_probability'] for p in predictions]
        avg_up = np.mean(up_probs) if up_probs else 50
        
        # 打分映射到0-100
        score = avg_up
        
        if score >= 60:
            label = "乐观"
        elif score >= 50:
            label = "偏乐观"
        elif score >= 40:
            label = "偏谨慎"
        else:
            label = "谨慎"
        
        return {
            "score": round(score, 2),
            "label": label,
            "bias": round(score - 50, 2),
            "total_stocks_analyzed": len(predictions),
            "bullish_count": sum(1 for p in predictions if p['up_probability'] > 55),
            "bearish_count": sum(1 for p in predictions if p['up_probability'] < 45),
        }

    # ==================== 模型管理 ====================
    def _load_models(self):
        """加载已训练的模型"""
        model_files = list(self.model_dir.glob("*.pkl"))
        for model_file in model_files:
            try:
                with open(model_file, 'rb') as f:
                    self._models[model_file.stem] = pickle.load(f)
            except Exception as e:
                print(f"  [AIPredictor] 加载模型失败 {model_file}: {e}")
        
        if self._models:
            print(f"[AIPredictor] 已加载 {len(self._models)} 个模型")

    def save_model(self, stock_code: str, model):
        """保存训练好的模型"""
        model_path = self.model_dir / f"{stock_code}.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        self._models[stock_code] = model

    def train_model(self, stock_code: str, X: np.ndarray, y: np.ndarray):
        """训练单只股票的模型（使用LightGBM）"""
        try:
            import lightgbm as lgb
            
            model = lgb.LGBMClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
            )
            model.fit(X, y)
            
            self.save_model(stock_code, model)
            print(f"[AIPredictor] {stock_code} 模型训练完成")
            
        except ImportError:
            print("[AIPredictor] LightGBM未安装，使用规则打分")
        except Exception as e:
            print(f"[AIPredictor] 训练失败: {e}")


# 全局单例
_ai_instance: Optional[AIPredictor] = None

def get_ai_predictor() -> AIPredictor:
    global _ai_instance
    if _ai_instance is None:
        _ai_instance = AIPredictor()
    return _ai_instance