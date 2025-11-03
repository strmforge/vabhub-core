"""
Database module for VabHub Core
"""

import sqlite3
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

class DatabaseManager:
    """Database manager for VabHub"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Subscriptions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    query TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    priority INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Rules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    conditions TEXT NOT NULL,
                    actions TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    priority INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    progress INTEGER DEFAULT 0,
                    result TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            
            # Media servers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS media_servers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    api_key TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Downloaders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS downloaders (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    username TEXT,
                    password TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Plugins table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS plugins (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Charts data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS charts_data (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    region TEXT NOT NULL,
                    time_range TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    chart_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            
            # Chart items table for detailed storage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chart_items (
                    id TEXT PRIMARY KEY,
                    chart_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    type TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    score REAL,
                    popularity INTEGER,
                    release_date TEXT,
                    poster_url TEXT,
                    provider TEXT NOT NULL,
                    FOREIGN KEY (chart_id) REFERENCES charts_data(id)
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.database_url)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute update query and return affected rows"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        result = self.execute_query("SELECT * FROM users WHERE id = ?", (user_id,))
        return result[0] if result else None
    
    def get_enabled_plugins(self) -> List[Dict[str, Any]]:
        """Get all enabled plugins"""
        return self.execute_query("SELECT * FROM plugins WHERE enabled = 1")
    
    # Subscription methods
    def get_subscriptions(self) -> List[Dict[str, Any]]:
        """Get all subscriptions"""
        return self.execute_query("SELECT * FROM subscriptions ORDER BY priority DESC, created_at DESC")
    
    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription by ID"""
        result = self.execute_query("SELECT * FROM subscriptions WHERE id = ?", (subscription_id,))
        return result[0] if result else None
    
    def create_subscription(self, subscription_data: Dict[str, Any]) -> str:
        """Create new subscription"""
        subscription_id = f"sub_{len(self.get_subscriptions()) + 1}"
        query = """
            INSERT INTO subscriptions (id, name, query, enabled, priority)
            VALUES (?, ?, ?, ?, ?)
        """
        self.execute_update(query, (
            subscription_id,
            subscription_data['name'],
            subscription_data['query'],
            subscription_data.get('enabled', True),
            subscription_data.get('priority', 0)
        ))
        return subscription_id
    
    def update_subscription(self, subscription_id: str, subscription_data: Dict[str, Any]) -> bool:
        """Update subscription"""
        query = """
            UPDATE subscriptions 
            SET name = ?, query = ?, enabled = ?, priority = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        affected = self.execute_update(query, (
            subscription_data['name'],
            subscription_data['query'],
            subscription_data.get('enabled', True),
            subscription_data.get('priority', 0),
            subscription_id
        ))
        return affected > 0
    
    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete subscription"""
        affected = self.execute_update("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))
        return affected > 0
    
    # Task methods
    def get_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tasks with optional status filter"""
        if status:
            return self.execute_query("SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC", (status,))
        return self.execute_query("SELECT * FROM tasks ORDER BY created_at DESC")
    
    def create_task(self, task_data: Dict[str, Any]) -> str:
        """Create new task"""
        task_id = f"task_{len(self.get_tasks()) + 1}"
        query = """
            INSERT INTO tasks (id, name, type, status, progress)
            VALUES (?, ?, ?, ?, ?)
        """
        self.execute_update(query, (
            task_id,
            task_data['name'],
            task_data['type'],
            task_data.get('status', 'pending'),
            task_data.get('progress', 0)
        ))
        return task_id
    
    def update_task_status(self, task_id: str, status: str, progress: int = 0, result: Optional[str] = None) -> bool:
        """Update task status and progress"""
        query = """
            UPDATE tasks 
            SET status = ?, progress = ?, result = ?, 
                started_at = CASE WHEN ? = 'running' AND started_at IS NULL THEN CURRENT_TIMESTAMP ELSE started_at END,
                completed_at = CASE WHEN ? IN ('completed', 'failed') AND completed_at IS NULL THEN CURRENT_TIMESTAMP ELSE completed_at END
            WHERE id = ?
        """
        affected = self.execute_update(query, (status, progress, result, status, status, task_id))
        return affected > 0
    
    # Media server methods
    def get_media_servers(self) -> List[Dict[str, Any]]:
        """Get all media servers"""
        return self.execute_query("SELECT * FROM media_servers WHERE enabled = 1")
    
    # Downloader methods
    def get_downloaders(self) -> List[Dict[str, Any]]:
        """Get all downloaders"""
        return self.execute_query("SELECT * FROM downloaders WHERE enabled = 1")
    
    # Charts data methods
    def save_charts_data(self, source: str, region: str, time_range: str, media_type: str, 
                         chart_data: str, expires_at: str) -> str:
        """Save charts data to database"""
        import time
        chart_id = f"chart_{source}_{region}_{time_range}_{media_type}_{int(time.time())}"
        query = """
            INSERT INTO charts_data (id, source, region, time_range, media_type, chart_data, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.execute_update(query, (chart_id, source, region, time_range, media_type, chart_data, expires_at))
        return chart_id
    
    def get_charts_data(self, source: str, region: str, time_range: str, media_type: str) -> Optional[Dict[str, Any]]:
        """Get charts data from database"""
        query = """
            SELECT * FROM charts_data 
            WHERE source = ? AND region = ? AND time_range = ? AND media_type = ? 
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ORDER BY created_at DESC LIMIT 1
        """
        result = self.execute_query(query, (source, region, time_range, media_type))
        return result[0] if result else None
    
    def save_chart_items(self, chart_id: str, chart_items: List[Dict[str, Any]]) -> bool:
        """Save chart items to database"""
        try:
            for i, item in enumerate(chart_items):
                item_id = f"item_{chart_id}_{i}"
                query = """
                    INSERT INTO chart_items (id, chart_id, title, type, rank, score, popularity, release_date, poster_url, provider)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                self.execute_update(query, (
                    item_id, chart_id, item.get('title', ''), item.get('type', ''), 
                    item.get('rank', 0), item.get('score'), item.get('popularity'),
                    item.get('release_date'), item.get('poster_url'), item.get('provider', '')
                ))
            return True
        except Exception:
            return False
    
    def get_chart_items(self, chart_id: str) -> List[Dict[str, Any]]:
        """Get chart items by chart ID"""
        return self.execute_query("SELECT * FROM chart_items WHERE chart_id = ? ORDER BY rank", (chart_id,))