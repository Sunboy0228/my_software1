"""第四阶段模块5：AI情绪分析系统
对每一条评论自动打分：看涨/看跌/中性 + 量化情绪分值
生成个股7日舆情情绪趋势
"""

import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from core.crawler.crawler_manager import CommentItem


# ==================== 情绪词库 ====================

BULLISH_WORDS = [
    "涨停", "大涨", "暴涨", "利好", "突破", "买入", "增持", "看涨", "看好",
    "业绩超预期", "低估", "底部", "反弹", "主升浪", "强势", "牛市", "起飞",
    "翻倍", "龙头", "白马", "成长", "价值洼地", "金叉", "放量", "主力流入",
    "加仓", "满仓", "抄底", "追涨", "连板", "利润大增", "分红", "回购"
]

BEARISH_WORDS = [
    "跌停", "大跌", "暴跌", "利空", "破位", "卖出", "减持", "看跌", "看空",
    "亏损", "泡沫", "顶部", "崩盘", "退市", "腰斩", "暴雷", "踩踏",
    "清仓", "减仓", "割肉", "套牢", "死叉", "缩量", "主力流出",
    "业绩下滑", "债务危机", "ST", "退市风险", "股东减持", "解禁"
]

NEUTRAL_WORDS = [
    "震荡", "盘整", "横盘", "观望", "持有", "等待", "不确定性",
    "波动", "整理", "筑底", "磨底", "方向不明", "风险收益比"
]

# 程度副词权重
INTENSIFIERS = {
    "非常": 1.5, "极其": 2.0, "超级": 1.8, "极度": 2.0,
    "大幅": 1.4, "显著": 1.3, "略微": 0.5, "稍微": 0.4,
    "可能": 0.7, "或许": 0.6, "大概率": 1.2, "确定性": 1.5,
}


@dataclass
class SentimentResult:
    """单条评论情绪分析结果"""
    original: CommentItem
    sentiment_label: str        # bullish / bearish / neutral
    sentiment_score: float      # -1.0 ~ 1.0
    confidence: float           # 置信度 0~1
    keywords_found: List[str]   # 匹配到的关键词
    
@dataclass 
class StockSentimentReport:
    """个股舆情情绪报告"""
    stock_code: str
    stock_name: str
    total_comments: int
    bullish_ratio: float        # 看涨比例
    bearish_ratio: float        # 看跌比例
    neutral_ratio: float        # 中性比例
    avg_sentiment_score: float  # 平均情绪分
    hot_score: float            # 热度分数
    top_keywords: List[str]     # 热门关键词
    trend_7d: List[Dict]        # 7日情绪趋势
    generated_time: str


