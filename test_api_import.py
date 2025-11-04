#!/usr/bin/env python3
"""测试api.py的导入"""

try:
    print("尝试导入core.api...")
    import core.api
    print("✅ api.py导入成功")
except Exception as e:
    import traceback
    print(f"❌ api.py导入失败: {e}")
    print("错误详情:")
    traceback.print_exc()
