#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音乐刮削模块
集成MusicBrainz + AcoustID音频指纹识别
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

import musicbrainzngs
import acoustid
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis

logger = logging.getLogger(__name__)


class MusicScraper:
    """音乐刮削器 - 集成MusicBrainz和AcoustID"""
    
    def __init__(self, acoustid_api_key: Optional[str] = None):
        """初始化音乐刮削器"""
        # 配置MusicBrainz
        musicbrainzngs.set_useragent(
            "StrataMedia/2.0.0",
            "2.0.0",
            "you@example.com"
        )
        
        self.acoustid_api_key = acoustid_api_key
        self.cache_enabled = True
        self.cache_file = "music_cache.json"
        self.cache_data = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """加载音乐识别缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载音乐缓存失败: {e}")
        return {}
    
    def _save_cache(self):
        """保存音乐识别缓存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存音乐缓存失败: {e}")
    
    def extract_metadata_from_file(self, file_path: str) -> Dict[str, Any]:
        """从音频文件提取元数据"""
        try:
            audio_file = mutagen.File(file_path)
            if not audio_file:
                return {}
            
            metadata = {}
            
            # 通用元数据提取
            if hasattr(audio_file, 'info'):
                info = audio_file.info
                metadata.update({
                    'duration': int(info.length) if info.length else None,
                    'bitrate': info.bitrate if hasattr(info, 'bitrate') else None,
                    'sample_rate': info.sample_rate if hasattr(info, 'sample_rate') else None,
                    'channels': info.channels if hasattr(info, 'channels') else None
                })
            
            # 特定格式的标签提取
            if isinstance(audio_file, EasyID3):
                # MP3文件
                tags = audio_file
                metadata.update({
                    'title': tags.get('title', [None])[0],
                    'artist': tags.get('artist', [None])[0],
                    'album': tags.get('album', [None])[0],
                    'year': tags.get('date', [None])[0],
                    'genre': tags.get('genre', [None])[0],
                    'track_number': tags.get('tracknumber', [None])[0]
                })
            elif isinstance(audio_file, FLAC):
                # FLAC文件
                tags = audio_file.tags
                if tags:
                    metadata.update({
                        'title': tags.get('title', [None])[0],
                        'artist': tags.get('artist', [None])[0],
                        'album': tags.get('album', [None])[0],
                        'date': tags.get('date', [None])[0],
                        'genre': tags.get('genre', [None])[0],
                        'tracknumber': tags.get('tracknumber', [None])[0]
                    })
            elif isinstance(audio_file, OggVorbis):
                # OGG文件
                tags = audio_file.tags
                metadata.update({
                    'title': tags.get('title', [None])[0],
                    'artist': tags.get('artist', [None])[0],
                    'album': tags.get('album', [None])[0],
                    'date': tags.get('date', [None])[0],
                    'genre': tags.get('genre', [None])[0]
                })
            
            # 清理空值
            metadata = {k: v for k, v in metadata.items() if v is not None}
            
            return metadata
            
        except Exception as e:
            logger.error(f"提取音频文件元数据失败 {file_path}: {e}")
            return {}
    
    def generate_audio_fingerprint(self, file_path: str) -> Optional[str]:
        """生成音频指纹"""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None
            
            # 检查文件大小（避免处理过大的文件）
            file_size = os.path.getsize(file_path)
            if file_size > 500 * 1024 * 1024:  # 500MB限制
                logger.warning(f"文件过大，跳过指纹生成: {file_path} ({file_size} bytes)")
                return None
            
            # 检查文件类型
            allowed_extensions = {'.mp3', '.flac', '.wav', '.ogg', '.m4a', '.aac'}
            file_extension = Path(file_path).suffix.lower()
            if file_extension not in allowed_extensions:
                logger.warning(f"不支持的文件类型: {file_path}")
                return None
            
            # 生成音频指纹
            duration, fingerprint = acoustid.fingerprint_file(file_path)
            
            # 验证指纹质量
            if len(fingerprint) < 100:  # 指纹太短可能质量不佳
                logger.warning(f"音频指纹质量可能不佳: {file_path} (长度: {len(fingerprint)})")
            
            logger.info(f"音频指纹生成成功: {file_path} (时长: {duration}s, 指纹长度: {len(fingerprint)})")
            return fingerprint
            
        except acoustid.FingerprintGenerationError as e:
            logger.error(f"音频指纹生成错误 {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"生成音频指纹失败 {file_path}: {e}")
            return None
    
    def search_musicbrainz(self, query: str, search_type: str = "recording") -> List[Dict[str, Any]]:
        """搜索MusicBrainz数据库"""
        try:
            if search_type == "recording":
                result = musicbrainzngs.search_recordings(query=query, limit=5)
                recordings = result.get('recording-list', [])
                return [self._parse_musicbrainz_recording(rec) for rec in recordings]
            elif search_type == "release":
                result = musicbrainzngs.search_releases(query=query, limit=5)
                releases = result.get('release-list', [])
                return [self._parse_musicbrainz_release(rel) for rel in releases]
            elif search_type == "artist":
                result = musicbrainzngs.search_artists(query=query, limit=5)
                artists = result.get('artist-list', [])
                return [self._parse_musicbrainz_artist(art) for art in artists]
            else:
                return []
        except Exception as e:
            logger.error(f"MusicBrainz搜索失败: {e}")
            return []
    
    def lookup_by_fingerprint(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        """通过音频指纹查找音乐"""
        if not self.acoustid_api_key:
            logger.warning("未配置AcoustID API密钥，无法使用指纹查找")
            return None
        
        try:
            # 检查指纹质量
            if len(fingerprint) < 50:
                logger.warning(f"音频指纹质量不佳，长度: {len(fingerprint)}")
                return None
            
            # 调用AcoustID API
            results = acoustid.lookup(
                self.acoustid_api_key,
                fingerprint,
                meta='recordings releases'
            )
            
            if not results:
                logger.info("AcoustID未找到匹配结果")
                return None
            
            # 按匹配分数排序，选择最佳结果
            sorted_results = sorted(results, key=lambda x: x.get('score', 0), reverse=True)
            best_result = sorted_results[0]
            
            # 检查匹配分数阈值
            score = best_result.get('score', 0)
            if score < 0.7:  # 设置匹配分数阈值
                logger.info(f"匹配分数过低: {score}，跳过此结果")
                return None
            
            logger.info(f"AcoustID匹配成功，分数: {score}")
            return self._parse_acoustid_result(best_result)
            
        except acoustid.WebServiceError as e:
            logger.error(f"AcoustID Web服务错误: {e}")
            return None
        except Exception as e:
            logger.error(f"AcoustID指纹查找失败: {e}")
            return None
    
    def scrape_music_file(self, file_path: str) -> Dict[str, Any]:
        """刮削音乐文件元数据"""
        # 检查缓存
        cache_key = f"music_{Path(file_path).name}"
        if self.cache_enabled and cache_key in self.cache_data:
            return self.cache_data[cache_key]
        
        metadata = {
            'file_path': file_path,
            'file_name': Path(file_path).name,
            'file_size': os.path.getsize(file_path),
            'scraped_at': str(asyncio.get_event_loop().time()),
            'sources': [],
            'fingerprint_quality': 'unknown'
        }
        
        # 1. 从文件本身提取元数据
        file_metadata = self.extract_metadata_from_file(file_path)
        metadata.update(file_metadata)
        metadata['sources'].append('file_tags')
        
        # 2. 尝试音频指纹识别（优先级最高）
        fingerprint_result = None
        if self.acoustid_api_key:
            fingerprint = self.generate_audio_fingerprint(file_path)
            if fingerprint:
                # 评估指纹质量
                if len(fingerprint) > 200:
                    metadata['fingerprint_quality'] = 'good'
                elif len(fingerprint) > 100:
                    metadata['fingerprint_quality'] = 'fair'
                else:
                    metadata['fingerprint_quality'] = 'poor'
                
                fingerprint_result = self.lookup_by_fingerprint(fingerprint)
                if fingerprint_result:
                    metadata.update(fingerprint_result)
                    metadata['sources'].append('acoustid_fingerprint')
                    logger.info(f"音频指纹识别成功: {file_path}")
        
        # 3. 如果指纹识别失败，尝试MusicBrainz搜索
        if not fingerprint_result and (file_metadata.get('title') or file_metadata.get('artist')):
            query_parts = []
            if file_metadata.get('artist'):
                query_parts.append(file_metadata['artist'])
            if file_metadata.get('title'):
                query_parts.append(file_metadata['title'])
            
            if query_parts:
                query = ' '.join(query_parts)
                mb_results = self.search_musicbrainz(query, 'recording')
                
                if mb_results:
                    best_match = mb_results[0]
                    metadata.update(best_match)
                    metadata['sources'].append('musicbrainz_search')
                    logger.info(f"MusicBrainz搜索成功: {file_path}")
        
        # 4. 如果都没有结果，尝试基于文件名的搜索
        if not metadata.get('title') and not metadata.get('artist'):
            # 从文件名提取可能的艺术家和标题
            filename = Path(file_path).stem
            # 简单的文件名解析逻辑
            if ' - ' in filename:
                parts = filename.split(' - ', 1)
                metadata['artist'] = parts[0].strip()
                metadata['title'] = parts[1].strip()
                metadata['sources'].append('filename_parsing')
            
            # 基于文件名搜索
            if metadata.get('title'):
                mb_results = self.search_musicbrainz(metadata['title'], 'recording')
                if mb_results:
                    best_match = mb_results[0]
                    metadata.update(best_match)
                    metadata['sources'].append('filename_search')
        
        # 5. 保存到缓存
        if self.cache_enabled:
            self.cache_data[cache_key] = metadata
            self._save_cache()
        
        # 记录刮削结果
        success_sources = [s for s in metadata['sources'] if s != 'file_tags']
        if success_sources:
            logger.info(f"音乐文件刮削成功: {file_path} (来源: {', '.join(success_sources)})")
        else:
            logger.warning(f"音乐文件刮削失败: {file_path}")
        
        return metadata
    
    def _parse_musicbrainz_recording(self, recording: Dict[str, Any]) -> Dict[str, Any]:
        """解析MusicBrainz录音信息"""
        return {
            'title': recording.get('title'),
            'artist': recording.get('artist-credit-phrase'),
            'album': recording.get('release-list', [{}])[0].get('title') if recording.get('release-list') else None,
            'year': recording.get('release-list', [{}])[0].get('date') if recording.get('release-list') else None,
            'mbid': recording.get('id'),
            'duration': recording.get('length'),
            'source': 'musicbrainz'
        }
    
    def _parse_musicbrainz_release(self, release: Dict[str, Any]) -> Dict[str, Any]:
        """解析MusicBrainz发行信息"""
        return {
            'title': release.get('title'),
            'artist': release.get('artist-credit-phrase'),
            'year': release.get('date'),
            'country': release.get('country'),
            'mbid': release.get('id'),
            'type': release.get('release-group', {}).get('type'),
            'source': 'musicbrainz'
        }
    
    def _parse_musicbrainz_artist(self, artist: Dict[str, Any]) -> Dict[str, Any]:
        """解析MusicBrainz艺术家信息"""
        return {
            'name': artist.get('name'),
            'mbid': artist.get('id'),
            'type': artist.get('type'),
            'country': artist.get('country'),
            'source': 'musicbrainz'
        }
    
    def _parse_acoustid_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """解析AcoustID结果"""
        recordings = result.get('recordings', [])
        if not recordings:
            return {}
        
        recording = recordings[0]
        return {
            'title': recording.get('title'),
            'artist': recording.get('artists', [{}])[0].get('name'),
            'album': recording.get('releasegroups', [{}])[0].get('title'),
            'mbid': recording.get('id'),
            'score': result.get('score'),
            'source': 'acoustid'
        }
    
    def batch_scrape_music_files(self, file_paths: List[str]) -> Dict[str, Dict[str, Any]]:
        """批量刮削音乐文件"""
        results = {}
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    results[file_path] = self.scrape_music_file(file_path)
                else:
                    results[file_path] = {'error': '文件不存在'}
            except Exception as e:
                results[file_path] = {'error': str(e)}
        
        return results
    
    def get_scraping_statistics(self) -> Dict[str, Any]:
        """获取刮削统计信息"""
        total_files = len(self.cache_data)
        successful_scrapes = sum(1 for data in self.cache_data.values() 
                                if 'error' not in data and data.get('sources'))
        
        source_counts = {}
        for data in self.cache_data.values():
            if 'sources' in data:
                for source in data['sources']:
                    source_counts[source] = source_counts.get(source, 0) + 1
        
        return {
            'total_files': total_files,
            'successful_scrapes': successful_scrapes,
            'success_rate': (successful_scrapes / total_files * 100) if total_files > 0 else 0,
            'source_distribution': source_counts
        }


# 使用示例
if __name__ == "__main__":
    # 创建音乐刮削器（需要配置AcoustID API密钥）
    scraper = MusicScraper(acoustid_api_key="YOUR_ACOUSTID_API_KEY")
    
    # 测试音乐文件刮削
    test_file = "/path/to/your/music/file.mp3"
    if os.path.exists(test_file):
        metadata = scraper.scrape_music_file(test_file)
        print("音乐元数据:")
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
    
    # 获取统计信息
    stats = scraper.get_scraping_statistics()
    print("\n刮削统计:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))