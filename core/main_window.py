"""第二阶段：软件主内核 - 主窗口框架
基于PyQt5构建，预留四大功能模块挂载位
"""

import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMenuBar, QMenu, QAction,
    QStatusBar, QToolBar, QDockWidget, QTabWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QSplitter,
    QMessageBox, QFileDialog, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSettings
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor

from config.settings import (
    ROOT_DIR, DATA_DIR, LOG_DIR,
    MONGODB_CONFIG, MYSQL_CONFIG, REDIS_CONFIG
)


class MainWindow(QMainWindow):
    """软件主窗口 - 所有模块的母体容器"""

    # 信号定义
    sig_data_updated = pyqtSignal(dict)       # 数据更新信号
    sig_crawler_status = pyqtSignal(str)      # 爬虫状态信号
    sig_ai_result = pyqtSignal(dict)          # AI结果信号

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Terminal Pro - 专业全功能股票终端")
        self.resize(1600, 950)
        self.setMinimumSize(1200, 700)
        
        # 加载设置
        self.settings = QSettings("StockTerminal", "Pro")
        self._restore_window_state()
        
        # 初始化四大功能模块状态
        self._module_states = {
            "data": False,      # 数据模块
            "crawler": False,   # 舆情爬虫模块
            "chart": False,     # K线图表模块
            "ai": False,        # AI智能模块
        }
        
        # 构建UI
        self._setup_menu_bar()
        self._setup_status_bar()
        self._setup_central_area()
        self._setup_dock_widgets()
        self._setup_tool_bar()
        
        # 日志
        self._log("主窗口初始化完成")
        self._log("四大模块挂载位已就绪")
        self._log(f"数据目录: {DATA_DIR}")
        
        # 定时刷新状态
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._refresh_status)
        self._status_timer.start(3000)

    # ==================== 菜单栏 ====================
    def _setup_menu_bar(self):
        """构建完整菜单栏"""
        menubar = self.menuBar()
        menubar.setStyleSheet("QMenuBar { font-size: 13px; padding: 2px; }")
        
        # ----- 文件菜单 -----
        file_menu = menubar.addMenu("文件(&F)")
        
        act_connect_db = QAction("连接数据库...", self)
        act_connect_db.triggered.connect(self._on_connect_db)
        file_menu.addAction(act_connect_db)
        
        file_menu.addSeparator()
        
        act_export = QAction("导出数据...", self)
        act_export.triggered.connect(self._on_export_data)
        file_menu.addAction(act_export)
        
        act_import = QAction("导入数据...", self)
        act_import.triggered.connect(self._on_import_data)
        file_menu.addAction(act_import)
        
        file_menu.addSeparator()
        
        act_exit = QAction("退出(&X)", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)
        
        # ----- 数据模块菜单 (挂载位1) -----
        self.data_menu = menubar.addMenu("数据模块(&D)")
        self.data_menu.setEnabled(False)
        
        act_stock_list = QAction("股票列表", self)
        self.data_menu.addAction(act_stock_list)
        act_market_data = QAction("行情数据", self)
        self.data_menu.addAction(act_market_data)
        act_fundamental = QAction("基本面数据", self)
        self.data_menu.addAction(act_fundamental)
        act_financial = QAction("财报数据", self)
        self.data_menu.addAction(act_financial)
        
        # ----- 舆情爬虫菜单 (挂载位2) -----
        self.crawler_menu = menubar.addMenu("舆情分析(&S)")
        self.crawler_menu.setEnabled(False)
        
        act_crawl_start = QAction("启动爬虫", self)
        self.crawler_menu.addAction(act_crawl_start)
        act_crawl_stop = QAction("停止爬虫", self)
        self.crawler_menu.addAction(act_crawl_stop)
        self.crawler_menu.addSeparator()
        act_sentiment = QAction("情绪分析面板", self)
        self.crawler_menu.addAction(act_sentiment)
        act_hot_articles = QAction("热门文章TOP10", self)
        self.crawler_menu.addAction(act_hot_articles)
        act_report = QAction("最新研报", self)
        self.crawler_menu.addAction(act_report)
        
        # ----- K线图表菜单 (挂载位3) -----
        self.chart_menu = menubar.addMenu("K线图表(&C)")
        self.chart_menu.setEnabled(False)
        
        act_daily_k = QAction("日K线", self)
        self.chart_menu.addAction(act_daily_k)
        act_weekly_k = QAction("周K线", self)
        self.chart_menu.addAction(act_weekly_k)
        act_minute_k = QAction("分钟K线", self)
        self.chart_menu.addAction(act_minute_k)
        self.chart_menu.addSeparator()
        act_multi_period = QAction("多周期同列", self)
        self.chart_menu.addAction(act_multi_period)
        act_custom_indicator = QAction("自定义指标", self)
        self.chart_menu.addAction(act_custom_indicator)
        
        # ----- AI智能菜单 (挂载位4) -----
        self.ai_menu = menubar.addMenu("AI决策(&A)")
        self.ai_menu.setEnabled(False)
        
        act_ai_predict = QAction("AI预测面板", self)
        self.ai_menu.addAction(act_ai_predict)
        act_ai_stock_pick = QAction("AI选股", self)
        self.ai_menu.addAction(act_ai_stock_pick)
        act_ai_factor = QAction("因子挖掘", self)
        self.ai_menu.addAction(act_ai_factor)
        act_ai_sentiment = QAction("市场情绪评分", self)
        self.ai_menu.addAction(act_ai_sentiment)
        
        # ----- 设置菜单 -----
        settings_menu = menubar.addMenu("设置(&E)")
        act_config = QAction("系统配置...", self)
        settings_menu.addAction(act_config)
        act_skin = QAction("界面皮肤", self)
        settings_menu.addAction(act_skin)
        
        # ----- 帮助菜单 -----
        help_menu = menubar.addMenu("帮助(&H)")
        act_about = QAction("关于软件", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)
        act_log = QAction("查看日志", self)
        help_menu.addAction(act_log)

    # ==================== 中央区域 ====================
    def _setup_central_area(self):
        """中央区域 - QTabWidget 多标签页"""
        self.central_tabs = QTabWidget()
        self.central_tabs.setTabsClosable(True)
        self.central_tabs.tabCloseRequested.connect(
            lambda i: self.central_tabs.removeTab(i) if i > 0 else None
        )
        self.central_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #3a3a3a; }
            QTabBar::tab { padding: 8px 20px; font-size: 12px; }
        """)
        
        # 默认首页
        self.home_panel = self._create_home_panel()
        self.central_tabs.addTab(self.home_panel, "🏠 首页")
        
        self.setCentralWidget(self.central_tabs)

    def _create_home_panel(self):
        """创建首页面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        title = QLabel("Stock Terminal Pro")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #0095ff;")
        layout.addWidget(title)
        
        subtitle = QLabel("专业全功能股票终端 · AI驱动的智能交易系统")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 14px; color: #888; margin-bottom: 20px;")
        layout.addWidget(subtitle)
        
        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #3a3a3a;")
        layout.addWidget(line)
        
        # 模块状态区
        status_label = QLabel("""
            <h3>📊 系统模块状态</h3>
            <table style='margin: 10px;'>
                <tr><td style='padding: 8px;'>📡 金融数据层</td><td style='color: orange;'>—— 待挂载</td></tr>
                <tr><td style='padding: 8px;'>🕷️ 舆情爬虫系统</td><td style='color: orange;'>—— 待挂载</td></tr>
                <tr><td style='padding: 8px;'>📈 K线图表引擎</td><td style='color: orange;'>—— 待挂载</td></tr>
                <tr><td style='padding: 8px;'>🧠 AI决策引擎</td><td style='color: orange;'>—— 待挂载</td></tr>
            </table>
        """)
        status_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(status_label)
        
        # 日志预览区
        log_label = QLabel("📋 系统日志")
        log_label.setStyleSheet("font-size: 13px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(log_label)
        
        self.home_log = QTextEdit()
        self.home_log.setReadOnly(True)
        self.home_log.setMaximumHeight(200)
        self.home_log.setStyleSheet("background-color: #1e1e1e; color: #ccc;")
        layout.addWidget(self.home_log)
        
        layout.addStretch()
        return panel

    # ==================== 停靠窗口 ====================
    def _setup_dock_widgets(self):
        """设置四大功能模块的停靠面板"""
        
        # ---- 左侧：股票列表面板 (数据模块挂载位) ----
        self.stock_list_dock = QDockWidget("📊 股票列表", self)
        self.stock_list_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.stock_list_dock.setMinimumWidth(250)
        
        stock_list_widget = QWidget()
        sl_layout = QVBoxLayout(stock_list_widget)
        sl_layout.addWidget(QLabel("自选股列表将在此显示"))
        sl_layout.addWidget(QTextEdit())
        self.stock_list_dock.setWidget(stock_list_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.stock_list_dock)
        
        # ---- 下方：输出/日志面板 ----
        self.output_dock = QDockWidget("📋 输出日志", self)
        self.output_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("background-color: #1a1a1a; color: #aaa; font-family: Consolas;")
        self.output_dock.setWidget(self.output_text)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.output_dock)
        
        # ---- 右侧：预留舆情面板 (爬虫模块挂载位) ----
        self.sentiment_dock = QDockWidget("💬 舆情面板", self)
        self.sentiment_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.sentiment_dock.hide()  # 默认隐藏
        
        sentiment_widget = QWidget()
        sent_layout = QVBoxLayout(sentiment_widget)
        sent_layout.addWidget(QLabel("全网舆情评论聚合区"))
        self.sentiment_dock.setWidget(sentiment_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.sentiment_dock)

    # ==================== 工具栏 ====================
    def _setup_tool_bar(self):
        """设置顶部工具栏"""
        self.toolbar = QToolBar("主工具栏")
        self.toolbar.setMovable(False)
        self.toolbar.setStyleSheet("QToolBar { spacing: 5px; padding: 3px; }")
        self.addToolBar(self.toolbar)
        
        # 快捷搜索
        self.toolbar.addWidget(QLabel(" 股票代码: "))
        from PyQt5.QtWidgets import QLineEdit
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入代码快速搜索...")
        self.search_input.setMaximumWidth(200)
        self.search_input.setStyleSheet("padding: 5px;")
        self.toolbar.addWidget(self.search_input)
        
        self.toolbar.addSeparator()
        
        # 模块快捷按钮
        from PyQt5.QtWidgets import QPushButton
        for name, label in [("data", "📡数据"), ("crawler", "🕷️舆情"), 
                             ("chart", "📈K线"), ("ai", "🧠AI")]:
            btn = QPushButton(label)
            btn.setStyleSheet("QPushButton { padding: 5px 12px; border-radius: 3px; }"
                              "QPushButton:hover { background-color: #444; }")
            btn.clicked.connect(lambda checked, n=name: self._toggle_module(n))
            self.toolbar.addWidget(btn)

    def _setup_status_bar(self):
        """底部状态栏"""
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("QStatusBar { background: #2a2a2a; color: #aaa; }")
        self.setStatusBar(self.status_bar)
        
        self.db_status_label = QLabel(" DB: — ")
        self.status_bar.addPermanentWidget(self.db_status_label)
        
        self.crawler_status_label = QLabel(" 🕷️: — ")
        self.status_bar.addPermanentWidget(self.crawler_status_label)
        
        self.ai_status_label = QLabel(" 🧠: — ")
        self.status_bar.addPermanentWidget(self.ai_status_label)
        
        self.time_label = QLabel("")
        self.status_bar.addPermanentWidget(self.time_label)

    # ==================== 核心方法 ====================
    def _log(self, msg: str):
        """统一日志输出"""
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{ts}] {msg}"
        self.output_text.append(formatted)
        self.home_log.append(formatted)

    def _toggle_module(self, module_name: str):
        """切换模块状态"""
        current = self._module_states.get(module_name, False)
        self._module_states[module_name] = not current
        state = "启用" if not current else "停用"
        self._log(f"模块 [{module_name}] {state}")
        self.status_bar.showMessage(f"模块 {module_name} 已{state}", 3000)

    def _refresh_status(self):
        """定时刷新状态栏"""
        from datetime import datetime
        self.time_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def _on_connect_db(self):
        """连接数据库"""
        self._log("正在连接数据库...")
        # 后续扩展：实际的数据库连接逻辑
        QMessageBox.information(self, "数据库连接", 
            f"MongoDB: {MONGODB_CONFIG['host']}:{MONGODB_CONFIG['port']}\n"
            f"MySQL: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}\n"
            f"Redis: {REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}")

    def _on_export_data(self):
        """导出数据"""
        path, _ = QFileDialog.getSaveFileName(self, "导出数据", "", "CSV文件 (*.csv)")
        if path:
            self._log(f"数据已导出至: {path}")

    def _on_import_data(self):
        """导入数据"""
        path, _ = QFileDialog.getOpenFileName(self, "导入数据", "", "CSV文件 (*.csv)")
        if path:
            self._log(f"从 {path} 导入数据")

    def _show_about(self):
        """关于对话框"""
        QMessageBox.about(self, "关于 Stock Terminal Pro",
            "<h2>Stock Terminal Pro v1.0.0</h2>"
            "<p>专业全功能股票终端</p>"
            "<ul>"
            "<li>全市场实盘交易</li>"
            "<li>全球金融数据库</li>"
            "<li>全网舆情爬取聚合（独有）</li>"
            "<li>AI机器学习选股</li>"
            "</ul>")

    def _restore_window_state(self):
        """恢复窗口状态"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

    def closeEvent(self, event):
        """关闭事件 - 保存状态"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self._log("软件正在关闭...")
        event.accept()


def run_main_window():
    """启动主窗口"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 暗色主题
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(45, 45, 45))
    palette.setColor(QPalette.WindowText, QColor(208, 208, 208))
    palette.setColor(QPalette.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.Text, QColor(208, 208, 208))
    palette.setColor(QPalette.Button, QColor(60, 60, 60))
    palette.setColor(QPalette.ButtonText, QColor(208, 208, 208))
    palette.setColor(QPalette.Highlight, QColor(0, 149, 255))
    app.setPalette(palette)
    
    app.setStyleSheet("""
        QMainWindow { background-color: #2d2d2d; }
        QDockWidget { border: 1px solid #3a3a3a; }
        QDockWidget::title { background: #333; padding: 6px; }
        QMenu { background: #333; color: #ddd; border: 1px solid #555; }
        QMenu::item:selected { background: #0d7377; }
    """)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_main_window()