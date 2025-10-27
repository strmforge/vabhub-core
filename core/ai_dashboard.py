#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能分析仪表板
实时展示AI分析结果、统计信息和性能指标
"""

import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class AIDashboard:
    """AI智能分析仪表板"""
    
    def __init__(self):
        self.analysis_history = []
        self.user_interactions = []
        self.service_performance = defaultdict(list)
        self.start_time = time.time()
    
    def record_analysis(self, analysis_result: Dict[str, Any], service_used: str, processing_time: float):
        """记录分析结果"""
        record = {
            "timestamp": time.time(),
            "file_path": analysis_result.get("file_path", ""),
            "file_name": analysis_result.get("file_name", ""),
            "media_type": analysis_result.get("media_type", "unknown"),
            "ai_confidence": analysis_result.get("ai_confidence", 0.0),
            "service_used": service_used,
            "processing_time": processing_time,
            "analysis_method": analysis_result.get("analysis_method", "unknown")
        }
        
        self.analysis_history.append(record)
        
        # 记录服务性能
        self.service_performance[service_used].append({
            "timestamp": time.time(),
            "processing_time": processing_time,
            "confidence": analysis_result.get("ai_confidence", 0.0),
            "success": True
        })
        
        # 保持历史记录大小
        if len(self.analysis_history) > 1000:
            self.analysis_history = self.analysis_history[-1000:]
    
    def record_user_interaction(self, interaction_type: str, user_id: str = "anonymous", details: Dict[str, Any] = None):
        """记录用户交互"""
        if details is None:
            details = {}
        
        interaction = {
            "timestamp": time.time(),
            "interaction_type": interaction_type,
            "user_id": user_id,
            "details": details
        }
        
        self.user_interactions.append(interaction)
        
        # 保持交互记录大小
        if len(self.user_interactions) > 5000:
            self.user_interactions = self.user_interactions[-5000:]
    
    def get_dashboard_overview(self) -> Dict[str, Any]:
        """获取仪表板概览"""
        total_analyses = len(self.analysis_history)
        
        if total_analyses == 0:
            return {
                "total_analyses": 0,
                "average_confidence": 0.0,
                "average_processing_time": 0.0,
                "uptime": time.time() - self.start_time,
                "service_distribution": {},
                "media_type_distribution": {}
            }
        
        # 计算平均置信度
        total_confidence = sum(r["ai_confidence"] for r in self.analysis_history)
        average_confidence = total_confidence / total_analyses
        
        # 计算平均处理时间
        total_processing_time = sum(r["processing_time"] for r in self.analysis_history)
        average_processing_time = total_processing_time / total_analyses
        
        # 服务分布
        service_distribution = defaultdict(int)
        for record in self.analysis_history:
            service_distribution[record["service_used"]] += 1
        
        # 媒体类型分布
        media_type_distribution = defaultdict(int)
        for record in self.analysis_history:
            media_type_distribution[record["media_type"]] += 1
        
        return {
            "total_analyses": total_analyses,
            "average_confidence": average_confidence,
            "average_processing_time": average_processing_time,
            "uptime": time.time() - self.start_time,
            "service_distribution": dict(service_distribution),
            "media_type_distribution": dict(media_type_distribution)
        }
    
    def get_trend_analysis(self, time_range: str = "24h") -> Dict[str, Any]:
        """获取趋势分析"""
        if time_range == "24h":
            cutoff_time = time.time() - 24 * 3600
        elif time_range == "7d":
            cutoff_time = time.time() - 7 * 24 * 3600
        elif time_range == "30d":
            cutoff_time = time.time() - 30 * 24 * 3600
        else:
            cutoff_time = 0  # 全部数据
        
        # 过滤时间范围内的记录
        recent_analyses = [r for r in self.analysis_history if r["timestamp"] >= cutoff_time]
        
        if not recent_analyses:
            return {
                "time_range": time_range,
                "total_analyses": 0,
                "hourly_analyses": [],
                "confidence_trend": [],
                "processing_time_trend": []
            }
        
        # 按小时分组
        hourly_analyses = defaultdict(int)
        confidence_by_hour = defaultdict(list)
        processing_time_by_hour = defaultdict(list)
        
        for record in recent_analyses:
            hour = datetime.fromtimestamp(record["timestamp"]).strftime('%Y-%m-%d %H:00')
            hourly_analyses[hour] += 1
            confidence_by_hour[hour].append(record["ai_confidence"])
            processing_time_by_hour[hour].append(record["processing_time"])
        
        # 计算趋势数据
        hourly_data = []
        confidence_trend = []
        processing_time_trend = []
        
        for hour in sorted(hourly_analyses.keys()):
            hourly_data.append({
                "hour": hour,
                "count": hourly_analyses[hour]
            })
            
            if confidence_by_hour[hour]:
                confidence_trend.append({
                    "hour": hour,
                    "average_confidence": sum(confidence_by_hour[hour]) / len(confidence_by_hour[hour])
                })
            
            if processing_time_by_hour[hour]:
                processing_time_trend.append({
                    "hour": hour,
                    "average_processing_time": sum(processing_time_by_hour[hour]) / len(processing_time_by_hour[hour])
                })
        
        return {
            "time_range": time_range,
            "total_analyses": len(recent_analyses),
            "hourly_analyses": hourly_data,
            "confidence_trend": confidence_trend,
            "processing_time_trend": processing_time_trend
        }
    
    def get_service_comparison(self) -> Dict[str, Any]:
        """获取服务性能比较"""
        service_stats = {}
        
        for service_name, records in self.service_performance.items():
            if not records:
                continue
            
            total_records = len(records)
            success_records = [r for r in records if r.get("success", True)]
            success_rate = len(success_records) / total_records if total_records > 0 else 0
            
            avg_processing_time = sum(r["processing_time"] for r in records) / total_records
            avg_confidence = sum(r["confidence"] for r in records) / total_records
            
            service_stats[service_name] = {
                "total_requests": total_records,
                "success_rate": success_rate,
                "average_processing_time": avg_processing_time,
                "average_confidence": avg_confidence,
                "last_used": max(r["timestamp"] for r in records) if records else 0
            }
        
        return service_stats
    
    def get_user_insights(self, user_id: str = None) -> Dict[str, Any]:
        """获取用户洞察"""
        if user_id:
            user_interactions = [i for i in self.user_interactions if i["user_id"] == user_id]
        else:
            user_interactions = self.user_interactions
        
        if not user_interactions:
            return {
                "total_interactions": 0,
                "interaction_types": {},
                "active_hours": [],
                "preferred_services": {}
            }
        
        # 交互类型分布
        interaction_types = defaultdict(int)
        for interaction in user_interactions:
            interaction_types[interaction["interaction_type"]] += 1
        
        # 活跃时间段分析
        active_hours = defaultdict(int)
        for interaction in user_interactions:
            hour = datetime.fromtimestamp(interaction["timestamp"]).hour
            active_hours[hour] += 1
        
        # 用户偏好的服务（通过分析记录推断）
        user_analyses = [r for r in self.analysis_history if any(
            i["user_id"] == (user_id or "anonymous") 
            for i in self.user_interactions 
            if i["timestamp"] == r["timestamp"]
        )]
        
        preferred_services = defaultdict(int)
        for analysis in user_analyses:
            preferred_services[analysis["service_used"]] += 1
        
        return {
            "total_interactions": len(user_interactions),
            "interaction_types": dict(interaction_types),
            "active_hours": [{"hour": h, "count": c} for h, c in sorted(active_hours.items())],
            "preferred_services": dict(preferred_services)
        }
    
    def get_recommendation_performance(self) -> Dict[str, Any]:
        """获取推荐性能指标"""
        # 这里可以集成推荐系统的性能数据
        recommendation_interactions = [
            i for i in self.user_interactions 
            if i["interaction_type"] in ["recommendation_click", "recommendation_view"]
        ]
        
        total_recommendations = len([i for i in recommendation_interactions if i["interaction_type"] == "recommendation_view"])
        total_clicks = len([i for i in recommendation_interactions if i["interaction_type"] == "recommendation_click"])
        
        click_rate = total_clicks / total_recommendations if total_recommendations > 0 else 0
        
        return {
            "total_recommendations": total_recommendations,
            "total_clicks": total_clicks,
            "click_rate": click_rate,
            "performance_score": click_rate * 100  # 简单的性能评分
        }
    
    def export_data(self, data_type: str = "all") -> Dict[str, Any]:
        """导出数据"""
        export_data = {}
        
        if data_type in ["all", "overview"]:
            export_data["overview"] = self.get_dashboard_overview()
        
        if data_type in ["all", "trends"]:
            export_data["trends"] = {
                "24h": self.get_trend_analysis("24h"),
                "7d": self.get_trend_analysis("7d"),
                "30d": self.get_trend_analysis("30d")
            }
        
        if data_type in ["all", "services"]:
            export_data["services"] = self.get_service_comparison()
        
        if data_type in ["all", "users"]:
            export_data["users"] = self.get_user_insights()
        
        if data_type in ["all", "recommendations"]:
            export_data["recommendations"] = self.get_recommendation_performance()
        
        return export_data
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        overview = self.get_dashboard_overview()
        service_comparison = self.get_service_comparison()
        
        # 计算健康分数
        health_score = 100  # 基础分数
        
        # 基于分析成功率调整分数
        if overview["total_analyses"] > 0:
            success_rate = sum(1 for r in self.analysis_history if r["ai_confidence"] > 0.5) / overview["total_analyses"]
            health_score *= success_rate
        
        # 基于服务可用性调整分数
        if service_comparison:
            avg_success_rate = sum(s["success_rate"] for s in service_comparison.values()) / len(service_comparison)
            health_score *= avg_success_rate
        
        # 基于处理时间调整分数
        if overview["average_processing_time"] > 10:  # 如果平均处理时间超过10秒
            health_score *= 0.8
        
        return {
            "health_score": min(100, max(0, health_score)),
            "status": "healthy" if health_score >= 80 else "degraded" if health_score >= 60 else "unhealthy",
            "last_analysis_time": self.analysis_history[-1]["timestamp"] if self.analysis_history else 0,
            "active_services": len(service_comparison),
            "recommendations": {
                "improve_accuracy": "考虑启用更多AI服务以提高分析准确性",
                "optimize_performance": "检查服务配置以优化处理时间",
                "monitor_health": "定期检查系统健康状态"
            }
        }


# 全局仪表板实例
ai_dashboard = AIDashboard()