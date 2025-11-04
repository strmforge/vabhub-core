#!/usr/bin/env python3
"""验证更多修复的文件是否能正确导入和使用"""

print("开始验证更多修复...")

# 测试music_platform_adapter.py
print("\n1. 测试music_platform_adapter.py...")
try:
    from core.music_platform_adapter import (
        MusicPlatformAdapter,
        MusicPlatformFactory,
        SpotifyAdapter,
        QQMusicAdapter,
        NeteaseMusicAdapter
    )
    print("✅ music_platform_adapter.py模块导入成功")
    print(f"✅ 抽象类MusicPlatformAdapter: {hasattr(MusicPlatformAdapter, '__abstractmethods__')}")
    print(f"✅ 抽象方法: {MusicPlatformAdapter.__abstractmethods__}")
    print(f"✅ 工厂类: {hasattr(MusicPlatformFactory, 'create_adapter')}")
    print(f"✅ Spotify适配器: {issubclass(SpotifyAdapter, MusicPlatformAdapter)}")
    print(f"✅ QQ音乐适配器: {issubclass(QQMusicAdapter, MusicPlatformAdapter)}")
    print(f"✅ 网易云适配器: {issubclass(NeteaseMusicAdapter, MusicPlatformAdapter)}")
except Exception as e:
    print(f"❌ music_platform_adapter.py导入失败: {e}")

# 测试graphql_api.py
print("\n2. 测试graphql_api.py...")
try:
    from core.graphql_api import (
        SubscriptionManager,
        WebSocketManager,
        create_graphql_app
    )
    print("✅ graphql_api.py模块导入成功")
    print(f"✅ SubscriptionManager类: {hasattr(SubscriptionManager, 'register_subscription')}")
    print(f"✅ WebSocketManager类: {hasattr(WebSocketManager, 'connect')}")
    print(f"✅ create_graphql_app函数: {callable(create_graphql_app)}")
except Exception as e:
    print(f"❌ graphql_api.py导入失败: {e}")

# 测试charts.py
print("\n3. 测试charts.py...")
try:
    from core import charts
    print("✅ charts.py模块导入成功")
except Exception as e:
    print(f"❌ charts.py导入失败: {e}")

print("\n验证完成！")
