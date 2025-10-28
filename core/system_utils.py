"""
系统工具类
提供跨平台的文件系统操作
"""

import os
import shutil
import platform
from pathlib import Path
from typing import Tuple, List


class SystemUtils:
    """系统工具类"""
    
    @staticmethod
    def is_windows() -> bool:
        """判断是否为Windows系统"""
        return platform.system().lower() == "windows"
    
    @staticmethod
    def is_linux() -> bool:
        """判断是否为Linux系统"""
        return platform.system().lower() == "linux"
    
    @staticmethod
    def is_macos() -> bool:
        """判断是否为macOS系统"""
        return platform.system().lower() == "darwin"
    
    @staticmethod
    def get_windows_drives() -> List[str]:
        """获取Windows驱动器列表"""
        if not SystemUtils.is_windows():
            return []
        
        drives = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive_path = f"{letter}:\\"
            if os.path.exists(drive_path):
                drives.append(drive_path)
        
        return drives
    
    @staticmethod
    def copy(src: Path, dest: Path) -> Tuple[int, str]:
        """复制文件"""
        try:
            if src.is_file():
                shutil.copy2(src, dest)
            else:
                shutil.copytree(src, dest)
            return 0, ""
        except Exception as e:
            return 1, str(e)
    
    @staticmethod
    def move(src: Path, dest: Path) -> Tuple[int, str]:
        """移动文件"""
        try:
            # 当前目录改名
            temp = src.replace(src.parent / dest.name)
            # 移动到目标目录
            shutil.move(temp, dest)
            return 0, ""
        except Exception as e:
            return 1, str(e)
    
    @staticmethod
    def link(src: Path, dest: Path) -> Tuple[int, str]:
        """硬链接文件"""
        try:
            # 创建临时文件
            tmp_path = dest.with_suffix(dest.suffix + ".mp")
            if tmp_path.exists():
                tmp_path.unlink()
            
            # 创建硬链接
            os.link(src, tmp_path)
            
            # 硬链接完成，移除临时后缀
            shutil.move(tmp_path, dest)
            return 0, ""
        except Exception as e:
            return 1, str(e)
    
    @staticmethod
    def softlink(src: Path, dest: Path) -> Tuple[int, str]:
        """软链接文件"""
        try:
            # 创建临时文件
            tmp_path = dest.with_suffix(dest.suffix + ".mp")
            if tmp_path.exists():
                tmp_path.unlink()
            
            # 创建软链接
            os.symlink(src, tmp_path)
            
            # 软链接完成，移除临时后缀
            shutil.move(tmp_path, dest)
            return 0, ""
        except Exception as e:
            return 1, str(e)
    
    @staticmethod
    def is_same_disk(src: Path, dest: Path) -> bool:
        """判断是否在同一磁盘"""
        try:
            src_stat = src.stat()
            dest_stat = dest.stat()
            return src_stat.st_dev == dest_stat.st_dev
        except:
            return False
    
    @staticmethod
    def is_network_filesystem(path: Path) -> bool:
        """判断是否为网络文件系统"""
        try:
            # 简单的网络路径检测
            path_str = str(path)
            if path_str.startswith("\\\\") or path_str.startswith("//"):
                return True
            
            # 检查挂载点（Linux/Mac）
            if SystemUtils.is_linux() or SystemUtils.is_macos():
                import subprocess
                result = subprocess.run(["df", str(path)], capture_output=True, text=True)
                if "nfs" in result.stdout.lower() or "smb" in result.stdout.lower():
                    return True
            
            return False
        except:
            return False
    
    @staticmethod
    def get_disk_usage(path: Path) -> Tuple[float, float, float]:
        """获取磁盘使用情况（GB）"""
        try:
            stat = shutil.disk_usage(path)
            total_gb = stat.total / (1024 ** 3)
            used_gb = stat.used / (1024 ** 3)
            free_gb = stat.free / (1024 ** 3)
            return total_gb, used_gb, free_gb
        except Exception as e:
            return 0.0, 0.0, 0.0
    
    @staticmethod
    def list_sub_directory(path: Path) -> List[Path]:
        """列出子目录"""
        try:
            return [p for p in path.iterdir() if p.is_dir()]
        except:
            return []
    
    @staticmethod
    def list_sub_file(path: Path) -> List[Path]:
        """列出子文件"""
        try:
            return [p for p in path.iterdir() if p.is_file()]
        except:
            return []