#!/usr/bin/env python3
"""
PyTorch兼容性补丁
解决transformers库与PyTorch 2.1.1的兼容性问题
"""

import torch

# 检查PyTorch版本
print(f"PyTorch版本: {torch.__version__}")

# 如果PyTorch版本低于2.2.0，需要应用兼容性补丁
if torch.__version__.startswith("2.1"):
    # 检查_pytree模块是否存在所需的方法
    if hasattr(torch.utils._pytree, '_register_pytree_node') and not hasattr(torch.utils._pytree, 'register_pytree_node'):
        # 创建兼容性别名
        torch.utils._pytree.register_pytree_node = torch.utils._pytree._register_pytree_node
        print("已应用PyTorch兼容性补丁: _register_pytree_node -> register_pytree_node")
    
    # 检查其他可能需要的兼容性补丁
    if hasattr(torch.utils._pytree, '_register_pytree_node'):
        print("PyTorch _pytree模块已包含_register_pytree_node方法")
    else:
        print("警告: PyTorch _pytree模块缺少_register_pytree_node方法")

print("PyTorch兼容性检查完成")