#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仪表盘布局管理器
支持可拖拽布局和插件系统
参考MoviePilot的插件化仪表盘架构设计
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class WidgetType(Enum):
    """组件类型"""
    CHART = "chart"
    STATS = "stats"
    LIST = "list"
    ALERT = "alert"
    CUSTOM = "custom"


class LayoutBreakpoint(Enum):
    """布局断点"""
    XS = "xs"  # < 576px
    SM = "sm"  # ≥ 576px
    MD = "md"  # ≥ 768px
    LG = "lg"  # ≥ 992px
    XL = "xl"  # ≥ 1200px


@dataclass
class WidgetPosition:
    """组件位置"""
    x: int
    y: int
    w: int
    h: int
    minW: Optional[int] = None
    minH: Optional[int] = None
    maxW: Optional[int] = None
    maxH: Optional[int] = None
    static: bool = False


@dataclass
class DashboardWidget:
    """仪表盘组件"""
    id: str
    name: str
    type: WidgetType
    description: str
    component: str  # Vue组件名称
    config: Dict[str, Any]
    positions: Dict[str, WidgetPosition]  # 不同断点的位置
    enabled: bool = True
    configurable: bool = True
    refresh_interval: int = 30  # 刷新间隔（秒）


@dataclass
class DashboardLayout:
    """仪表盘布局"""
    id: str
    name: str
    description: str
    breakpoint: LayoutBreakpoint
    cols: int
    rowHeight: int
    margin: List[int]
    layouts: Dict[str, List[Dict[str, Any]]]  # 不同断点的布局
    widgets: List[str]  # 包含的组件ID列表
    created_at: str
    updated_at: str


