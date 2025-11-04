"""
路径管理器测试

测试路径管理器的核心功能，包括文件操作、重命名、路径管理等
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from core.path_manager import PathManager


class TestPathManager:
    """测试路径管理器"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def path_manager(self, temp_dir):
        """创建路径管理器实例"""
        return PathManager(base_path=temp_dir)

    def test_init_with_base_path(self, temp_dir):
        """测试使用基础路径初始化"""
        pm = PathManager(base_path=temp_dir)
        assert pm.base_path == Path(temp_dir)

    def test_init_without_base_path(self):
        """测试无基础路径初始化"""
        pm = PathManager()
        assert pm.base_path is None

    def test_sanitize_filename(self, path_manager):
        """测试文件名清理"""
        # 测试特殊字符清理
        dirty_name = "file/with\invalid:characters*?\"<>|"
        clean_name = path_manager.sanitize_filename(dirty_name)
        assert "/" not in clean_name
        assert "\\" not in clean_name
        assert ":" not in clean_name
        assert "*" not in clean_name
        assert "?" not in clean_name
        assert '"' not in clean_name
        assert "<" not in clean_name
        assert ">" not in clean_name
        assert "|" not in clean_name

        # 测试空格处理
        name_with_spaces = "  file with spaces  "
        clean_name = path_manager.sanitize_filename(name_with_spaces)
        assert clean_name == "file with spaces"

        # 测试过长文件名
        long_name = "a" * 300
        clean_name = path_manager.sanitize_filename(long_name)
        assert len(clean_name) <= 255

    def test_get_unique_filename(self, path_manager, temp_dir):
        """测试获取唯一文件名"""
        # 创建测试文件
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")

        # 获取唯一文件名
        unique_name = path_manager.get_unique_filename(str(test_file))
        assert unique_name != str(test_file)
        assert "test" in unique_name
        assert ".txt" in unique_name

    def test_create_symlink(self, path_manager, temp_dir):
        """测试创建符号链接"""
        # 创建源文件
        source_file = Path(temp_dir) / "source.txt"
        source_file.write_text("source content")

        # 创建目标路径
        target_file = Path(temp_dir) / "target.txt"

        # 创建符号链接
        result = path_manager.create_symlink(str(source_file), str(target_file))
        assert result is True
        assert target_file.exists()
        assert target_file.is_symlink()

        # 测试链接到已存在文件
        result = path_manager.create_symlink(str(source_file), str(target_file))
        assert result is True

    def test_batch_rename_music_files(self, path_manager, temp_dir):
        """测试批量重命名音乐文件"""
        # 创建测试音乐文件
        test_file = Path(temp_dir) / "old_music.mp3"
        test_file.write_text("music content")

        files = [
            {
                "path": str(test_file),
                "type": "music",
                "artist": "Test Artist",
                "album": "Test Album",
                "track": 1,
                "title": "Test Song",
                "extension": "mp3"
            }
        ]

        results = path_manager.batch_rename(files, "{artist} - {album} - {track:02d} - {title}")
        
        assert len(results) == 1
        assert results[0]["success"] is True
        assert "Test Artist - Test Album - 01 - Test Song.mp3" in results[0]["new_path"]

    def test_batch_rename_movie_files(self, path_manager, temp_dir):
        """测试批量重命名电影文件"""
        # 创建测试电影文件
        test_file = Path(temp_dir) / "old_movie.mkv"
        test_file.write_text("movie content")

        files = [
            {
                "path": str(test_file),
                "type": "movie",
                "title": "Test Movie",
                "year": "2023",
                "quality": "1080p",
                "codec": "H264",
                "extension": "mkv"
            }
        ]

        results = path_manager.batch_rename(files, "{title}.{year}.{quality}.{codec}")
        
        assert len(results) == 1
        assert results[0]["success"] is True
        assert "Test Movie.2023.1080p.H264.mkv" in results[0]["new_path"]

    def test_batch_rename_tv_files(self, path_manager, temp_dir):
        """测试批量重命名电视剧文件"""
        # 创建测试电视剧文件
        test_file = Path(temp_dir) / "old_tv.mkv"
        test_file.write_text("tv content")

        files = [
            {
                "path": str(test_file),
                "type": "tv",
                "title": "Test Show",
                "season": 1,
                "episode": 1,
                "quality": "1080p",
                "codec": "H264",
                "extension": "mkv"
            }
        ]

        results = path_manager.batch_rename(files, "{title}.S{season:02d}E{episode:02d}.{quality}.{codec}")
        
        assert len(results) == 1
        assert results[0]["success"] is True
        assert "Test Show.S01E01.1080p.H264.mkv" in results[0]["new_path"]

    def test_find_duplicates(self, path_manager, temp_dir):
        """测试查找重复文件"""
        # 创建相同内容的文件
        file1 = Path(temp_dir) / "file1.txt"
        file2 = Path(temp_dir) / "file2.txt"
        
        file1.write_text("same content")
        file2.write_text("same content")

        # 创建不同内容的文件
        file3 = Path(temp_dir) / "file3.txt"
        file3.write_text("different content")

        duplicates = path_manager.find_duplicates(temp_dir)
        
        # 应该找到一对重复文件
        assert len(duplicates) >= 1
        duplicate_pair = duplicates[0]
        assert "file1.txt" in duplicate_pair[0] or "file2.txt" in duplicate_pair[0]
        assert "file1.txt" in duplicate_pair[1] or "file2.txt" in duplicate_pair[1]

    def test_cleanup_empty_dirs(self, path_manager, temp_dir):
        """测试清理空目录"""
        # 创建空目录
        empty_dir = Path(temp_dir) / "empty_dir"
        empty_dir.mkdir()

        # 创建有文件的目录
        non_empty_dir = Path(temp_dir) / "non_empty_dir"
        non_empty_dir.mkdir()
        (non_empty_dir / "file.txt").write_text("content")

        removed_dirs = path_manager.cleanup_empty_dirs(temp_dir)
        
        # 应该只删除空目录
        assert len(removed_dirs) == 1
        assert "empty_dir" in removed_dirs[0]
        assert not empty_dir.exists()
        assert non_empty_dir.exists()

    def test_organize_media_files(self, path_manager, temp_dir):
        """测试组织媒体文件"""
        # 创建测试媒体文件
        music_file = Path(temp_dir) / "song.mp3"
        movie_file = Path(temp_dir) / "movie.mkv"
        tv_file = Path(temp_dir) / "tvshow.mkv"
        
        music_file.write_text("music")
        movie_file.write_text("movie")
        tv_file.write_text("tv")

        results = path_manager.organize_media_files(temp_dir, temp_dir)
        
        assert results["processed"] == 3
        assert results["success"] == 3
        assert len(results["errors"]) == 0
        assert len(results["moved_files"]) == 3

    def test_error_handling(self, path_manager, temp_dir):
        """测试错误处理"""
        # 测试不存在的文件
        result = path_manager.create_symlink("nonexistent.txt", "target.txt")
        assert result is False

        # 测试无效的重命名
        files = [{"path": "nonexistent.txt", "type": "music"}]
        results = path_manager.batch_rename(files, "{title}")
        assert len(results) == 1
        assert results[0]["success"] is False
        assert "error" in results[0]

    def test_performance_large_batch(self, path_manager, temp_dir):
        """测试大批量文件处理性能"""
        import time

        # 创建大量测试文件
        test_files = []
        for i in range(100):
            file_path = Path(temp_dir) / f"file_{i}.txt"
            file_path.write_text(f"content {i}")
            test_files.append({
                "path": str(file_path),
                "type": "music",
                "artist": f"Artist {i}",
                "album": f"Album {i}",
                "track": i,
                "title": f"Song {i}",
                "extension": "txt"
            })

        start_time = time.time()
        results = path_manager.batch_rename(test_files, "{artist} - {album} - {track:02d} - {title}")
        end_time = time.time()

        # 验证所有文件都处理完成
        assert len(results) == 100
        assert all(r["success"] for r in results)
        
        # 验证处理时间在合理范围内
        processing_time = end_time - start_time
        assert processing_time < 10.0  # 100个文件应该在10秒内完成
        print(f"大批量处理时间: {processing_time:.2f}秒")

    def test_edge_cases(self, path_manager, temp_dir):
        """测试边界情况"""
        # 测试空文件列表
        results = path_manager.batch_rename([], "{title}")
        assert len(results) == 0

        # 测试空目录
        empty_dir = Path(temp_dir) / "empty"
        empty_dir.mkdir()
        
        duplicates = path_manager.find_duplicates(str(empty_dir))
        assert len(duplicates) == 0
        
        removed_dirs = path_manager.cleanup_empty_dirs(str(empty_dir))
        assert len(removed_dirs) == 1

        # 测试特殊字符文件名
        special_file = Path(temp_dir) / "file with spaces and (parentheses).txt"
        special_file.write_text("content")
        
        clean_name = path_manager.sanitize_filename("file with spaces and (parentheses)")
        assert " " in clean_name  # 空格应该保留
        assert "(" in clean_name  # 括号应该保留
        assert ")" in clean_name  # 括号应该保留