#!/usr/bin/env python3
"""验证我们修复的文件是否能正确导入和使用"""

print("开始验证修复...")

# 测试导入
print("\n1. 测试导入fastapi和pydantic...")
try:
    import fastapi
    import pydantic
    print("✅ fastapi和pydantic导入成功")
except ImportError as e:
    print(f"❌ 导入错误: {e}")

# 测试api_subscription.py
print("\n2. 测试api_subscription.py...")
try:
    from core.api_subscription import router as subscription_router
    print(f"✅ api_subscription.py导入成功，路由前缀: {subscription_router.prefix}")
except Exception as e:
    print(f"❌ api_subscription.py导入失败: {e}")

# 测试api_performance.py
print("\n3. 测试api_performance.py...")
try:
    from core.api_performance import router as performance_router
    print(f"✅ api_performance.py导入成功，路由前缀: {performance_router.prefix}")
except Exception as e:
    print(f"❌ api_performance.py导入失败: {e}")

# 测试music_subscription.py
print("\n4. 测试music_subscription.py...")
try:
    from core.music_subscription import MusicSubscriptionManager
    print("✅ MusicSubscriptionManager类导入成功")
    # 测试类的基本初始化（如果可能）
    # 由于我们没有配置，可能无法完全初始化，但至少可以检查类结构
    print(f"✅ 类方法: {[method for method in dir(MusicSubscriptionManager) if not method.startswith('_')]}")
except Exception as e:
    print(f"❌ music_subscription.py导入失败: {e}")

# 测试api.py
print("\n5. 测试api.py...")
try:
    import core.api
    print("✅ api.py模块导入成功")
except Exception as e:
    print(f"❌ api.py导入失败: {e}")

print("\n验证完成！")
