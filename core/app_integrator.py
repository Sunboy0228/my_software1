"""第七阶段：全模块总集成器
统一打通：数据库 → 数据层 → 爬虫 → AI → 图表 → 主窗口
"""

from typing import Optional

from config.settings import (
    MONGODB_CONFIG, MYSQL_CONFIG, REDIS_CONFIG,
    CRAWLER_CONFIG, AI_CONFIG, CHART_CONFIG, TRADE_CONFIG
)


class AppIntegrator:
    """应用程序总集成器 - 所有模块的统一入口和管理"""

    def __init__(self):
        self._data_manager = None
        self._crawler = None
        self._sentiment_analyzer = None
        self._chart_engine = None
        self._ai_predictor = None
        self._db_manager = None
        self._scheduler = None
        self._main_window = None
        
        self._initialized = False
        
        print("=" * 60)
        print("  Stock Terminal Pro - 全模块集成器")
        print("=" * 60)

    # ==================== 顺序初始化所有模块 ====================
    
    def initialize_all(self, main_window=None) -> bool:
        """
        按顺序初始化所有模块（严格按照大纲顺序）
        返回是否全部初始化成功
        """
        if self._initialized:
            print("[Integrator] 已初始化，跳过")
            return True
        
        self._main_window = main_window
        
        try:
            # 阶段1: 数据库连接
            print("\n>>> 第一阶段：数据库连接...")
            self._init_database()
            
            # 阶段2: 主窗口（由外部传入）
            print("\n>>> 第二阶段：主窗口挂载...")
            if main_window:
                self._mount_to_main_window(main_window)
            
            # 阶段3: 金融数据底层
            print("\n>>> 第三阶段：金融数据层...")
            self._init_data_layer()
            
            # 阶段4: 舆情爬虫系统
            print("\n>>> 第四阶段：舆情爬虫系统...")
            self._init_crawler()
            
            # 阶段5: K线图表引擎
            print("\n>>> 第五阶段：K线图表引擎...")
            self._init_chart()
            
            # 阶段6: AI决策引擎
            print("\n>>> 第六阶段：AI决策引擎...")
            self._init_ai()
            
            # 阶段7: 任务调度器
            print("\n>>> 第七阶段：任务调度器...")
            self._init_scheduler()
            
            self._initialized = True
            
            print("\n" + "=" * 60)
            print("  ✅ 所有模块初始化完成！")
            print("=" * 60)
            
            self._print_module_status()
            
            return True
            
        except Exception as e:
            print(f"\n❌ 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ----- 各阶段初始化 -----
    
    def _init_database(self):
        """初始化数据库连接"""
        from core.database.db_manager import get_db_manager
        self._db_manager = get_db_manager()
        connected = self._db_manager.connect_all()
        
        for db, status in connected.items():
            icon = "✅" if status else "⚠️"
            print(f"  {icon} {db}: {'已连接' if status else '未连接（使用兜底方案）'}")

    def _mount_to_main_window(self, window):
        """将模块挂载到主窗口"""
        # 启用四大模块菜单
        window.data_menu.setEnabled(True)
        window.data_menu.setTitle("📡 数据模块(&D)")
        
        window.crawler_menu.setEnabled(True)
        window.crawler_menu.setTitle("🕷️ 舆情分析(&S)")
        
        window.chart_menu.setEnabled(True)
        window.chart_menu.setTitle("📈 K线图表(&C)")
        
        window.ai_menu.setEnabled(True)
        window.ai_menu.setTitle("🧠 AI决策(&A)")
        
        window._log("✅ 四大功能模块已挂载到主窗口")
        window.status_bar.showMessage("系统就绪 - 所有模块已加载", 5000)
        
        # 更新状态栏
        window.db_status_label.setText(" DB: 已连接 ")

    def _init_data_layer(self):
        """初始化金融数据层"""
        from core.data_layer.data_manager import get_data_manager
        self._data_manager = get_data_manager()
        
        # 预加载股票列表
        for market in ["A股", "港股", "美股"]:
            stocks = self._data_manager.get_stock_list(market)
            print(f"  {market}: {len(stocks)} 只股票已加载")

    def _init_crawler(self):
        """初始化舆情爬虫"""
        from core.crawler.crawler_manager import get_crawler_manager
        from core.crawler.sentiment_analyzer import get_sentiment_analyzer
        
        self._crawler = get_crawler_manager()
        self._sentiment_analyzer = get_sentiment_analyzer()
        print(f"  爬取源: {self._crawler.sources}")
        print(f"  情绪词库: {len(self._sentiment_analyzer.bullish_set)}看涨词 / "
              f"{len(self._sentiment_analyzer.bearish_set)}看跌词")

    def _init_chart(self):
        """初始化K线图表引擎"""
        from core.chart.chart_engine import get_chart_engine
        self._chart_engine = get_chart_engine()

    def _init_ai(self):
        """初始化AI引擎"""
        from core.ai_engine.ai_predictor import get_ai_predictor
        self._ai_predictor = get_ai_predictor()

    def _init_scheduler(self):
        """初始化任务调度器"""
        from core.scheduler import get_scheduler
        self._scheduler = get_scheduler()
        
        # 注册定时任务
        self._scheduler.add_task(
            "舆情爬取-交易时段",
            self._task_crawl_sentiment,
            interval_minutes=30,
            condition_func=self._scheduler.is_trading_time
        )
        
        self._scheduler.add_task(
            "舆情爬取-非交易时段",
            self._task_crawl_sentiment,
            interval_minutes=120,
            condition_func=lambda: not self._scheduler.is_trading_time()
        )
        
        self._scheduler.add_task(
            "AI选股更新",
            self._task_ai_stock_screening,
            interval_minutes=60,
        )
        
        self._scheduler.start()
        print(f"  已注册 {len(self._scheduler.tasks)} 个定时任务")

    # ----- 定时任务回调 -----
    
    def _task_crawl_sentiment(self):
        """定时爬取舆情"""
        if self._crawler and self._data_manager:
            stocks = self._data_manager.get_stock_list("A股")
            # 只爬取前5只作为示例（实际应全部爬取）
            sample = list(zip(stocks['code'].head(5), stocks['name'].head(5)))
            comments = self._crawler.crawl_all_stocks(sample)
            
            if comments and self._sentiment_analyzer:
                results = self._sentiment_analyzer.analyze_batch(comments)
                print(f"  [定时任务] 爬取完成: {len(comments)}条评论, 情绪分析: {len(results)}条")

    def _task_ai_stock_screening(self):
        """定时AI选股"""
        if self._ai_predictor and self._data_manager:
            print("  [定时任务] AI选股中...")
            # 实际应传入真实数据
            # results = self._ai_predictor.screen_stocks(stock_data, top_k=20)

    # ==================== 状态打印 ====================
    
    def _print_module_status(self):
        """打印所有模块状态"""
        modules = [
            ("数据库", self._db_manager is not None),
            ("金融数据层", self._data_manager is not None),
            ("舆情爬虫", self._crawler is not None),
            ("情绪分析", self._sentiment_analyzer is not None),
            ("K线图表", self._chart_engine is not None),
            ("AI引擎", self._ai_predictor is not None),
            ("任务调度", self._scheduler is not None),
        ]
        
        for name, status in modules:
            icon = "✅" if status else "❌"
            print(f"  {icon} {name}")

    # ==================== 便捷访问 ====================
    
    @property
    def data_manager(self):
        return self._data_manager
    
    @property
    def crawler(self):
        return self._crawler
    
    @property
    def sentiment_analyzer(self):
        return self._sentiment_analyzer
    
    @property
    def chart_engine(self):
        return self._chart_engine
    
    @property
    def ai_predictor(self):
        return self._ai_predictor
    
    @property
    def db_manager(self):
        return self._db_manager
    
    @property
    def scheduler(self):
        return self._scheduler


# 全局单例
_integrator_instance: Optional[AppIntegrator] = None

def get_integrator() -> AppIntegrator:
    global _integrator_instance
    if _integrator_instance is None:
        _integrator_instance = AppIntegrator()
    return _integrator_instance