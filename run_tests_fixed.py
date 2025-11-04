#!/usr/bin/env python3
"""
修复PyTorch和Transformers兼容性问题后运行测试
"""

import sys
import os
import subprocess

def fix_imports():
    """修复导入问题"""
    # 添加当前目录到Python路径
    sys.path.insert(0, os.path.dirname(__file__))
    
    # 尝试修复PyTorch兼容性问题
    try:
        import torch
        import torch.utils._pytree as pytree
        
        # 如果缺少register_pytree_node方法，创建一个兼容性包装器
        if not hasattr(pytree, 'register_pytree_node'):
            print("应用PyTorch兼容性补丁...")
            
            def register_pytree_node_wrapper(cls, flatten_func, unflatten_func, serialized_type_name=None):
                """兼容性包装器"""
                if hasattr(pytree, '_register_pytree_node'):
                    if serialized_type_name:
                        pytree._register_pytree_node(cls, flatten_func, unflatten_func, serialized_type_name)
                    else:
                        pytree._register_pytree_node(cls, flatten_func, unflatten_func)
                else:
                    pytree._register_pytree_node(cls, flatten_func, unflatten_func)
            
            pytree.register_pytree_node = register_pytree_node_wrapper
            print("✓ PyTorch兼容性补丁已应用")
            
    except Exception as e:
        print(f"PyTorch兼容性修复失败: {e}")

def run_tests():
    """运行测试"""
    print("开始运行测试...")
    
    # 修复导入问题
    fix_imports()
    
    # 直接运行pytest
    try:
        # 使用系统Python运行测试
        python_exe = r"C:\Users\56214\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe"
        
        # 运行单个测试文件来检查问题
        test_files = [
            "tests/test_api.py",
            "tests/test_integration.py", 
            "tests/test_integration_basic.py",
            "tests/test_integration_simple.py"
        ]
        
        for test_file in test_files:
            if os.path.exists(test_file):
                print(f"\n运行测试文件: {test_file}")
                result = subprocess.run([
                    python_exe, "-m", "pytest", test_file, "-v", "--tb=short"
                ], capture_output=True, text=True)
                
                print(f"退出码: {result.returncode}")
                if result.stdout:
                    print("输出:", result.stdout[-1000:])  # 只显示最后1000字符
                if result.stderr:
                    print("错误:", result.stderr[-1000:])
                    
    except Exception as e:
        print(f"运行测试时出错: {e}")

if __name__ == "__main__":
    run_tests()