"""数据库连接管理器
MongoDB - 舆情评论 / MySQL - 交易记录 / Redis - 缓存任务
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from config.settings import MONGODB_CONFIG, MYSQL_CONFIG, REDIS_CONFIG


class DatabaseManager:
    """统一数据库管理"""

    def __init__(self):
        self.mongo_config = MONGODB_CONFIG
        self.mysql_config = MYSQL_CONFIG
        self.redis_config = REDIS_CONFIG
        
        self._mongo_client = None
        self._mongo_db = None
        self._mysql_conn = None
        self._redis_client = None
        
        self._connected = {
            "mongo": False,
            "mysql": False,
            "redis": False
        }
        
        print("[DBManager] 数据库管理器初始化完成")

    # ==================== MongoDB ====================
    def connect_mongo(self) -> bool:
        """连接MongoDB"""
        try:
            from pymongo import MongoClient
            
            uri = f"mongodb://{self.mongo_config['host']}:{self.mongo_config['port']}"
            self._mongo_client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self._mongo_client.server_info()  # 测试连接
            self._mongo_db = self._mongo_client[self.mongo_config['db']]
            self._connected['mongo'] = True
            print(f"[DBManager] MongoDB连接成功: {self.mongo_config['db']}")
            return True
        except Exception as e:
            print(f"[DBManager] MongoDB连接失败: {e}（将使用本地文件缓存）")
            return False

    def insert_comments(self, comments: List[Dict]) -> int:
        """批量插入评论"""
        if not self._connected['mongo'] or not comments:
            return 0
        
        try:
            collection = self._mongo_db['comments']
            # 使用content_hash去重
            for comment in comments:
                collection.update_one(
                    {'content_hash': comment.get('content_hash')},
                    {'$set': comment},
                    upsert=True
                )
            return len(comments)
        except Exception as e:
            print(f"[DBManager] 插入评论失败: {e}")
            return 0

    def query_comments(
        self,
        stock_code: str = None,
        platform: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """查询评论"""
        if not self._connected['mongo']:
            return []
        
        try:
            query = {}
            if stock_code:
                query['stock_code'] = stock_code
            if platform:
                query['platform'] = platform
            
            return list(
                self._mongo_db['comments']
                .find(query)
                .sort('publish_time', -1)
                .limit(limit)
            )
        except Exception as e:
            print(f"[DBManager] 查询评论失败: {e}")
            return []

    # ==================== MySQL ====================
    def connect_mysql(self) -> bool:
        """连接MySQL"""
        try:
            import pymysql
            
            self._mysql_conn = pymysql.connect(
                host=self.mysql_config['host'],
                port=self.mysql_config['port'],
                user=self.mysql_config['user'],
                password=self.mysql_config['password'],
                database=self.mysql_config['database'],
                charset=self.mysql_config['charset'],
                autocommit=True
            )
            self._connected['mysql'] = True
            print(f"[DBManager] MySQL连接成功: {self.mysql_config['database']}")
            self._init_mysql_tables()
            return True
        except Exception as e:
            print(f"[DBManager] MySQL连接失败: {e}（将使用SQLite兜底）")
            return False

    def _init_mysql_tables(self):
        """初始化MySQL表结构"""
        if not self._connected['mysql']:
            return
        
        cursor = self._mysql_conn.cursor()
        
        # 交易记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                trade_type VARCHAR(10) NOT NULL,
                price DECIMAL(10,3),
                volume INT,
                amount DECIMAL(16,2),
                trade_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                strategy_name VARCHAR(50),
                profit_loss DECIMAL(10,2),
                INDEX idx_code (stock_code),
                INDEX idx_time (trade_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # AI选股结果表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_picks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                stock_name VARCHAR(50),
                up_probability DECIMAL(5,2),
                confidence DECIMAL(5,2),
                signal VARCHAR(20),
                pick_date DATE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_date (pick_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # 策略日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                strategy_name VARCHAR(50),
                action VARCHAR(20),
                stock_code VARCHAR(20),
                message TEXT,
                log_time DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        print("[DBManager] MySQL表初始化完成")

    # ==================== Redis ====================
    def connect_redis(self) -> bool:
        """连接Redis"""
        try:
            import redis
            
            self._redis_client = redis.Redis(
                host=self.redis_config['host'],
                port=self.redis_config['port'],
                db=self.redis_config['db'],
                password=self.redis_config['password'] or None,
                decode_responses=True
            )
            self._redis_client.ping()
            self._connected['redis'] = True
            print(f"[DBManager] Redis连接成功")
            return True
        except Exception as e:
            print(f"[DBManager] Redis连接失败: {e}（定时任务将使用内存队列）")
            return False

    def cache_get(self, key: str) -> Optional[str]:
        """Redis缓存读取"""
        if self._connected['redis']:
            try:
                return self._redis_client.get(key)
            except:
                pass
        return None

    def cache_set(self, key: str, value: str, expire_seconds: int = 3600):
        """Redis缓存写入"""
        if self._connected['redis']:
            try:
                self._redis_client.setex(key, expire_seconds, value)
            except:
                pass

    # ==================== 统一接口 ====================
    def connect_all(self) -> Dict[str, bool]:
        """连接所有数据库"""
        self.connect_mongo()
        self.connect_mysql()
        self.connect_redis()
        return self._connected

    def is_any_connected(self) -> bool:
        """是否有至少一个数据库可用"""
        return any(self._connected.values())


# 全局单例
_db_instance: Optional[DatabaseManager] = None

def get_db_manager() -> DatabaseManager:
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance