"""验证GraphQL和相关文件修复的脚本"""

import sys
import importlib.util
from typing import Dict, Any

def check_import(file_path: str, module_name: str) -> Dict[str, Any]:
    """检查文件是否可以成功导入"""
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return {"success": True, "module": module, "error": None}
        return {"success": False, "module": None, "error": "无法创建模块规范"}
    except Exception as e:
        return {"success": False, "module": None, "error": str(e)}

def verify_all_fixes() -> None:
    """验证所有修复的文件"""
    print("开始验证修复的文件...")
    
    # 定义要验证的文件列表
    files_to_verify = [
        {"path": "f:/VabHub_Extracted/VabHub/vabhub-Core/core/graphql_schema.py", "name": "graphql_schema"},
        {"path": "f:/VabHub_Extracted/VabHub/vabhub-Core/core/download_manager.py", "name": "download_manager"},
        {"path": "f:/VabHub_Extracted/VabHub/vabhub-Core/core/api_notification.py", "name": "api_notification"},
        {"path": "f:/VabHub_Extracted/VabHub/vabhub-Core/core/site_bundle_manager.py", "name": "site_bundle_manager"},
        {"path": "f:/VabHub_Extracted/VabHub/vabhub-Core/core/hnr_detector.py", "name": "hnr_detector"},
    ]
    
    success_count = 0
    failure_count = 0
    
    # 验证每个文件
    for file_info in files_to_verify:
        print(f"\n验证 {file_info['name']}...")
        result = check_import(file_info['path'], file_info['name'])
        
        if result["success"]:
            print(f"✓ {file_info['name']} 导入成功")
            success_count += 1
            
            # 进行简单的类和函数检查
            if hasattr(result["module"], "SiteBundleType"):
                print("  - SiteBundleType 类存在")
            if hasattr(result["module"], "HNRDetectionResultType"):
                print("  - HNRDetectionResultType 类存在")
            if hasattr(result["module"], "DownloadManager"):
                print("  - DownloadManager 类存在")
        else:
            print(f"✗ {file_info['name']} 导入失败: {result['error']}")
            failure_count += 1
    
    # 打印总结
    print("\n" + "="*50)
    print(f"验证结果: 成功 {success_count}, 失败 {failure_count}")
    
    if failure_count == 0:
        print("🎉 所有文件验证通过!")
        sys.exit(0)
    else:
        print("❌ 有文件验证失败，请检查修复。")
        sys.exit(1)

if __name__ == "__main__":
    verify_all_fixes()