class DashboardLayoutManager:
    """仪表盘布局管理器"""
    
    def __init__(self, config_dir: str = "config/dashboards"):
        self.config_dir = config_dir
        self.widgets: Dict[str, DashboardWidget] = {}
        self.layouts: Dict[str, DashboardLayout] = {}
        self.plugins: Dict[str, Any] = {}
        
        # 创建配置目录
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 初始化默认组件
        self._init_default_widgets()
        
        # 初始化默认布局
        self._init_default_layouts()
        
        # 加载用户配置
        self._load_user_config()
    
    def _init_default_widgets(self):
        """初始化默认组件"""
        default_widgets = [
            DashboardWidget(
                id="system_monitor",
                name="系统监控",
                type=WidgetType.CHART,
                description="实时监控CPU、内存、磁盘、网络使用情况",
                component="SystemMonitorChart",
                config={
                    "metrics": ["cpu", "memory", "disk", "network"],
                    "time_range": "1h",
                    "auto_refresh": True
                },
                positions={
                    "lg": WidgetPosition(x=0, y=0, w=6, h=4),
                    "md": WidgetPosition(x=0, y=0, w=6, h=4),
                    "sm": WidgetPosition(x=0, y=0, w=12, h=4)
                }
            ),
            DashboardWidget(
                id="download_status",
                name="下载状态",
                type=WidgetType.LIST,
                description="显示当前下载任务和速度",
                component="DownloadStatusList",
                config={
                    "show_speed": True,
                    "show_progress": True,
                    "max_items": 10
                },
                positions={
                    "lg": WidgetPosition(x=6, y=0, w=6, h=3),
                    "md": WidgetPosition(x=6, y=0, w=6, h=3),
                    "sm": WidgetPosition(x=0, y=4, w=12, h=3)
                }
            ),
            DashboardWidget(
                id="media_library",
                name="媒体库概览",
                type=WidgetType.STATS,
                description="显示媒体库统计信息",
                component="MediaLibraryStats",
                config={
                    "show_movies": True,
                    "show_tv_shows": True,
                    "show_music": True
                },
                positions={
                    "lg": WidgetPosition(x=0, y=4, w=4, h=2),
                    "md": WidgetPosition(x=0, y=4, w=6, h=2),
                    "sm": WidgetPosition(x=0, y=7, w=12, h=2)
                }
            ),
            DashboardWidget(
                id="ai_analytics",
                name="AI分析",
                type=WidgetType.CHART,
                description="显示AI分析结果和趋势",
                component="AIAnalyticsChart",
                config={
                    "show_confidence": True,
                    "show_processing_time": True,
                    "time_range": "24h"
                },
                positions={
                    "lg": WidgetPosition(x=4, y=4, w=8, h=3),
                    "md": WidgetPosition(x=0, y=6, w=12, h=3),
                    "sm": WidgetPosition(x=0, y=9, w=12, h=3)
                }
            ),
            DashboardWidget(
                id="scheduled_tasks",
                name="定时任务",
                type=WidgetType.LIST,
                description="显示定时任务状态",
                component="ScheduledTasksList",
                config={
                    "show_next_run": True,
                    "show_last_run": True,
                    "max_items": 5
                },
                positions={
                    "lg": WidgetPosition(x=0, y=6, w=6, h=3),
                    "md": WidgetPosition(x=0, y=9, w=12, h=3),
                    "sm": WidgetPosition(x=0, y=12, w=12, h=3)
                }
            ),
            DashboardWidget(
                id="system_alerts",
                name="系统警报",
                type=WidgetType.ALERT,
                description="显示系统警报信息",
                component="SystemAlerts",
                config={
                    "show_critical": True,
                    "show_warnings": True,
                    "max_alerts": 5
                },
                positions={
                    "lg": WidgetPosition(x=6, y=3, w=6, h=3),
                    "md": WidgetPosition(x=0, y=12, w=12, h=3),
                    "sm": WidgetPosition(x=0, y=15, w=12, h=3)
                }
            )
        ]
        
        for widget in default_widgets:
            self.widgets[widget.id] = widget
    
    def _init_default_layouts(self):
        """初始化默认布局"""
        default_layout = DashboardLayout(
            id="default",
            name="默认布局",
            description="系统默认的仪表盘布局",
            breakpoint=LayoutBreakpoint.LG,
            cols=12,
            rowHeight=100,
            margin=[10, 10],
            layouts={
                "lg": [
                    {"i": "system_monitor", "x": 0, "y": 0, "w": 6, "h": 4},
                    {"i": "download_status", "x": 6, "y": 0, "w": 6, "h": 3},
                    {"i": "media_library", "x": 0, "y": 4, "w": 4, "h": 2},
                    {"i": "ai_analytics", "x": 4, "y": 4, "w": 8, "h": 3},
                    {"i": "scheduled_tasks", "x": 0, "y": 6, "w": 6, "h": 3},
                    {"i": "system_alerts", "x": 6, "y": 3, "w": 6, "h": 3}
                ],
                "md": [
                    {"i": "system_monitor", "x": 0, "y": 0, "w": 6, "h": 4},
                    {"i": "download_status", "x": 6, "y": 0, "w": 6, "h": 3},
                    {"i": "media_library", "x": 0, "y": 4, "w": 6, "h": 2},
                    {"i": "ai_analytics", "x": 0, "y": 6, "w": 12, "h": 3},
                    {"i": "scheduled_tasks", "x": 0, "y": 9, "w": 12, "h": 3},
                    {"i": "system_alerts", "x": 0, "y": 12, "w": 12, "h": 3}
                ],
                "sm": [
                    {"i": "system_monitor", "x": 0, "y": 0, "w": 12, "h": 4},
                    {"i": "download_status", "x": 0, "y": 4, "w": 12, "h": 3},
                    {"i": "media_library", "x": 0, "y": 7, "w": 12, "h": 2},
                    {"i": "ai_analytics", "x": 0, "y": 9, "w": 12, "h": 3},
                    {"i": "scheduled_tasks", "x": 0, "y": 12, "w": 12, "h": 3},
                    {"i": "system_alerts", "x": 0, "y": 15, "w": 12, "h": 3}
                ]
            },
            widgets=["system_monitor", "download_status", "media_library", "ai_analytics", "scheduled_tasks", "system_alerts"],
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00"
        )
        
        self.layouts[default_layout.id] = default_layout
    
    def _load_user_config(self):
        """加载用户配置"""
        try:
            # 加载用户组件配置
            widgets_file = os.path.join(self.config_dir, "widgets.json")
            if os.path.exists(widgets_file):
                with open(widgets_file, 'r', encoding='utf-8') as f:
                    user_widgets = json.load(f)
                    for widget_data in user_widgets:
                        widget = DashboardWidget(**widget_data)
                        self.widgets[widget.id] = widget
            
            # 加载用户布局配置
            layouts_file = os.path.join(self.config_dir, "layouts.json")
            if os.path.exists(layouts_file):
                with open(layouts_file, 'r', encoding='utf-8') as f:
                    user_layouts = json.load(f)
                    for layout_data in user_layouts:
                        layout = DashboardLayout(**layout_data)
                        self.layouts[layout.id] = layout
                        
        except Exception as e:
            print(f"加载用户配置失败: {e}")
    
    def save_user_config(self):
        """保存用户配置"""
        try:
            # 保存组件配置
            widgets_file = os.path.join(self.config_dir, "widgets.json")
            user_widgets = [asdict(widget) for widget in self.widgets.values()]
            with open(widgets_file, 'w', encoding='utf-8') as f:
                json.dump(user_widgets, f, ensure_ascii=False, indent=2)
            
            # 保存布局配置
            layouts_file = os.path.join(self.config_dir, "layouts.json")
            user_layouts = [asdict(layout) for layout in self.layouts.values()]
            with open(layouts_file, 'w', encoding='utf-8') as f:
                json.dump(user_layouts, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存用户配置失败: {e}")
    
    def get_available_widgets(self) -> List[DashboardWidget]:
        """获取可用的组件列表"""
        return list(self.widgets.values())
    
    def get_widget(self, widget_id: str) -> Optional[DashboardWidget]:
        """获取指定组件"""
        return self.widgets.get(widget_id)
    
    def add_widget(self, widget: DashboardWidget) -> bool:
        """添加组件"""
        if widget.id in self.widgets:
            return False
        
        self.widgets[widget.id] = widget
        self.save_user_config()
        return True
    
    def update_widget(self, widget_id: str, updates: Dict[str, Any]) -> bool:
        """更新组件"""
        if widget_id not in self.widgets:
            return False
        
        widget = self.widgets[widget_id]
        for key, value in updates.items():
            if hasattr(widget, key):
                setattr(widget, key, value)
        
        widget.updated_at = "2024-01-01T00:00:00"  # 应该使用当前时间
        self.save_user_config()
        return True
    
    def remove_widget(self, widget_id: str) -> bool:
        """移除组件"""
        if widget_id not in self.widgets:
            return False
        
        del self.widgets[widget_id]
        
        # 从所有布局中移除该组件
        for layout in self.layouts.values():
            if widget_id in layout.widgets:
                layout.widgets.remove(widget_id)
        
        self.save_user_config()
        return True
    
    def get_layout(self, layout_id: str) -> Optional[DashboardLayout]:
        """获取指定布局"""
        return self.layouts.get(layout_id)
    
    def get_default_layout(self) -> DashboardLayout:
        """获取默认布局"""
        return self.layouts["default"]
    
    def create_layout(self, layout: DashboardLayout) -> bool:
        """创建新布局"""
        if layout.id in self.layouts:
            return False
        
        self.layouts[layout.id] = layout
        self.save_user_config()
        return True
    
    def update_layout(self, layout_id: str, updates: Dict[str, Any]) -> bool:
        """更新布局"""
        if layout_id not in self.layouts:
            return False
        
        layout = self.layouts[layout_id]
        for key, value in updates.items():
            if hasattr(layout, key):
                setattr(layout, key, value)
        
        layout.updated_at = "2024-01-01T00:00:00"  # 应该使用当前时间
        self.save_user_config()
        return True
    
    def delete_layout(self, layout_id: str) -> bool:
        """删除布局"""
        if layout_id == "default":
            return False  # 不能删除默认布局
        
        if layout_id not in self.layouts:
            return False
        
        del self.layouts[layout_id]
        self.save_user_config()
        return True
    
    def get_layout_for_breakpoint(self, layout_id: str, breakpoint: LayoutBreakpoint) -> List[Dict[str, Any]]:
        """获取指定断点的布局"""
        layout = self.get_layout(layout_id)
        if not layout:
            return []
        
        return layout.layouts.get(breakpoint.value, [])
    
    def register_plugin(self, plugin_id: str, plugin_config: Dict[str, Any]) -> bool:
        """注册插件"""
        try:
            # 检查插件配置
            if "widgets" not in plugin_config:
                return False
            
            # 注册插件组件
            for widget_config in plugin_config["widgets"]:
                widget = DashboardWidget(**widget_config)
                self.add_widget(widget)
            
            self.plugins[plugin_id] = plugin_config
            return True
            
        except Exception as e:
            print(f"注册插件失败: {e}")
            return False
    
    def unregister_plugin(self, plugin_id: str) -> bool:
        """注销插件"""
        if plugin_id not in self.plugins:
            return False
        
        # 移除插件组件
        plugin_config = self.plugins[plugin_id]
        for widget_config in plugin_config.get("widgets", []):
            widget_id = widget_config.get("id")
            if widget_id:
                self.remove_widget(widget_id)
        
        del self.plugins[plugin_id]
        return True
    
    def get_plugin_dashboard_config(self, plugin_id: str) -> Tuple[Dict, Dict, Optional[List[dict]]]:
        """获取插件的仪表盘配置"""
        """
        返回：1、仪表板col配置；2、全局配置；3、页面元素配置
        参考MoviePilot的插件接口设计
        """
        if plugin_id not in self.plugins:
            return {}, {}, None
        
        plugin_config = self.plugins[plugin_id]
        
        # 仪表板col配置
        col_config = {
            "xs": 24,  # 超小屏幕
            "sm": 12,  # 小屏幕
            "md": 8,   # 中等屏幕
            "lg": 6,   # 大屏幕
            "xl": 4    # 超大屏幕
        }
        
        # 全局配置
        global_config = {
            "refresh_interval": plugin_config.get("refresh_interval", 30),
            "auto_refresh": plugin_config.get("auto_refresh", True),
            "theme": plugin_config.get("theme", "default")
        }
        
        # 页面元素配置
        page_elements = []
        for widget_config in plugin_config.get("widgets", []):
            page_elements.append({
                "component": widget_config.get("component"),
                "props": widget_config.get("config", {}),
                "position": widget_config.get("positions", {}).get("lg", {})
            })
        
        return col_config, global_config, page_elements


# 全局布局管理器实例
dashboard_layout_manager = DashboardLayoutManager()