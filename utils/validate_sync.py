#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 多仓库同步验证脚本
验证所有新功能是否已正确同步到各个仓库
"""

import os
import sys
from pathlib import Path
import importlib.util
import ast

def check_file_exists(file_path):
    """检查文件是否存在"""
    return os.path.exists(file_path)

def check_python_imports(file_path, required_imports):
    """检查Python文件中的导入语句"""
    if not check_file_exists(file_path):
        return False, f"文件不存在: {file_path}"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查类定义和函数定义
        missing_imports = []
        for imp in required_imports:
            if imp in content:
                # 检查是否是类定义或函数定义
                if f"class {imp}" in content or f"def {imp}" in content:
                    continue
                else:
                    missing_imports.append(imp)
            else:
                missing_imports.append(imp)
        
        if missing_imports:
            return False, f"缺少导入: {', '.join(missing_imports)}"
        else:
            return True, "导入检查通过"
    except Exception as e:
        return False, f"解析错误: {str(e)}"

def check_requirements_deps(requirements_path, required_deps):
    """检查requirements.txt中的依赖"""
    if not check_file_exists(requirements_path):
        return False, f"依赖文件不存在: {requirements_path}"
    
    try:
        with open(requirements_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        missing_deps = []
        for dep in required_deps:
            if dep not in content:
                missing_deps.append(dep)
        
        if missing_deps:
            return False, f"缺少依赖: {', '.join(missing_deps)}"
        else:
            return True, "依赖检查通过"
    except Exception as e:
        return False, f"读取错误: {str(e)}"

def validate_core_repo():
    """验证VabHub-Core仓库"""
    print("🔍 验证 VabHub-Core 仓库...")
    
    checks = []
    
    # 检查核心模块文件
    core_files = [
        "VabHub-Core/core/event.py",
        "VabHub-Core/core/scheduler.py", 
        "VabHub-Core/core/chain.py",
        "VabHub-Core/core/plugin.py"
    ]
    
    for file_path in core_files:
        exists = check_file_exists(file_path)
        checks.append((file_path, exists, "文件存在" if exists else "文件不存在"))
    
    # 检查依赖
    deps_check = check_requirements_deps(
        "VabHub-Core/requirements.txt",
        ["APScheduler==3.10.4", "pydantic-settings==2.1.0"]
    )
    checks.append(("VabHub-Core/requirements.txt", deps_check[0], deps_check[1]))
    
    # 检查事件系统导入
    event_imports = check_python_imports(
        "VabHub-Core/core/event.py",
        ["EventType", "EventManager", "event_handler"]
    )
    checks.append(("VabHub-Core/core/event.py 导入", event_imports[0], event_imports[1]))
    
    return checks

def validate_frontend_repo():
    """验证VabHub-Frontend仓库"""
    print("🔍 验证 VabHub-Frontend 仓库...")
    
    checks = []
    
    # 检查API接口文件
    api_files = [
        "VabHub-Frontend/src/api/index.js"
    ]
    
    for file_path in api_files:
        exists = check_file_exists(file_path)
        checks.append((file_path, exists, "文件存在" if exists else "文件不存在"))
    
    # 检查API接口内容
    if check_file_exists("VabHub-Frontend/src/api/index.js"):
        with open("VabHub-Frontend/src/api/index.js", 'r', encoding='utf-8') as f:
            content = f.read()
        
        api_endpoints = ["eventAPI", "schedulerAPI", "chainAPI"]
        missing_apis = []
        for api in api_endpoints:
            if f"export const {api}" not in content:
                missing_apis.append(api)
        
        if missing_apis:
            checks.append(("前端API接口", False, f"缺少API: {', '.join(missing_apis)}"))
        else:
            checks.append(("前端API接口", True, "API接口完整"))
    
    return checks

def validate_plugins_repo():
    """验证VabHub-Plugins仓库"""
    print("🔍 验证 VabHub-Plugins 仓库...")
    
    checks = []
    
    # 检查插件基础文件
    plugin_files = [
        "VabHub-Plugins/plugins/base.py"
    ]
    
    for file_path in plugin_files:
        exists = check_file_exists(file_path)
        checks.append((file_path, exists, "文件存在" if exists else "文件不存在"))
    
    # 检查插件基础类
    if check_file_exists("VabHub-Plugins/plugins/base.py"):
        with open("VabHub-Plugins/plugins/base.py", 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "class PluginBase(BasePlugin)" in content:
            checks.append(("插件基础类", True, "插件基础类继承正确"))
        else:
            checks.append(("插件基础类", False, "插件基础类继承错误"))
    
    return checks

def validate_deploy_repo():
    """验证VabHub-Deploy仓库"""
    print("🔍 验证 VabHub-Deploy 仓库...")
    
    checks = []
    
    # 检查部署依赖
    deps_check = check_requirements_deps(
        "VabHub-Deploy/deploy_requirements.txt",
        ["APScheduler==3.10.4"]
    )
    checks.append(("VabHub-Deploy/requirements.txt", deps_check[0], deps_check[1]))
    
    return checks

def main():
    """主验证函数"""
    print("🚀 VabHub 多仓库同步验证开始")
    print("=" * 60)
    
    all_checks = []
    
    # 验证各个仓库
    all_checks.extend(validate_core_repo())
    all_checks.extend(validate_frontend_repo()) 
    all_checks.extend(validate_plugins_repo())
    all_checks.extend(validate_deploy_repo())
    
    print("\n📊 验证结果汇总:")
    print("-" * 60)
    
    passed = 0
    failed = 0
    
    for check_name, status, message in all_checks:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {check_name}: {message}")
        if status:
            passed += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"📈 总体统计: 通过 {passed} 项, 失败 {failed} 项")
    
    if failed == 0:
        print("🎉 所有仓库同步验证通过！")
        return 0
    else:
        print("⚠️  存在同步问题，请检查失败的项")
        return 1

if __name__ == "__main__":
    sys.exit(main())