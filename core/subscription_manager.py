"""
订阅系统和自动化规则管理器
基于现有Subscription插件进行增强，支持RSS订阅和自动化规则
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)


class SubscriptionType(Enum):
    """订阅类型枚举"""
    RSS = "rss"
    TORZNAB = "torznab"
    CUSTOM = "custom"


class RuleAction(Enum):
    """规则动作枚举"""
    DOWNLOAD = "download"
    NOTIFY = "notify"
    IGNORE = "ignore"
    ADD_TO_WATCHLIST = "add_to_watchlist"


@dataclass
class Subscription:
    """订阅配置"""
    subscription_id: str
    name: str
    type: SubscriptionType
    url: str
    enabled: bool
    interval: int  # 检查间隔（秒）
    last_check: Optional[datetime]
    rules: List[Dict[str, Any]]
    category: str
    tags: List[str]


@dataclass
class SubscriptionItem:
    """订阅项"""
    item_id: str
    subscription_id: str
    title: str
    link: str
    description: Optional[str]
    pub_date: datetime
    size: Optional[int]
    seeders: Optional[int]
    leechers: Optional[int]
    category: str
    matched_rules: List[str]


@dataclass
class AutomationRule:
    """自动化规则"""
    rule_id: str
    name: str
    priority: int
    conditions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    enabled: bool
    last_matched: Optional[datetime]
    match_count: int


class SubscriptionManager:
    """订阅管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.subscriptions: Dict[str, Subscription] = {}
        self.rules: Dict[str, AutomationRule] = {}
        self.history: List[Dict[str, Any]] = []
        self.is_running = False
        self.check_task = None
        
    async def initialize(self) -> bool:
        """初始化订阅管理器"""
        logger.info("初始化订阅管理器")
        
        try:
            # 加载配置中的订阅和规则
            await self._load_config()
            
            # 启动订阅检查任务
            await self.start()
            
            logger.info("订阅管理器初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"订阅管理器初始化失败: {e}")
            return False
    
    async def _load_config(self):
        """加载配置"""
        # 加载订阅配置
        subscriptions_config = self.config.get('subscriptions', {})
        for sub_id, sub_config in subscriptions_config.items():
            subscription = Subscription(
                subscription_id=sub_id,
                name=sub_config.get('name', sub_id),
                type=SubscriptionType(sub_config.get('type', 'rss')),
                url=sub_config.get('url', ''),
                enabled=sub_config.get('enabled', True),
                interval=sub_config.get('interval', 3600),
                last_check=None,
                rules=sub_config.get('rules', []),
                category=sub_config.get('category', 'general'),
                tags=sub_config.get('tags', [])
            )
            self.subscriptions[sub_id] = subscription
        
        # 加载自动化规则
        rules_config = self.config.get('automation_rules', {})
        for rule_id, rule_config in rules_config.items():
            rule = AutomationRule(
                rule_id=rule_id,
                name=rule_config.get('name', rule_id),
                priority=rule_config.get('priority', 0),
                conditions=rule_config.get('conditions', []),
                actions=rule_config.get('actions', []),
                enabled=rule_config.get('enabled', True),
                last_matched=None,
                match_count=0
            )
            self.rules[rule_id] = rule
    
    async def start(self):
        """启动订阅管理器"""
        if self.is_running:
            return
        
        self.is_running = True
        self.check_task = asyncio.create_task(self._check_loop())
        logger.info("订阅管理器已启动")
    
    async def stop(self):
        """停止订阅管理器"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.check_task:
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("订阅管理器已停止")
    
    async def _check_loop(self):
        """订阅检查循环"""
        while self.is_running:
            try:
                await self._check_all_subscriptions()
                await asyncio.sleep(60)  # 每分钟检查一次是否有订阅需要更新
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"订阅检查循环异常: {e}")
                await asyncio.sleep(300)  # 出错后等待5分钟重试
    
    async def _check_all_subscriptions(self):
        """检查所有订阅"""
        current_time = datetime.now()
        
        for subscription in self.subscriptions.values():
            if not subscription.enabled:
                continue
            
            # 检查是否需要更新
            if (subscription.last_check is None or 
                (current_time - subscription.last_check).total_seconds() >= subscription.interval):
                
                await self._check_subscription(subscription)
                subscription.last_check = current_time
    
    async def _check_subscription(self, subscription: Subscription):
        """检查单个订阅"""
        logger.info(f"检查订阅: {subscription.name}")
        
        try:
            # 获取订阅内容
            items = await self._fetch_subscription_items(subscription)
            
            # 处理每个订阅项
            for item in items:
                await self._process_subscription_item(subscription, item)
            
            logger.info(f"订阅检查完成: {subscription.name}, 找到 {len(items)} 个项")
            
        except Exception as e:
            logger.error(f"检查订阅失败 {subscription.name}: {e}")
    
    async def _fetch_subscription_items(self, subscription: Subscription) -> List[SubscriptionItem]:
        """获取订阅内容"""
        items = []
        
        if subscription.type == SubscriptionType.RSS:
            items = await self._fetch_rss_items(subscription.url)
        elif subscription.type == SubscriptionType.TORZNAB:
            items = await self._fetch_torznab_items(subscription.url)
        
        return items
    
    async def _fetch_rss_items(self, url: str) -> List[SubscriptionItem]:
        """获取RSS订阅内容"""
        # 这里应该实现实际的RSS解析逻辑
        # 暂时返回模拟数据
        return [
            SubscriptionItem(
                item_id="item_1",
                subscription_id="rss_1",
                title="示例电影 2024 1080p",
                link="magnet:?xt=urn:btih:example1",
                description="示例电影描述",
                pub_date=datetime.now(),
                size=1024 * 1024 * 1024,  # 1GB
                seeders=10,
                leechers=5,
                category="movies",
                matched_rules=[]
            )
        ]
    
    async def _fetch_torznab_items(self, url: str) -> List[SubscriptionItem]:
        """获取Torznab订阅内容"""
        # 这里应该实现实际的Torznab API调用
        # 暂时返回模拟数据
        return [
            SubscriptionItem(
                item_id="item_2",
                subscription_id="torznab_1",
                title="示例电视剧 S01E01 720p",
                link="magnet:?xt=urn:btih:example2",
                description="示例电视剧描述",
                pub_date=datetime.now() - timedelta(hours=1),
                size=512 * 1024 * 1024,  # 512MB
                seeders=20,
                leechers=10,
                category="tv_shows",
                matched_rules=[]
            )
        ]
    
    async def _process_subscription_item(self, subscription: Subscription, item: SubscriptionItem):
        """处理订阅项"""
        # 应用订阅规则
        matched_rules = await self._apply_subscription_rules(subscription, item)
        item.matched_rules = matched_rules
        
        if matched_rules:
            # 应用自动化规则
            await self._apply_automation_rules(subscription, item, matched_rules)
            
            # 记录历史
            self._add_to_history(subscription, item, matched_rules)
    
    async def _apply_subscription_rules(self, subscription: Subscription, 
                                      item: SubscriptionItem) -> List[str]:
        """应用订阅规则"""
        matched_rules = []
        
        for rule in subscription.rules:
            if await self._evaluate_rule(rule, item):
                matched_rules.append(rule.get('name', 'unnamed_rule'))
        
        return matched_rules
    
    async def _apply_automation_rules(self, subscription: Subscription, 
                                    item: SubscriptionItem, matched_rules: List[str]):
        """应用自动化规则"""
        # 按优先级排序规则
        sorted_rules = sorted(self.rules.values(), key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            if not rule.enabled:
                continue
            
            # 检查规则条件
            if await self._evaluate_rule_conditions(rule.conditions, subscription, item):
                # 执行规则动作
                await self._execute_rule_actions(rule.actions, subscription, item)
                
                # 更新规则统计
                rule.last_matched = datetime.now()
                rule.match_count += 1
                
                logger.info(f"自动化规则匹配: {rule.name} -> {item.title}")
                break  # 只执行最高优先级的匹配规则
    
    async def _evaluate_rule(self, rule: Dict[str, Any], item: SubscriptionItem) -> bool:
        """评估单个规则"""
        conditions = rule.get('conditions', [])
        
        for condition in conditions:
            if not await self._evaluate_condition(condition, item):
                return False
        
        return True
    
    async def _evaluate_condition(self, condition: Dict[str, Any], item: SubscriptionItem) -> bool:
        """评估单个条件"""
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        # 获取字段值
        field_value = getattr(item, field, None)
        if field_value is None:
            field_value = item.__dict__.get(field)
        
        # 应用操作符
        if operator == 'contains':
            return str(value).lower() in str(field_value).lower()
        elif operator == 'not_contains':
            return str(value).lower() not in str(field_value).lower()
        elif operator == 'equals':
            return str(field_value) == str(value)
        elif operator == 'not_equals':
            return str(field_value) != str(value)
        elif operator == 'greater_than':
            return float(field_value or 0) > float(value)
        elif operator == 'less_than':
            return float(field_value or 0) < float(value)
        elif operator == 'regex':
            return bool(re.search(value, str(field_value or '')))
        
        return False
    
    async def _evaluate_rule_conditions(self, conditions: List[Dict[str, Any]], 
                                       subscription: Subscription, item: SubscriptionItem) -> bool:
        """评估规则条件"""
        for condition in conditions:
            if not await self._evaluate_advanced_condition(condition, subscription, item):
                return False
        
        return True
    
    async def _evaluate_advanced_condition(self, condition: Dict[str, Any], 
                                         subscription: Subscription, item: SubscriptionItem) -> bool:
        """评估高级条件"""
        condition_type = condition.get('type')
        
        if condition_type == 'subscription_field':
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            field_value = getattr(subscription, field, None)
            return self._compare_values(field_value, operator, value)
        
        elif condition_type == 'item_field':
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            field_value = getattr(item, field, None)
            if field_value is None:
                field_value = item.__dict__.get(field)
            
            return self._compare_values(field_value, operator, value)
        
        elif condition_type == 'custom':
            # 自定义条件评估
            return await self._evaluate_custom_condition(condition, subscription, item)
        
        return False
    
    def _compare_values(self, field_value, operator, value):
        """比较值"""
        if operator == 'equals':
            return str(field_value) == str(value)
        elif operator == 'not_equals':
            return str(field_value) != str(value)
        elif operator == 'contains':
            return str(value).lower() in str(field_value).lower()
        # 其他操作符...
        
        return False
    
    async def _evaluate_custom_condition(self, condition: Dict[str, Any], 
                                        subscription: Subscription, item: SubscriptionItem) -> bool:
        """评估自定义条件"""
        # 这里可以实现复杂的自定义条件逻辑
        # 例如：检查文件大小、种子数、发布时间等
        
        condition_name = condition.get('name')
        
        if condition_name == 'high_seeders':
            return item.seeders and item.seeders > 50
        elif condition_name == 'recent_publish':
            if item.pub_date:
                return (datetime.now() - item.pub_date).total_seconds() < 24 * 3600  # 24小时内
        elif condition_name == 'proper_size':
            if item.size:
                return 100 * 1024 * 1024 < item.size < 10 * 1024 * 1024 * 1024  # 100MB - 10GB
        
        return False
    
    async def _execute_rule_actions(self, actions: List[Dict[str, Any]], 
                                  subscription: Subscription, item: SubscriptionItem):
        """执行规则动作"""
        for action in actions:
            await self._execute_action(action, subscription, item)
    
    async def _execute_action(self, action: Dict[str, Any], 
                            subscription: Subscription, item: SubscriptionItem):
        """执行单个动作"""
        action_type = action.get('type')
        
        if action_type == 'download':
            await self._action_download(subscription, item, action)
        elif action_type == 'notify':
            await self._action_notify(subscription, item, action)
        elif action_type == 'add_to_watchlist':
            await self._action_add_to_watchlist(subscription, item, action)
    
    async def _action_download(self, subscription: Subscription, 
                              item: SubscriptionItem, action: Dict[str, Any]):
        """下载动作"""
        logger.info(f"执行下载动作: {item.title}")
        
        # 这里应该调用下载管理器
        # 暂时记录日志
        pass
    
    async def _action_notify(self, subscription: Subscription, 
                           item: SubscriptionItem, action: Dict[str, Any]):
        """通知动作"""
        logger.info(f"执行通知动作: {item.title}")
        
        # 这里应该调用通知系统
        # 暂时记录日志
        pass
    
    async def _action_add_to_watchlist(self, subscription: Subscription, 
                                     item: SubscriptionItem, action: Dict[str, Any]):
        """添加到观看列表动作"""
        logger.info(f"执行添加到观看列表动作: {item.title}")
        
        # 这里应该调用媒体库管理器
        # 暂时记录日志
        pass
    
    def _add_to_history(self, subscription: Subscription, 
                       item: SubscriptionItem, matched_rules: List[str]):
        """添加到历史记录"""
        history_entry = {
            'timestamp': datetime.now(),
            'subscription_id': subscription.subscription_id,
            'subscription_name': subscription.name,
            'item_title': item.title,
            'item_link': item.link,
            'matched_rules': matched_rules,
            'actions_taken': ['processed']  # 实际应该记录执行的动作
        }
        
        self.history.append(history_entry)
        
        # 限制历史记录大小
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
    
    async def add_subscription(self, subscription: Subscription) -> bool:
        """添加订阅"""
        if subscription.subscription_id in self.subscriptions:
            logger.warning(f"订阅已存在: {subscription.subscription_id}")
            return False
        
        self.subscriptions[subscription.subscription_id] = subscription
        logger.info(f"订阅添加成功: {subscription.name}")
        return True
    
    async def remove_subscription(self, subscription_id: str) -> bool:
        """移除订阅"""
        if subscription_id not in self.subscriptions:
            logger.warning(f"订阅不存在: {subscription_id}")
            return False
        
        del self.subscriptions[subscription_id]
        logger.info(f"订阅移除成功: {subscription_id}")
        return True
    
    async def get_subscription_stats(self) -> Dict[str, Any]:
        """获取订阅统计信息"""
        stats = {
            'total_subscriptions': len(self.subscriptions),
            'enabled_subscriptions': len([s for s in self.subscriptions.values() if s.enabled]),
            'total_rules': len(self.rules),
            'enabled_rules': len([r for r in self.rules.values() if r.enabled]),
            'history_count': len(self.history),
            'last_check': max([s.last_check for s in self.subscriptions.values() if s.last_check] or [None])
        }
        
        return stats
    
    async def get_recent_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的历史记录"""
        return self.history[-limit:]


# 使用示例
async def main():
    """使用示例"""
    config = {
        'subscriptions': {
            'movie_rss': {
                'name': '电影RSS订阅',
                'type': 'rss',
                'url': 'https://example.com/rss/movies',
                'enabled': True,
                'interval': 3600,
                'rules': [
                    {
                        'name': '高清电影规则',
                        'conditions': [
                            {'field': 'title', 'operator': 'contains', 'value': '1080p'},
                            {'field': 'seeders', 'operator': 'greater_than', 'value': 5}
                        ]
                    }
                ],
                'category': 'movies',
                'tags': ['movie', 'rss']
            }
        },
        'automation_rules': {
            'auto_download_movies': {
                'name': '自动下载电影',
                'priority': 10,
                'enabled': True,
                'conditions': [
                    {
                        'type': 'subscription_field',
                        'field': 'category',
                        'operator': 'equals',
                        'value': 'movies'
                    },
                    {
                        'type': 'custom',
                        'name': 'high_seeders'
                    }
                ],
                'actions': [
                    {'type': 'download'}
                ]
            }
        }
    }
    
    manager = SubscriptionManager(config)
    
    # 初始化管理器
    success = await manager.initialize()
    if not success:
        print("初始化失败")
        return
    
    try:
        # 运行一段时间
        await asyncio.sleep(120)
        
        # 获取统计信息
        stats = await manager.get_subscription_stats()
        print(f"订阅统计: {stats}")
        
        # 获取最近历史
        history = await manager.get_recent_history(10)
        print(f"最近历史: {len(history)} 条记录")
        
    finally:
        await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())