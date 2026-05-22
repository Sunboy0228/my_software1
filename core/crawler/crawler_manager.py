"""第四阶段：全网舆情爬虫管理器
统一调度六大平台爬虫 + 去重 + 断点续爬
"""

import json
import time
import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import deque

import requests
from config.settings import (
    CRAWLER_SOURCES, CRAWLER_CONFIG, DATA_DIR,
    MONGODB_CONFIG, REDIS_CONFIG, SCHEDULE_CONFIG
)


# ==================== 数据模型 ====================

@dataclass
class CommentItem:
    """统一评论/文章数据结构"""
    stock_code: str          # 股票代码
    stock_name: str          # 股票名称
    platform: str            # 来源平台
    author: str              # 作者
    title: str               # 标题
    content: str             # 正文
    publish_time: str        # 发布时间
    url: str                 # 原文链接
    likes: int = 0           # 点赞数
    comments_count: int = 0  # 评论数
    hot_score: float = 0.0   # 热度分数
    sentiment_label: str = "neutral"  # 情绪标签: bullish/bearish/neutral
    sentiment_score: float = 0.0      # 情绪分值: -1到1
    crawl_time: str = ""     # 爬取时间
    content_hash: str = ""   # 内容哈希（去重用）

    def __post_init__(self):
        if not self.crawl_time:
            self.crawl_time = datetime.now().isoformat()
        if not self.content_hash:
            raw = f"{self.platform}{self.author}{self.title}{self.content}"
            self.content_hash = hashlib.md5(raw.encode()).hexdigest()


# ==================== 爬虫管理器 ====================

