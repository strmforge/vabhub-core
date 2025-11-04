"""
性能监控器测试

测试性能监控器的核心功能，包括指标收集、统计分析和性能优化建议
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock

from core.performance_monitor import PerformanceMonitor, MetricType, PerformanceMetric


class TestPerformanceMonitor:
    """测试性能监控器"""

    @pytest.fixture
    def monitor(self):
        """创建性能监控器实例"""
        return PerformanceMonitor(history_size=100)

    @pytest.mark.asyncio
    async def test_init(self, monitor):
        """测试初始化"""
        assert monitor.history_size == 100
        assert len(monitor.stats) == len(MetricType)
        assert monitor.logger is not None

    @pytest.mark.asyncio
    async def test_record_metric(self, monitor):
        """测试记录指标"""
        # 记录CPU使用率指标
        await monitor.record_metric(MetricType.CPU_USAGE, 75.5)

        # 验证指标被记录
        history = await monitor.get_metrics_history(MetricType.CPU_USAGE)
        assert len(history) == 1

        metric = history[0]
        assert metric.metric_type == MetricType.CPU_USAGE
        assert metric.value == 75.5
        assert metric.timestamp > 0

    @pytest.mark.asyncio
    async def test_record_metric_with_tags(self, monitor):
        """测试记录带标签的指标"""
        tags = {"host": "server1", "region": "us-east"}
        await monitor.record_metric(MetricType.MEMORY_USAGE, 60.0, tags)

        history = await monitor.get_metrics_history(MetricType.MEMORY_USAGE)
        assert len(history) == 1
        assert history[0].tags == tags

    @pytest.mark.asyncio
    async def test_get_stats(self, monitor):
        """测试获取统计信息"""
        # 记录多个指标值
        values = [50.0, 60.0, 70.0, 80.0, 90.0]
        for value in values:
            await monitor.record_metric(MetricType.CPU_USAGE, value)

        # 获取统计信息
        stats = await monitor.get_stats(MetricType.CPU_USAGE)

        assert stats.metric_type == MetricType.CPU_USAGE
        assert stats.count == 5
        assert stats.min_value == 50.0
        assert stats.max_value == 90.0
        assert stats.avg_value == 70.0
        assert stats.last_value == 90.0

    @pytest.mark.asyncio
    async def test_get_all_stats(self, monitor):
        """测试获取所有统计信息"""
        # 记录不同指标的数值
        await monitor.record_metric(MetricType.CPU_USAGE, 75.0)
        await monitor.record_metric(MetricType.MEMORY_USAGE, 60.0)

        all_stats = await monitor.get_all_stats()

        assert len(all_stats) == len(MetricType)
        assert MetricType.CPU_USAGE in all_stats
        assert MetricType.MEMORY_USAGE in all_stats

        cpu_stats = all_stats[MetricType.CPU_USAGE]
        assert cpu_stats.count == 1
        assert cpu_stats.avg_value == 75.0

    @pytest.mark.asyncio
    async def test_get_metrics_history_with_limit(self, monitor):
        """测试带限制的获取指标历史"""
        # 记录多个指标
        for i in range(50):
            await monitor.record_metric(MetricType.DISK_IO, i)

        # 获取最近10个指标
        history = await monitor.get_metrics_history(MetricType.DISK_IO, limit=10)

        assert len(history) == 10
        # 应该返回最新的指标（值最大的）
        assert history[0].value == 49
        assert history[-1].value == 40

    @pytest.mark.asyncio
    async def test_analyze_performance(self, monitor):
        """测试性能分析"""
        # 记录各种指标
        await monitor.record_metric(MetricType.CPU_USAGE, 85.0)  # 高使用率
        await monitor.record_metric(MetricType.MEMORY_USAGE, 70.0)  # 中等使用率
        await monitor.record_metric(MetricType.CACHE_HIT_RATE, 65.0)  # 低命中率
        await monitor.record_metric(MetricType.RESPONSE_TIME, 1200.0)  # 长响应时间

        analysis = await monitor.analyze_performance()

        assert "recommendations" in analysis
        assert "warnings" in analysis
        assert "metrics_summary" in analysis

        # 验证警告和建议
        warnings = analysis["warnings"]
        recommendations = analysis["recommendations"]

        # 应该有关于高CPU使用率和长响应时间的警告
        assert any("CPU使用率过高" in warning for warning in warnings)
        assert any("API响应时间过长" in warning for warning in warnings)

        # 应该有关于内存使用率和缓存命中率的建议
        assert any("内存使用率较高" in rec for rec in recommendations)
        assert any("缓存命中率较低" in rec for rec in recommendations)

    @pytest.mark.asyncio
    async def test_record_system_metrics(self, monitor):
        """测试记录系统指标"""
        with patch("psutil.cpu_percent", return_value=75.0):
            with patch("psutil.virtual_memory") as mock_memory:
                mock_memory.return_value.percent = 60.0

                await monitor.record_system_metrics()

        # 验证系统指标被记录
        cpu_history = await monitor.get_metrics_history(MetricType.CPU_USAGE)
        memory_history = await monitor.get_metrics_history(MetricType.MEMORY_USAGE)

        assert len(cpu_history) == 1
        assert len(memory_history) == 1

        assert cpu_history[0].value == 75.0
        assert memory_history[0].value == 60.0

    @pytest.mark.asyncio
    async def test_record_api_metrics(self, monitor):
        """测试记录API指标"""
        await monitor.record_api_metrics(200, 150.0)  # 成功请求
        await monitor.record_api_metrics(500, 200.0)  # 错误请求

        # 验证API指标被记录
        response_history = await monitor.get_metrics_history(MetricType.RESPONSE_TIME)
        request_history = await monitor.get_metrics_history(MetricType.REQUEST_COUNT)
        error_history = await monitor.get_metrics_history(MetricType.ERROR_RATE)

        assert len(response_history) == 2
        assert len(request_history) == 2
        assert len(error_history) == 2

    @pytest.mark.asyncio
    async def test_record_cache_metrics(self, monitor):
        """测试记录缓存指标"""
        await monitor.record_cache_metrics(80, 20)  # 80次命中，20次未命中

        cache_history = await monitor.get_metrics_history(MetricType.CACHE_HIT_RATE)
        assert len(cache_history) == 1
        assert cache_history[0].value == 80.0  # 80%命中率

    @pytest.mark.asyncio
    async def test_start_monitoring(self, monitor):
        """测试开始监控"""
        # 使用较短的间隔进行测试
        monitor_task = asyncio.create_task(monitor.start_monitoring(interval=0.1))

        # 等待一小段时间让监控任务运行几次
        await asyncio.sleep(0.3)

        # 取消监控任务
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # 验证系统指标被记录
        cpu_history = await monitor.get_metrics_history(MetricType.CPU_USAGE)
        memory_history = await monitor.get_metrics_history(MetricType.MEMORY_USAGE)

        # 应该至少记录了一些指标
        assert len(cpu_history) > 0
        assert len(memory_history) > 0

    @pytest.mark.asyncio
    async def test_history_size_limit(self, monitor):
        """测试历史记录大小限制"""
        # 记录超过历史大小的指标
        for i in range(150):  # 超过100的限制
            await monitor.record_metric(MetricType.CPU_USAGE, i)

        history = await monitor.get_metrics_history(MetricType.CPU_USAGE)

        # 历史记录应该不超过设置的大小
        assert len(history) <= 100
        # 应该保留最新的指标
        assert history[0].value == 149
        assert history[-1].value == 50

    @pytest.mark.asyncio
    async def test_performance_metric_dataclass(self):
        """测试性能指标数据类"""
        timestamp = time.time()
        metric = PerformanceMetric(
            timestamp=timestamp,
            metric_type=MetricType.CPU_USAGE,
            value=75.0,
            tags={"host": "test"},
        )

        assert metric.timestamp == timestamp
        assert metric.metric_type == MetricType.CPU_USAGE
        assert metric.value == 75.0
        assert metric.tags == {"host": "test"}

    @pytest.mark.asyncio
    async def test_performance_stats_update(self):
        """测试性能统计更新"""
        stats = PerformanceStats(MetricType.CPU_USAGE)

        # 初始状态
        assert stats.count == 0
        assert stats.min_value == float("inf")
        assert stats.max_value == float("-inf")
        assert stats.sum_value == 0.0
        assert stats.avg_value == 0.0

        # 更新统计
        stats.update(50.0)
        assert stats.count == 1
        assert stats.min_value == 50.0
        assert stats.max_value == 50.0
        assert stats.sum_value == 50.0
        assert stats.avg_value == 50.0
        assert stats.last_value == 50.0

        # 再次更新
        stats.update(70.0)
        assert stats.count == 2
        assert stats.min_value == 50.0
        assert stats.max_value == 70.0
        assert stats.sum_value == 120.0
        assert stats.avg_value == 60.0
        assert stats.last_value == 70.0

    @pytest.mark.asyncio
    async def test_edge_cases(self, monitor):
        """测试边界情况"""
        # 测试无效指标类型
        with pytest.raises(ValueError):
            await monitor.record_metric("invalid_type", 50.0)

        # 测试获取不存在的指标历史
        history = await monitor.get_metrics_history(MetricType.NETWORK_IO)
        assert len(history) == 0

        # 测试获取不存在的统计信息
        stats = await monitor.get_stats(MetricType.NETWORK_IO)
        assert stats.count == 0
        assert stats.avg_value == 0.0

    @pytest.mark.asyncio
    async def test_concurrent_metric_recording(self, monitor):
        """测试并发指标记录"""

        async def record_metrics():
            for i in range(10):
                await monitor.record_metric(MetricType.CPU_USAGE, i)
                await asyncio.sleep(0.01)

        # 创建多个并发任务
        tasks = [record_metrics() for _ in range(5)]
        await asyncio.gather(*tasks)

        # 验证所有指标都被正确记录
        history = await monitor.get_metrics_history(MetricType.CPU_USAGE)
        assert len(history) == 50  # 5个任务 * 10个指标

        # 验证统计信息正确
        stats = await monitor.get_stats(MetricType.CPU_USAGE)
        assert stats.count == 50

    @pytest.mark.asyncio
    async def test_performance_under_load(self, monitor):
        """测试高负载下的性能"""
        import time

        start_time = time.time()

        # 快速记录大量指标
        tasks = []
        for i in range(1000):
            task = monitor.record_metric(MetricType.CPU_USAGE, i % 100)
            tasks.append(task)

        await asyncio.gather(*tasks)

        end_time = time.time()
        processing_time = end_time - start_time

        # 验证处理时间在合理范围内
        assert processing_time < 5.0  # 1000个指标应该在5秒内完成

        # 验证所有指标都被记录
        history = await monitor.get_metrics_history(MetricType.CPU_USAGE)
        assert len(history) == 100  # 受历史大小限制

        print(f"高负载处理时间: {processing_time:.2f}秒")
