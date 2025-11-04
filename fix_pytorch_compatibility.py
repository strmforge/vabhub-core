#!/usr/bin/env python3
"""
临时修复PyTorch和transformers兼容性问题的脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_pytorch_import():
    """修复PyTorch导入问题"""
    try:
        # 尝试导入torch并检查版本
        import torch
        print(f"PyTorch版本: {torch.__version__}")
        
        # 检查是否有pytree问题
        if hasattr(torch.utils, '_pytree'):
            print("PyTorch pytree模块存在")
            
            # 如果register_pytree_node不存在，创建一个兼容性补丁
            if not hasattr(torch.utils._pytree, 'register_pytree_node'):
                print("检测到register_pytree_node缺失，应用兼容性补丁...")
                
                # 创建一个简单的兼容性包装器
                def register_pytree_node(*args, **kwargs):
                    print("register_pytree_node被调用，但已跳过（兼容性处理）")
                    return None
                
                # 将补丁函数添加到pytree模块
                torch.utils._pytree.register_pytree_node = register_pytree_node
                print("兼容性补丁已应用")
        
        return True
    except Exception as e:
        print(f"PyTorch导入错误: {e}")
        return False

def fix_transformers_import():
    """修复transformers导入问题"""
    try:
        # 尝试导入transformers
        import transformers
        print(f"Transformers版本: {transformers.__version__}")
        
        # 检查transformers是否能正常工作
        from transformers import __version__ as tf_version
        print(f"Transformers导入成功，版本: {tf_version}")
        
        return True
    except Exception as e:
        print(f"Transformers导入错误: {e}")
        
        # 如果是pytree相关错误，尝试应用补丁
        if "register_pytree_node" in str(e):
            print("检测到pytree相关错误，尝试应用兼容性补丁...")
            
            # 尝试修复PyTorch导入
            if fix_pytorch_import():
                # 重新尝试导入transformers
                try:
                    import transformers
                    print("Transformers导入修复成功")
                    return True
                except Exception as e2:
                    print(f"Transformers导入修复失败: {e2}")
        
        return False

def main():
    """主函数"""
    print("开始修复PyTorch和Transformers兼容性问题...")
    
    # 修复PyTorch导入
    pytorch_fixed = fix_pytorch_import()
    
    # 修复transformers导入
    transformers_fixed = fix_transformers_import()
    
    if pytorch_fixed and transformers_fixed:
        print("✅ 兼容性问题修复成功！")
        return True
    else:
        print("❌ 兼容性问题修复失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)