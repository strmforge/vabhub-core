#!/usr/bin/env python3
"""
PyTorch兼容性补丁 - 修复_register_pytree_node错误
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def apply_pytorch_patch():
    """应用PyTorch兼容性补丁"""
    try:
        # 导入torch
        import torch
        print(f"PyTorch版本: {torch.__version__}")
        
        # 检查是否有pytree模块
        if hasattr(torch.utils, '_pytree'):
            print("检测到PyTorch pytree模块")
            
            # 检查_register_pytree_node方法
            if hasattr(torch.utils._pytree, '_register_pytree_node'):
                print("检测到_register_pytree_node方法")
                
                # 保存原始方法
                original_method = torch.utils._pytree._register_pytree_node
                
                # 创建兼容性包装器
                def patched_register_pytree_node(cls, flatten_fn, unflatten_fn, serialized_type_name=None):
                    """兼容性包装器，忽略serialized_type_name参数"""
                    if serialized_type_name is not None:
                        print(f"警告: 忽略serialized_type_name参数: {serialized_type_name}")
                    
                    # 调用原始方法，但不传递serialized_type_name
                    return original_method(cls, flatten_fn, unflatten_fn)
                
                # 应用补丁
                torch.utils._pytree._register_pytree_node = patched_register_pytree_node
                print("PyTorch兼容性补丁已应用")
                return True
            else:
                print("未找到_register_pytree_node方法")
                return False
        else:
            print("未找到PyTorch pytree模块")
            return False
            
    except Exception as e:
        print(f"应用PyTorch补丁时出错: {e}")
        return False

def test_transformers_import():
    """测试transformers导入"""
    try:
        import transformers
        print(f"Transformers版本: {transformers.__version__}")
        return True
    except Exception as e:
        print(f"Transformers导入错误: {e}")
        return False

def main():
    """主函数"""
    print("开始应用PyTorch兼容性补丁...")
    
    # 应用补丁
    patch_applied = apply_pytorch_patch()
    
    if patch_applied:
        print("✅ PyTorch兼容性补丁应用成功")
        
        # 测试transformers导入
        print("测试Transformers导入...")
        transformers_ok = test_transformers_import()
        
        if transformers_ok:
            print("✅ Transformers导入成功")
            return True
        else:
            print("❌ Transformers导入失败")
            return False
    else:
        print("❌ PyTorch兼容性补丁应用失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)