class CrawlerManager:
    """全网舆情爬虫总控制器"""

    def __init__(self):
        self.sources = CRAWLER_SOURCES
        self.config = CRAWLER_CONFIG
        self.schedule = SCHEDULE_CONFIG
        
        # 爬取队列
        self._crawl_queue: deque = deque()
        self._crawled_hashes: Set[str] = set()  # 已爬取内容哈希
        
        # 断点续爬记录
        self._checkpoint_file = DATA_DIR / "crawler_checkpoint.json"
        self._checkpoint = self._load_checkpoint()
        
        # 运行状态
        self.is_running = False
        self._stop_flag = False
        
        # 统计
        self.stats = {
            "total_crawled": 0,
            "total_errors": 0,
            "last_crawl_time": None,
            "platform_stats": {s: 0 for s in self.sources}
        }
        
        # 请求会话
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        print("[CrawlerManager] 舆情爬虫管理器初始化完成")
        print(f"[CrawlerManager] 爬取源: {self.sources}")

    # ==================== 断点续爬 ====================
    def _load_checkpoint(self) -> dict:
        """加载爬取断点"""
        if self._checkpoint_file.exists():
            with open(self._checkpoint_file, 'r', encoding='utf-8') as f:
                cp = json.load(f)
            print(f"[CrawlerManager] 加载断点: 已爬 {cp.get('total_crawled', 0)} 条")
            return cp
        return {"total_crawled": 0, "last_hash": None, "platform_positions": {}}

    def _save_checkpoint(self):
        """保存爬取断点"""
        self._checkpoint["total_crawled"] = self.stats["total_crawled"]
        self._checkpoint["last_hash"] = list(self._crawled_hashes)[-1] if self._crawled_hashes else None
        with open(self._checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(self._checkpoint, f, ensure_ascii=False, indent=2)

    # ==================== 核心爬取流程 ====================
    def crawl_stock(self, stock_code: str, stock_name: str = "") -> List[CommentItem]:
        """爬取单只股票的全网评论"""
        all_comments = []
        
        for platform in self.sources:
            if self._stop_flag:
                break
            
            try:
                comments = self._crawl_platform(platform, stock_code, stock_name)
                
                # 去重
                new_comments = []
                for c in comments:
                    if c.content_hash not in self._crawled_hashes:
                        self._crawled_hashes.add(c.content_hash)
                        new_comments.append(c)
                
                all_comments.extend(new_comments)
                self.stats["platform_stats"][platform] += len(new_comments)
                
                print(f"  [{platform}] {stock_code} -> {len(new_comments)} 条新内容")
                
                # 随机延迟防封
                delay = random.uniform(*self.config["request_delay"])
                time.sleep(delay)
                
            except Exception as e:
                self.stats["total_errors"] += 1
                print(f"  [{platform}] {stock_code} 爬取失败: {e}")
        
        self.stats["total_crawled"] += len(all_comments)
        self.stats["last_crawl_time"] = datetime.now().isoformat()
        
        return all_comments

    def _crawl_platform(self, platform: str, stock_code: str, stock_name: str) -> List[CommentItem]:
        """分平台爬取（各平台独立实现）"""
        # 根据平台类型调用对应的爬取逻辑
        if platform == "eastmoney":
            return self._crawl_eastmoney(stock_code, stock_name)
        elif platform == "xueqiu":
            return self._crawl_xueqiu(stock_code, stock_name)
        elif platform == "tonghuashun":
            return self._crawl_tonghuashun(stock_code, stock_name)
        elif platform == "sina":
            return self._crawl_sina(stock_code, stock_name)
        elif platform == "stcn":
            return self._crawl_stcn(stock_code, stock_name)
        elif platform == "yicai":
            return self._crawl_yicai(stock_code, stock_name)
        else:
            return []

    # ==================== 六大平台爬取实现 ====================

    def _crawl_eastmoney(self, code: str, name: str) -> List[CommentItem]:
        """东方财富（股吧+研报）"""
        comments = []
        try:
            # 模拟东方财富股吧数据（实际需接入API）
            mock_titles = [
                f"{name}最近走势分析，后市如何？",
                f"{name}业绩超预期，看好长期发展",
                f"{name}主力资金大幅流入，值得关注",
                f"{name}短期回调是买入机会吗？",
            ]
            for i, title in enumerate(mock_titles[:random.randint(1,3)]):
                comments.append(CommentItem(
                    stock_code=code, stock_name=name,
                    platform="eastmoney",
                    author=f"股友{random.randint(10000,99999)}",
                    title=title,
                    content=title + "\n从技术面来看，短期均线多头排列，MACD金叉向上。",
                    publish_time=(datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat(),
                    url=f"https://guba.eastmoney.com/list,{code}.html",
                    likes=random.randint(0, 200),
                    comments_count=random.randint(0, 50),
                ))
        except Exception as e:
            print(f"    [eastmoney] 爬取异常: {e}")
        return comments

    def _crawl_xueqiu(self, code: str, name: str) -> List[CommentItem]:
        """雪球（大V深度分析）"""
        comments = []
        try:
            mock_authors = ["价值投资者", "技术派老张", "基本面分析", "量化小散"]
            mock_titles = [
                f"深度分析{name}的投资价值",
                f"{name}估值处于历史低位",
                f"从财务数据看{name}的成长性",
            ]
            for i, title in enumerate(mock_titles[:random.randint(1,2)]):
                comments.append(CommentItem(
                    stock_code=code, stock_name=name,
                    platform="xueqiu",
                    author=random.choice(mock_authors),
                    title=title,
                    content=f"经过深入研究{name}的基本面，我认为当前估值合理，长期持有价值凸显。",
                    publish_time=(datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat(),
                    url=f"https://xueqiu.com/S/{code}",
                    likes=random.randint(10, 500),
                    comments_count=random.randint(5, 100),
                ))
        except Exception as e:
            print(f"    [xueqiu] 爬取异常: {e}")
        return comments

    def _crawl_tonghuashun(self, code: str, name: str) -> List[CommentItem]:
        """同花顺（问答+快讯）"""
        return []  # 占位

    def _crawl_sina(self, code: str, name: str) -> List[CommentItem]:
        """新浪财经"""
        return []  # 占位

    def _crawl_stcn(self, code: str, name: str) -> List[CommentItem]:
        """证券之星"""
        return []  # 占位

    def _crawl_yicai(self, code: str, name: str) -> List[CommentItem]:
        """第一财经"""
        return []  # 占位

    # ==================== 批量爬取 ====================
    def crawl_all_stocks(self, stock_list: List[tuple]) -> List[CommentItem]:
        """遍历全市场股票爬取"""
        all_comments = []
        total = len(stock_list)
        
        print(f"[CrawlerManager] 开始批量爬取 {total} 只股票...")
        
        for i, (code, name) in enumerate(stock_list):
            if self._stop_flag:
                break
            
            print(f"[{i+1}/{total}] 爬取 {code} {name}...")
            comments = self.crawl_stock(code, name)
            all_comments.extend(comments)
            
            # 每50只保存一次断点
            if (i + 1) % 50 == 0:
                self._save_checkpoint()
        
        self._save_checkpoint()
        print(f"[CrawlerManager] 批量爬取完成，共获取 {len(all_comments)} 条评论")
        
        return all_comments

    # ==================== 控制方法 ====================
    def start(self):
        """启动爬虫"""
        self.is_running = True
        self._stop_flag = False
        print("[CrawlerManager] 爬虫已启动")

    def stop(self):
        """停止爬虫"""
        self._stop_flag = True
        self.is_running = False
        self._save_checkpoint()
        print("[CrawlerManager] 爬虫已停止")

    def get_stats(self) -> dict:
        """获取爬取统计"""
        return self.stats


# 全局单例
_crawler_instance: Optional[CrawlerManager] = None

def get_crawler_manager() -> CrawlerManager:
    global _crawler_instance
    if _crawler_instance is None:
        _crawler_instance = CrawlerManager()
    return _crawler_instance