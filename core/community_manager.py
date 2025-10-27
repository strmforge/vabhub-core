#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
社区管理器
支持用户分享、模板市场、插件市场、社区交流
"""

import os
import json
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path


class CommunityManager:
    """社区管理器"""
    
    def __init__(self):
        self.community_dir = "community"
        self.users_dir = os.path.join(self.community_dir, "users")
        self.share_dir = os.path.join(self.community_dir, "shared")
        self.market_dir = os.path.join(self.community_dir, "market")
        self.forum_dir = os.path.join(self.community_dir, "forum")
        
        # 创建社区目录结构
        os.makedirs(self.users_dir, exist_ok=True)
        os.makedirs(self.share_dir, exist_ok=True)
        os.makedirs(self.market_dir, exist_ok=True)
        os.makedirs(self.forum_dir, exist_ok=True)
        
        # 用户数据
        self.users = {}
        self.shared_items = {}
        self.market_items = {}
        self.forum_posts = {}
        
        # 加载数据
        self.load_community_data()
    
    def load_community_data(self):
        """加载社区数据"""
        try:
            # 加载用户数据
            users_file = os.path.join(self.community_dir, "users.json")
            if os.path.exists(users_file):
                with open(users_file, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            
            # 加载分享数据
            shared_file = os.path.join(self.community_dir, "shared.json")
            if os.path.exists(shared_file):
                with open(shared_file, 'r', encoding='utf-8') as f:
                    self.shared_items = json.load(f)
            
            # 加载市场数据
            market_file = os.path.join(self.community_dir, "market.json")
            if os.path.exists(market_file):
                with open(market_file, 'r', encoding='utf-8') as f:
                    self.market_items = json.load(f)
            
            # 加载论坛数据
            forum_file = os.path.join(self.community_dir, "forum.json")
            if os.path.exists(forum_file):
                with open(forum_file, 'r', encoding='utf-8') as f:
                    self.forum_posts = json.load(f)
                    
        except Exception as e:
            print(f"加载社区数据失败: {e}")
    
    def save_community_data(self):
        """保存社区数据"""
        try:
            # 保存用户数据
            users_file = os.path.join(self.community_dir, "users.json")
            with open(users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False)
            
            # 保存分享数据
            shared_file = os.path.join(self.community_dir, "shared.json")
            with open(shared_file, 'w', encoding='utf-8') as f:
                json.dump(self.shared_items, f, indent=2, ensure_ascii=False)
            
            # 保存市场数据
            market_file = os.path.join(self.community_dir, "market.json")
            with open(market_file, 'w', encoding='utf-8') as f:
                json.dump(self.market_items, f, indent=2, ensure_ascii=False)
            
            # 保存论坛数据
            forum_file = os.path.join(self.community_dir, "forum.json")
            with open(forum_file, 'w', encoding='utf-8') as f:
                json.dump(self.forum_posts, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"保存社区数据失败: {e}")
    
    def register_user(self, username: str, email: str, password: str) -> bool:
        """注册用户"""
        try:
            # 检查用户是否已存在
            if username in self.users:
                return False
            
            # 创建用户数据
            user_id = hashlib.md5(username.encode()).hexdigest()[:8]
            
            self.users[username] = {
                "user_id": user_id,
                "username": username,
                "email": email,
                "password_hash": hashlib.md5(password.encode()).hexdigest(),
                "registration_date": datetime.now().isoformat(),
                "last_login": datetime.now().isoformat(),
                "profile": {
                    "display_name": username,
                    "avatar": "",
                    "bio": "",
                    "location": ""
                },
                "stats": {
                    "shared_items": 0,
                    "downloads": 0,
                    "likes": 0,
                    "followers": 0,
                    "following": 0
                },
                "preferences": {
                    "theme": "light",
                    "language": "zh-CN",
                    "notifications": True
                }
            }
            
            self.save_community_data()
            return True
            
        except Exception as e:
            print(f"注册用户失败: {e}")
            return False
    
    def login_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """用户登录"""
        try:
            user = self.users.get(username)
            if not user:
                return None
            
            # 验证密码
            password_hash = hashlib.md5(password.encode()).hexdigest()
            if user["password_hash"] != password_hash:
                return None
            
            # 更新最后登录时间
            user["last_login"] = datetime.now().isoformat()
            self.save_community_data()
            
            return user
            
        except Exception as e:
            print(f"用户登录失败: {e}")
            return None
    
    def share_template(self, username: str, template_type: str, template_data: Dict[str, Any], 
                      title: str, description: str, tags: List[str]) -> Optional[str]:
        """分享模板"""
        try:
            if username not in self.users:
                return None
            
            # 生成分享ID
            share_id = hashlib.md5(
                f"{username}_{template_type}_{datetime.now().isoformat()}".encode()
            ).hexdigest()[:12]
            
            # 创建分享项目
            shared_item = {
                "share_id": share_id,
                "username": username,
                "template_type": template_type,
                "template_data": template_data,
                "title": title,
                "description": description,
                "tags": tags,
                "share_date": datetime.now().isoformat(),
                "downloads": 0,
                "likes": 0,
                "comments": [],
                "rating": 0.0,
                "visibility": "public"
            }
            
            # 保存分享项目
            self.shared_items[share_id] = shared_item
            
            # 更新用户统计
            self.users[username]["stats"]["shared_items"] += 1
            
            self.save_community_data()
            return share_id
            
        except Exception as e:
            print(f"分享模板失败: {e}")
            return None
    
    def download_template(self, share_id: str, username: str) -> Optional[Dict[str, Any]]:
        """下载模板"""
        try:
            shared_item = self.shared_items.get(share_id)
            if not shared_item:
                return None
            
            # 更新下载统计
            shared_item["downloads"] += 1
            
            # 更新用户统计
            if username in self.users:
                self.users[username]["stats"]["downloads"] += 1
            
            # 更新分享者统计
            sharer_username = shared_item["username"]
            if sharer_username in self.users:
                self.users[sharer_username]["stats"]["downloads"] += 1
            
            self.save_community_data()
            return shared_item["template_data"]
            
        except Exception as e:
            print(f"下载模板失败: {e}")
            return None
    
    def like_template(self, share_id: str, username: str) -> bool:
        """点赞模板"""
        try:
            shared_item = self.shared_items.get(share_id)
            if not shared_item:
                return False
            
            # 检查是否已经点赞
            if "likes" not in shared_item:
                shared_item["likes"] = []
            
            if username in shared_item["likes"]:
                return False  # 已经点赞过
            
            # 添加点赞
            shared_item["likes"].append(username)
            
            # 更新分享者统计
            sharer_username = shared_item["username"]
            if sharer_username in self.users:
                self.users[sharer_username]["stats"]["likes"] += 1
            
            self.save_community_data()
            return True
            
        except Exception as e:
            print(f"点赞模板失败: {e}")
            return False
    
    def search_templates(self, query: str, template_type: str = None, 
                        tags: List[str] = None, sort_by: str = "popularity") -> List[Dict[str, Any]]:
        """搜索模板"""
        try:
            results = []
            
            for share_id, item in self.shared_items.items():
                # 过滤条件
                if template_type and item["template_type"] != template_type:
                    continue
                
                if tags and not any(tag in item.get("tags", []) for tag in tags):
                    continue
                
                # 搜索条件
                search_text = f"{item['title']} {item['description']} {' '.join(item.get('tags', []))}".lower()
                if query.lower() not in search_text:
                    continue
                
                results.append(item)
            
            # 排序
            if sort_by == "popularity":
                results.sort(key=lambda x: x.get("downloads", 0) + len(x.get("likes", [])), reverse=True)
            elif sort_by == "date":
                results.sort(key=lambda x: x["share_date"], reverse=True)
            elif sort_by == "rating":
                results.sort(key=lambda x: x.get("rating", 0), reverse=True)
            
            return results[:50]  # 限制返回数量
            
        except Exception as e:
            print(f"搜索模板失败: {e}")
            return []
    
    def create_market_item(self, username: str, item_type: str, item_data: Dict[str, Any], 
                          title: str, description: str, price: float, tags: List[str]) -> Optional[str]:
        """创建市场项目"""
        try:
            if username not in self.users:
                return None
            
            # 生成项目ID
            item_id = hashlib.md5(
                f"{username}_{item_type}_{datetime.now().isoformat()}".encode()
            ).hexdigest()[:12]
            
            # 创建市场项目
            market_item = {
                "item_id": item_id,
                "username": username,
                "item_type": item_type,  # plugin, template, theme
                "item_data": item_data,
                "title": title,
                "description": description,
                "price": price,
                "tags": tags,
                "create_date": datetime.now().isoformat(),
                "sales": 0,
                "revenue": 0.0,
                "reviews": [],
                "rating": 0.0,
                "status": "active"
            }
            
            # 保存市场项目
            self.market_items[item_id] = market_item
            self.save_community_data()
            return item_id
            
        except Exception as e:
            print(f"创建市场项目失败: {e}")
            return None
    
    def create_forum_post(self, username: str, title: str, content: str, 
                          category: str, tags: List[str]) -> Optional[str]:
        """创建论坛帖子"""
        try:
            if username not in self.users:
                return None
            
            # 生成帖子ID
            post_id = hashlib.md5(
                f"{username}_{title}_{datetime.now().isoformat()}".encode()
            ).hexdigest()[:12]
            
            # 创建论坛帖子
            forum_post = {
                "post_id": post_id,
                "username": username,
                "title": title,
                "content": content,
                "category": category,
                "tags": tags,
                "create_date": datetime.now().isoformat(),
                "views": 0,
                "replies": [],
                "likes": [],
                "status": "active"
            }
            
            # 保存论坛帖子
            self.forum_posts[post_id] = forum_post
            self.save_community_data()
            return post_id
            
        except Exception as e:
            print(f"创建论坛帖子失败: {e}")
            return None
    
    def get_hot_templates(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门模板"""
        try:
            templates = list(self.shared_items.values())
            
            # 按热度排序（下载量 + 点赞数）
            templates.sort(key=lambda x: x.get("downloads", 0) + len(x.get("likes", [])), reverse=True)
            
            return templates[:limit]
            
        except Exception as e:
            print(f"获取热门模板失败: {e}")
            return []
    
    def get_user_stats(self, username: str) -> Optional[Dict[str, Any]]:
        """获取用户统计信息"""
        try:
            user = self.users.get(username)
            if not user:
                return None
            
            # 计算用户贡献
            user_contributions = {
                "templates_shared": 0,
                "templates_downloaded": 0,
                "total_likes": 0,
                "market_items": 0,
                "forum_posts": 0
            }
            
            # 统计用户分享的模板
            for item in self.shared_items.values():
                if item["username"] == username:
                    user_contributions["templates_shared"] += 1
            
            # 统计用户的市场项目
            for item in self.market_items.values():
                if item["username"] == username:
                    user_contributions["market_items"] += 1
            
            # 统计用户的论坛帖子
            for post in self.forum_posts.values():
                if post["username"] == username:
                    user_contributions["forum_posts"] += 1
            
            return {
                "user_info": user,
                "contributions": user_contributions
            }
            
        except Exception as e:
            print(f"获取用户统计失败: {e}")
            return None
    
    def get_community_stats(self) -> Dict[str, Any]:
        """获取社区统计信息"""
        try:
            stats = {
                "total_users": len(self.users),
                "total_shared_templates": len(self.shared_items),
                "total_market_items": len(self.market_items),
                "total_forum_posts": len(self.forum_posts),
                "total_downloads": sum(item.get("downloads", 0) for item in self.shared_items.values()),
                "total_likes": sum(len(item.get("likes", [])) for item in self.shared_items.values()),
                "active_users": self._get_active_users_count(),
                "popular_categories": self._get_popular_categories()
            }
            
            return stats
            
        except Exception as e:
            print(f"获取社区统计失败: {e}")
            return {}
    
    def _get_active_users_count(self) -> int:
        """获取活跃用户数量（最近30天有活动的用户）"""
        try:
            active_threshold = datetime.now() - timedelta(days=30)
            active_count = 0
            
            for user in self.users.values():
                last_login = datetime.fromisoformat(user["last_login"])
                if last_login > active_threshold:
                    active_count += 1
            
            return active_count
            
        except Exception as e:
            print(f"获取活跃用户失败: {e}")
            return 0
    
    def _get_popular_categories(self) -> List[Dict[str, Any]]:
        """获取热门分类"""
        try:
            categories = {}
            
            for item in self.shared_items.values():
                template_type = item["template_type"]
                if template_type not in categories:
                    categories[template_type] = 0
                categories[template_type] += 1
            
            # 转换为列表并排序
            popular_categories = [
                {"category": cat, "count": count}
                for cat, count in categories.items()
            ]
            popular_categories.sort(key=lambda x: x["count"], reverse=True)
            
            return popular_categories[:10]
            
        except Exception as e:
            print(f"获取热门分类失败: {e}")
            return []