class SentimentAnalyzer:
    """AI情绪分析引擎"""
    
    def __init__(self):
        # 加载词库
        self.bullish_set = set(BULLISH_WORDS)
        self.bearish_set = set(BEARISH_WORDS)
        self.neutral_set = set(NEUTRAL_WORDS)
        
        # 关键词统计（用于热度分析）
        self._keyword_counter: Dict[str, int] = defaultdict(int)
        
        # 情绪趋势缓存
        self._trend_cache: Dict[str, List[Dict]] = {}
        
        print("[SentimentAnalyzer] AI情绪分析引擎初始化完成")
        print(f"  看涨词: {len(self.bullish_set)} 个")
        print(f"  看跌词: {len(self.bearish_set)} 个")
        print(f"  中性词: {len(self.neutral_set)} 个")

    # ==================== 单条评论分析 ====================
    
    def analyze_comment(self, comment: CommentItem) -> SentimentResult:
        """分析单条评论的情绪"""
        text = f"{comment.title} {comment.content}"
        
        # 统计各方向关键词命中
        bullish_hits = []
        bearish_hits = []
        neutral_hits = []
        
        for word in self.bullish_set:
            if word in text:
                bullish_hits.append(word)
        for word in self.bearish_set:
            if word in text:
                bearish_hits.append(word)
        for word in self.neutral_set:
            if word in text:
                neutral_hits.append(word)
        
        # 计算情绪分数
        bullish_score = len(bullish_hits) * 1.0
        bearish_score = len(bearish_hits) * 1.0
        neutral_score = len(neutral_hits) * 0.3
        
        # 程度副词加权
        for intensifier, weight in INTENSIFIERS.items():
            if intensifier in text:
                bullish_score *= weight
                bearish_score *= weight
        
        # 综合得分
        total = bullish_score + bearish_score + neutral_score + 0.001
        raw_score = (bullish_score - bearish_score) / total
        
        # 映射到 [-1, 1]
        sentiment_score = max(-1.0, min(1.0, raw_score))
        
        # 确定标签
        if sentiment_score > 0.15:
            label = "bullish"
        elif sentiment_score < -0.15:
            label = "bearish"
        else:
            label = "neutral"
        
        # 置信度 = 匹配到的关键词总占比
        all_hits = bullish_hits + bearish_hits + neutral_hits
        confidence = min(1.0, len(all_hits) / 5.0) if all_hits else 0.3
        
        # 更新关键词统计
        for w in all_hits:
            self._keyword_counter[w] += 1
        
        return SentimentResult(
            original=comment,
            sentiment_label=label,
            sentiment_score=round(sentiment_score, 4),
            confidence=round(confidence, 4),
            keywords_found=list(set(all_hits))
        )

    # ==================== 批量分析 ====================
    
    def analyze_batch(self, comments: List[CommentItem]) -> List[SentimentResult]:
        """批量情绪分析"""
        results = []
        for comment in comments:
            try:
                result = self.analyze_comment(comment)
                results.append(result)
            except Exception as e:
                print(f"  [SentimentAnalyzer] 分析失败: {e}")
        
        print(f"[SentimentAnalyzer] 批量分析完成: {len(results)}/{len(comments)} 条")
        return results

    # ==================== 个股情绪报告 ====================
    
    def generate_stock_report(
        self, 
        stock_code: str, 
        stock_name: str,
        results: List[SentimentResult]
    ) -> StockSentimentReport:
        """生成个股情绪报告"""
        if not results:
            return StockSentimentReport(
                stock_code=stock_code,
                stock_name=stock_name,
                total_comments=0,
                bullish_ratio=0, bearish_ratio=0, neutral_ratio=0,
                avg_sentiment_score=0, hot_score=0,
                top_keywords=[],
                trend_7d=[],
                generated_time=datetime.now().isoformat()
            )
        
        total = len(results)
        bullish_count = sum(1 for r in results if r.sentiment_label == "bullish")
        bearish_count = sum(1 for r in results if r.sentiment_label == "bearish")
        neutral_count = sum(1 for r in results if r.sentiment_label == "neutral")
        
        scores = [r.sentiment_score for r in results]
        avg_score = np.mean(scores) if scores else 0.0
        
        # 热度 = 评论数 + 点赞加权 + 关键词多样性
        total_likes = sum(r.original.likes for r in results)
        hot_score = total * 0.5 + total_likes * 0.01
        
        # 热门关键词 Top10
        top_keywords = sorted(
            self._keyword_counter.items(),
            key=lambda x: x[1], reverse=True
        )[:10]
        top_kw = [kw for kw, _ in top_keywords]
        
        # 7日趋势（按时间聚合）
        trend_7d = self._calc_7d_trend(results)
        
        return StockSentimentReport(
            stock_code=stock_code,
            stock_name=stock_name,
            total_comments=total,
            bullish_ratio=round(bullish_count / total, 4),
            bearish_ratio=round(bearish_count / total, 4),
            neutral_ratio=round(neutral_count / total, 4),
            avg_sentiment_score=round(avg_score, 4),
            hot_score=round(hot_score, 2),
            top_keywords=top_kw,
            trend_7d=trend_7d,
            generated_time=datetime.now().isoformat()
        )

    def _calc_7d_trend(self, results: List[SentimentResult]) -> List[Dict]:
        """计算7日情绪趋势"""
        daily_scores = defaultdict(list)
        
        for r in results:
            try:
                date = r.original.publish_time[:10]
                daily_scores[date].append(r.sentiment_score)
            except:
                continue
        
        trend = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d")
            scores = daily_scores.get(date, [])
            trend.append({
                "date": date,
                "avg_score": round(np.mean(scores), 4) if scores else 0,
                "comment_count": len(scores)
            })
        
        return trend

    # ==================== 市场整体情绪 ====================
    
    def get_market_sentiment(self, stock_reports: List[StockSentimentReport]) -> Dict:
        """计算市场整体情绪"""
        if not stock_reports:
            return {"overall_score": 0, "label": "neutral", "hot_sectors": []}
        
        scores = [r.avg_sentiment_score for r in stock_reports]
        overall = np.mean(scores)
        
        if overall > 0.1:
            label = "看涨"
        elif overall < -0.1:
            label = "看跌"
        else:
            label = "震荡"
        
        return {
            "overall_score": round(overall, 4),
            "label": label,
            "analyzed_stocks": len(stock_reports),
            "total_comments": sum(r.total_comments for r in stock_reports),
        }


# 全局单例
_sentiment_instance: Optional[SentimentAnalyzer] = None

def get_sentiment_analyzer() -> SentimentAnalyzer:
    global _sentiment_instance
    if _sentiment_instance is None:
        _sentiment_instance = SentimentAnalyzer()
    return _sentiment_instance