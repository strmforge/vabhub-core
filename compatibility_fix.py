#!/usr/bin/env python3
"""
PyTorch和Transformers兼容性修复补丁
解决PyTorch 2.1.1与transformers库的兼容性问题
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

def fix_pytorch_compatibility():
    """修复PyTorch兼容性问题"""
    try:
        import torch
        import torch.utils._pytree as pytree
        
        # 检查是否缺少register_pytree_node方法
        if not hasattr(pytree, 'register_pytree_node'):
            print("检测到PyTorch缺少register_pytree_node方法，正在创建兼容性补丁...")
            
            # 创建一个兼容性包装器
            def register_pytree_node_wrapper(cls, flatten_func, unflatten_func, serialized_type_name=None):
                """兼容性包装器函数"""
                if hasattr(pytree, '_register_pytree_node'):
                    # 使用新的API
                    if serialized_type_name:
                        pytree._register_pytree_node(cls, flatten_func, unflatten_func, serialized_type_name)
                    else:
                        pytree._register_pytree_node(cls, flatten_func, unflatten_func)
                else:
                    # 回退到旧API
                    pytree._register_pytree_node(cls, flatten_func, unflatten_func)
            
            # 将包装器添加到pytree模块
            pytree.register_pytree_node = register_pytree_node_wrapper
            print("✓ PyTorch兼容性补丁已应用")
        else:
            print("✓ PyTorch兼容性正常")
            
    except Exception as e:
        print(f"✗ 应用PyTorch兼容性补丁时出错: {e}")

def fix_transformers_imports():
    """修复transformers库的导入问题"""
    try:
        # 在导入transformers之前应用补丁
        fix_pytorch_compatibility()
        
        # 现在尝试导入transformers
        import transformers
        print(f"✓ Transformers版本: {transformers.__version__}")
        
        # 检查PyTorch是否可用
        if transformers.is_torch_available():
            print("✓ PyTorch在transformers中可用")
        else:
            print("⚠ PyTorch在transformers中不可用")
            
    except Exception as e:
        print(f"✗ 导入transformers时出错: {e}")
        
        # 尝试降级transformers到兼容版本
        print("正在尝试安装兼容的transformers版本...")
        try:
            import subprocess
            # 安装与PyTorch 2.0.1兼容的transformers版本
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "transformers==4.35.2", "--force-reinstall"
            ])
            print("✓ 已安装transformers 4.35.2")
        except Exception as install_error:
            print(f"✗ 安装兼容版本失败: {install_error}")

if __name__ == "__main__":
    print("正在应用PyTorch和Transformers兼容性修复...")
    fix_transformers_imports()
    print("兼容性修复完成")