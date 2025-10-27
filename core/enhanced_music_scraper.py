#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版音乐刮削模块
集成MusicBrainz + AcoustID音频指纹识别 + Discogs + 智能匹配算法
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
import re
from difflib import SequenceMatcher

import musicbrainzngs
import acoustid
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis

logger = logging.getLogger(__name__)


class EnhancedMusicScraper:
    """增强版音乐刮削器"""
    
    def __init__(self, acoustid_api_key: Optional[str] = None, discogs_token: Optional[str] = None):
        """初始化增强版音乐刮削器"""
        # 配置MusicBrainz
        musicbrainzngs.set_useragent(
            "StrataMedia/2.0.0",
            "2.0.0",
            "you@example.com"
        )
        
        self.acoustid_api_key = acoustid_api_key
        self.discogs_token = discogs_token
        self.cache_enabled = True
        self.cache_file = "enhanced_music_cache.json"
        self.cache_data = self._load_cache()
        
        # 智能匹配配置
        self.similarity_threshold = 0.8
        self.max_retry_attempts = 3
        self.timeout_seconds = 30
    
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
    
    def extract_enhanced_metadata(self, file_path: str) -> Dict[str, Any]:
        """增强版元数据提取"""
        try:
            audio_file = mutagen.File(file_path)
            if not audio_file:
                return {}
            
            metadata = {}
            
            # 基础音频信息
            if hasattr(audio_file, 'info'):
                info = audio_file.info
                metadata.update({
                    'duration': int(info.length) if info.length else None,
                    'bitrate': info.bitrate if hasattr(info, 'bitrate') else None,
                    'sample_rate': info.sample_rate if hasattr(info, 'sample_rate') else None,
                    'channels': info.channels if hasattr(info, 'channels') else None,
                    'bits_per_sample': getattr(info, 'bits_per_sample', None)
                })
            
            # 增强标签提取
            metadata.update(self._extract_comprehensive_tags(audio_file))
            
            # 文件信息
            metadata.update({
                'file_format': Path(file_path).suffix.lower(),
                'file_size_mb': round(os.path.getsize(file_path) / (1024 * 1024), 2),
                'file_modified': os.path.getmtime(file_path)
            })
            
            # 清理空值
            metadata = {k: v for k, v in metadata.items() if v is not None}
            
            return metadata
            
        except Exception as e:
            logger.error(f"增强版元数据提取失败 {file_path}: {e}")
            return {}
    
    def _extract_comprehensive_tags(self, audio_file) -> Dict[str, Any]:
        """提取全面的音频标签"""
        tags = {}
        
        try:
            if isinstance(audio_file, EasyID3):
                # MP3文件
                tags.update({
                    'title': self._get_first_tag(audio_file, 'title'),
                    'artist': self._get_first_tag(audio_file, 'artist'),
                    'album': self._get_first_tag(audio_file, 'album'),
                    'year': self._get_first_tag(audio_file, 'date'),
                    'genre': self._get_first_tag(audio_file, 'genre'),
                    'track_number': self._get_first_tag(audio_file, 'tracknumber'),
                    'disc_number': self._get_first_tag(audio_file, 'discnumber'),
                    'composer': self._get_first_tag(audio_file, 'composer'),
                    'album_artist': self._get_first_tag(audio_file, 'albumartist'),
                    'bpm': self._get_first_tag(audio_file, 'bpm')
                })
            elif isinstance(audio_file, FLAC):
                # FLAC文件
                if audio_file.tags:
                    tags.update({
                        'title': self._get_first_tag(audio_file.tags, 'title'),
                        'artist': self._get_first_tag(audio_file.tags, 'artist'),
                        'album': self._get_first_tag(audio_file.tags, 'album'),
                        'date': self._get_first_tag(audio_file.tags, 'date'),
                        'genre': self._get_first_tag(audio_file.tags, 'genre'),
                        'tracknumber': self._get_first_tag(audio_file.tags, 'tracknumber'),
                        'discnumber': self._get_first_tag(audio_file.tags, 'discnumber'),
                        'composer': self._get_first_tag(audio_file.tags, 'composer'),
                        'album_artist': self._get_first_tag(audio_file.tags, 'albumartist'),
                        'organization': self._get_first_tag(audio_file.tags, 'organization')
                    })
            elif isinstance(audio_file, OggVorbis):
                # OGG文件
                tags.update({
                    'title': self._get_first_tag(audio_file.tags, 'title'),
                    'artist': self._get_first_tag(audio_file.tags, 'artist'),
                    'album': self._get_first_tag(audio_file.tags, 'album'),
                    'date': self._get_first_tag(audio_file.tags, 'date'),
                    'genre': self._get_first_tag(audio_file.tags, 'genre'),
                    'tracknumber': self._get_first_tag(audio_file.tags, 'tracknumber')
                })
            
        except Exception as e:
            logger.warning(f"标签提取失败: {e}")
        
        return tags
    
    def _get_first_tag(self, tags, key: str) -> Optional[str]:
        """获取标签的第一个值"""
        try:
            value = tags.get(key)
            if value and len(value) > 0:
                return str(value[0])
        except (AttributeError, IndexError, TypeError):
            pass
        return None
    
    def generate_robust_fingerprint(self, file_path: str) -> Optional[Dict[str, Any]]:
        """生成鲁棒的音频指纹"""
        try:
            # 检查文件
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None
            
            # 文件大小限制
            file_size = os.path.getsize(file_path)
            if file_size > 500 * 1024 * 1024:
                logger.warning(f"文件过大: {file_path}")
                return None
            
            # 生成指纹
            duration, fingerprint = acoustid.fingerprint_file(file_path)
            
            # 指纹质量评估
            quality = self._assess_fingerprint_quality(fingerprint, duration)
            
            return {
                'fingerprint': fingerprint,
                'duration': duration,
                'quality': quality,
                'length': len(fingerprint)
            }
            
        except Exception as e:
            logger.error(f"指纹生成失败 {file_path}: {e}")
            return None
    
    def _assess_fingerprint_quality(self, fingerprint: str, duration: float) -> str:
        """评估指纹质量"""
        if len(fingerprint) < 50:
            return 'poor'
        elif len(fingerprint) < 100:
            return 'fair'
        elif len(fingerprint) < 200:
            return 'good'
        else:
            return 'excellent'
    
    def intelligent_music_search(self, file_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """智能音乐搜索"""
        results = {}
        
        # 1. 音频指纹搜索（最高优先级）
        if self.acoustid_api_key:
            fingerprint_data = self.generate_robust_fingerprint(file_path)
            if fingerprint_data and fingerprint_data['quality'] in ['good', 'excellent']:
                fingerprint_result = self.lookup_by_fingerprint(fingerprint_data['fingerprint'])
                if fingerprint_result:
                    results.update(fingerprint_result)
                    results['match_source'] = 'acoustid_fingerprint'
                    results['match_confidence'] = 0.95
                    return results
        
        # 2. MusicBrainz精确搜索
        if metadata.get('title') and metadata.get('artist'):
            mb_results = self.search_musicbrainz_comprehensive(
                metadata['title'], 
                metadata['artist'],
                metadata.get('album'),
                metadata.get('year')
            )
            if mb_results:
                best_match = self._select_best_match(mb_results, metadata)
                if best_match and best_match['confidence'] > self.similarity_threshold:
                    results.update(best_match['metadata'])
                    results['match_source'] = 'musicbrainz_precise'
                    results['match_confidence'] = best_match['confidence']
                    return results
        
        # 3. 文件名解析搜索
        filename_results = self._search_by_filename(file_path)
        if filename_results:
            results.update(filename_results)
            results['match_source'] = 'filename_analysis'
            results['match_confidence'] = 0.7
        
        return results
    
    def search_musicbrainz_comprehensive(self, title: str, artist: str, 
                                       album: Optional[str] = None, 
                                       year: Optional[str] = None) -> List[Dict[str, Any]]:
        """综合MusicBrainz搜索"""
        results = []
        
        # 尝试多种搜索策略
        search_queries = [
            f"{artist} {title}",
            f"{title} artist:{artist}",
            title  # 仅标题搜索
        ]
        
        if album:
            search_queries.append(f"{artist} {album} {title}")
        
        for query in search_queries:
            try:
                mb_results = musicbrainzngs.search_recordings(query=query, limit=10)
                recordings = mb_results.get('recording-list', [])
                
                for recording in recordings:
                    parsed = self._parse_musicbrainz_recording(recording)
                    if parsed:
                        results.append(parsed)
                
                if results:
                    break
                    
            except Exception as e:
                logger.warning(f"MusicBrainz搜索失败 {query}: {e}")
        
        return results
    
    def _select_best_match(self, candidates: List[Dict[str, Any]], 
                          original_metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """选择最佳匹配"""
        scored_candidates = []
        
        for candidate in candidates:
            score = self._calculate_similarity_score(candidate, original_metadata)
            scored_candidates.append({
                'metadata': candidate,
                'confidence': score
            })
        
        # 按置信度排序
        scored_candidates.sort(key=lambda x: x['confidence'], reverse=True)
        
        return scored_candidates[0] if scored_candidates else None
    
    def _calculate_similarity_score(self, candidate: Dict[str, Any], 
                                   original: Dict[str, Any]) -> float:
        """计算相似度分数"""
        score = 0.0
        total_weight = 0
        
        # 标题相似度（权重最高）
        if candidate.get('title') and original.get('title'):
            title_similarity = self._string_similarity(candidate['title'], original['title'])
            score += title_similarity * 0.4
            total_weight += 0.4
        
        # 艺术家相似度
        if candidate.get('artist') and original.get('artist'):
            artist_similarity = self._string_similarity(candidate['artist'], original['artist'])
            score += artist_similarity * 0.3
            total_weight += 0.3
        
        # 专辑相似度
        if candidate.get('album') and original.get('album'):
            album_similarity = self._string_similarity(candidate['album'], original['album'])
            score += album_similarity * 0.2
            total_weight += 0.2
        
        # 年份匹配
        if candidate.get('year') and original.get('year'):
            if candidate['year'] == original['year']:
                score += 0.1
            total_weight += 0.1
        
        # 归一化分数
        if total_weight > 0:
            return score / total_weight
        else:
            return 0.0
    
    def _string_similarity(self, str1: str, str2: str) -> float:
        """计算字符串相似度"""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def _search_by_filename(self, file_path: str) -> Dict[str, Any]:
        """基于文件名搜索"""
        filename = Path(file_path).stem
        
        # 常见文件名格式解析
        patterns = [
            r'^(.*?) - (.*?)$',  # "艺术家 - 标题"
            r'^(.*?)_(.*?)$',    # "艺术家_标题"
            r'^(\d+)\s+(.*?)$'  # "序号 标题"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    artist = groups[0].strip()
                    title = groups[1].strip()
                    
                    # 搜索MusicBrainz
                    mb_results = self.search_musicbrainz_comprehensive(title, artist)
                    if mb_results:
                        return mb_results[0]
        
        return {}
    
    def scrape_enhanced_music_file(self, file_path: str) -> Dict[str, Any]:
        """增强版音乐文件刮削"""
        # 检查缓存
        cache_key = f"enhanced_music_{Path(file_path).name}"
        if self.cache_enabled and cache_key in self.cache_data:
            return self.cache_data[cache_key]
        
        metadata = {
            'file_path': file_path,
            'file_name': Path(file_path).name,
            'file_size': os.path.getsize(file_path),
            'scraped_at': str(asyncio.get_event_loop().time()),
            'sources': [],
            'match_confidence': 0.0,
            'processing_steps': []
        }
        
        # 步骤1: 提取文件元数据
        file_metadata = self.extract_enhanced_metadata(file_path)
        metadata.update(file_metadata)
        metadata['sources'].append('file_tags')
        metadata['processing_steps'].append('file_metadata_extraction')
        
        # 步骤2: 智能搜索
        search_results = self.intelligent_music_search(file_path, file_metadata)
        if search_results:
            metadata.update(search_results)
            metadata['processing_steps'].append('intelligent_search')
        
        # 步骤3: 质量评估
        metadata['quality_score'] = self._assess_overall_quality(metadata)
        
        # 保存到缓存
        if self.cache_enabled:
            self.cache_data[cache_key] = metadata
            self._save_cache()
        
        # 记录结果
        self._log_scraping_result(file_path, metadata)
        
        return metadata
    
    def _assess_overall_quality(self, metadata: Dict[str, Any]) -> float:
        """评估整体刮削质量"""
        score = 0.0
        
        # 基础信息完整性
        if metadata.get('title'): score += 0.3
        if metadata.get('artist'): score += 0.3
        if metadata.get('album'): score += 0.2
        if metadata.get('year'): score += 0.1
        if metadata.get('genre'): score += 0.1
        
        # 匹配置信度加成
        if 'match_confidence' in metadata:
            score += metadata['match_confidence'] * 0.2
        
        return min(score, 1.0)
    
    def _log_scraping_result(self, file_path: str, metadata: Dict[str, Any]):
        """记录刮削结果"""
        quality_score = metadata.get('quality_score', 0)
        sources = metadata.get('sources', [])
        
        if quality_score > 0.7:
            logger.info(f"高质量刮削: {file_path} (分数: {quality_score:.2f}, 来源: {sources})")
        elif quality_score > 0.3:
            logger.info(f"中等质量刮削: {file_path} (分数: {quality_score:.2f})")
        else:
            logger.warning(f"低质量刮削: {file_path} (分数: {quality_score:.2f})")
    
    # 保留原有方法以保持兼容性
    def scrape_music_file(self, file_path: str) -> Dict[str, Any]:
        """兼容性方法"""
        return self.scrape_enhanced_music_file(file_path)
    
    def lookup_by_fingerprint(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        """通过音频指纹查找音乐"""
        if not self.acoustid_api_key:
            return None
        
        try:
            results = acoustid.lookup(
                self.acoustid_api_key,
                fingerprint,
                meta='recordings releases'
            )
            
            if results and len(results) > 0:
                best_result = results[0]
                return self._parse_acoustid_result(best_result)
            
            return None
            
        except Exception as e:
            logger.error(f"AcoustID指纹查找失败: {e}")
            return None
    
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


# 使用示例
if __name__ == "__main__":
    # 创建增强版音乐刮削器
    scraper = EnhancedMusicScraper(
        acoustid_api_key="YOUR_ACOUSTID_API_KEY",
        discogs_token="YOUR_DISCOGS_TOKEN"
    )
    
    # 测试音乐文件刮削
    test_file = "/path/to/your/music/file.mp3"
    if os.path.exists(test_file):
        metadata = scraper.scrape_enhanced_music_file(test_file)
        print("增强版音乐元数据:")
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
        
        print(f"\n刮削质量分数: {metadata.get('quality_score', 0):.2f}")
        print(f"匹配来源: {metadata.get('match_source', 'unknown')}")
        print(f"处理步骤: {metadata.get('processing_steps', [])}")