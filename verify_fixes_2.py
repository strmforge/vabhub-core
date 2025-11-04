#!/usr/bin/env python3
"""验证第二批修复的文件是否能正确导入"""

print("开始验证第二批修复...")

# 测试api_notification.py
print("\n1. 测试api_notification.py...")
try:
    from core.api_notification import router as notification_router
    print("✅ api_notification.py导入成功")
    print(f"✅ 路由前缀: {notification_router.prefix}")
except Exception as e:
    print(f"❌ api_notification.py导入失败: {e}")

# 测试subscription_manager.py
print("\n2. 测试subscription_manager.py...")
try:
    from core.subscription_manager import SubscriptionManager, SubscriptionRule, SubscriptionStatus
    print("✅ subscription_manager.py导入成功")
    print(f"✅ SubscriptionManager类: {hasattr(SubscriptionManager, 'create_subscription')}")
    print(f"✅ SubscriptionRule类: {hasattr(SubscriptionRule, 'keywords')}")
    print(f"✅ SubscriptionStatus枚举: {SubscriptionStatus.ACTIVE}")
except Exception as e:
    print(f"❌ subscription_manager.py导入失败: {e}")

# 测试cache_manager.py
print("\n3. 测试cache_manager.py...")
try:
    from core.cache_manager import CacheManager, CacheLevel
    print("✅ cache_manager.py导入成功")
    print(f"✅ CacheManager类: {hasattr(CacheManager, 'get')}")
    print(f"✅ CacheLevel枚举: {CacheLevel.MEMORY}")
except Exception as e:
    print(f"❌ cache_manager.py导入失败: {e}")

# 测试cache.py
print("\n4. 测试cache.py...")
try:
    from core.cache import RedisCacheManager, get_cache_manager, init_cache_manager
    print("✅ cache.py导入成功")
    print(f"✅ RedisCacheManager类: {hasattr(RedisCacheManager, 'get')}")
    print(f"✅ get_cache_manager函数: {callable(get_cache_manager)}")
except Exception as e:
    print(f"❌ cache.py导入失败: {e}")

# 测试music_platform_adapter.py
print("\n5. 测试music_platform_adapter.py...")
try:
    from core.music_platform_adapter import MusicPlatformAdapter, Throttler
    print("✅ music_platform_adapter.py导入成功")
    print(f"✅ Throttler类: {hasattr(Throttler, 'acquire')}")
except Exception as e:
    print(f"❌ music_platform_adapter.py导入失败: {e}")

print("\n验证完成！")
