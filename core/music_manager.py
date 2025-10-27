#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音乐库管理器
智能音乐文件识别、分类和管理
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis

from core.config import settings


class MusicManager:
    """音乐库管理器"""
    
    def __init__(self):
        self.supported_formats = ['.mp3', '.flac', '.wav', '.ogg', '.m4a', '.aac']
        self.artist_database = {}
        self.album_database = {}
        self.playlist_database = {}
        
        self._load_music_database()
    
    def _load_music_database(self):
        """加载音乐数据库"""
        try:
            with open('music_database.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.artist_database = data.get('artists', {})
                self.album_database = data.get('albums', {})
                self.playlist_database = data.get('playlists', {})
        except:
            pass
    
    def _save_music_database(self):
        """保存音乐数据库"""
        data = {
            'artists': self.artist_database,
            'albums': self.album_database,
            'playlists': self.playlist_database
        }
        try:
            with open('music_database.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    async def analyze_music_file(self, file_path: str) -> Dict[str, Any]:
        """分析音乐文件"""
        try:
            file_path = Path(file_path)
            if file_path.suffix.lower() not in self.supported_formats:
                return {"error": "不支持的音频格式"}
            
            # 读取音频元数据
            metadata = await self._extract_metadata(file_path)
            
            # 智能识别艺术家和专辑
            enhanced_metadata = await self._enhance_with_ai(metadata, file_path)
            
            # 更新音乐数据库
            await self._update_music_database(enhanced_metadata)
            
            return enhanced_metadata
            
        except Exception as e:
            return {"error": f"音乐文件分析失败: {str(e)}"}
    
    async def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """提取音频元数据"""
        try:
            # 根据文件格式使用不同的解析器
            if file_path.suffix.lower() == '.mp3':
                audio = MP3(file_path, ID3=EasyID3)
            elif file_path.suffix.lower() == '.flac':
                audio = FLAC(file_path)
            elif file_path.suffix.lower() == '.ogg':
                audio = OggVorbis(file_path)
            else:
                audio = mutagen.File(file_path)
            
            metadata = {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'file_size': file_path.stat().st_size,
                'format': file_path.suffix.lower(),
                'duration': audio.info.length if audio else 0,
                'bitrate': audio.info.bitrate if audio else 0,
                'sample_rate': audio.info.sample_rate if audio else 0
            }
            
            # 提取ID3标签
            if audio and hasattr(audio, 'tags'):
                tags = audio.tags
                if tags:
                    metadata.update({
                        'title': tags.get('title', [''])[0] if tags.get('title') else '',
                        'artist': tags.get('artist', [''])[0] if tags.get('artist') else '',
                        'album': tags.get('album', [''])[0] if tags.get('album') else '',
                        'genre': tags.get('genre', [''])[0] if tags.get('genre') else '',
                        'year': tags.get('date', [''])[0] if tags.get('date') else '',
                        'track_number': tags.get('tracknumber', [''])[0] if tags.get('tracknumber') else '',
                        'album_artist': tags.get('albumartist', [''])[0] if tags.get('albumartist') else ''
                    })
            
            return metadata
            
        except Exception as e:
            return {"error": f"元数据提取失败: {str(e)}"}
    
    async def _enhance_with_ai(self, metadata: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """使用AI增强音乐识别"""
        # 这里可以集成音乐识别API，如Shazam、AcoustID等
        
        enhanced = metadata.copy()
        
        # 智能填充缺失信息
        if not enhanced.get('artist') and enhanced.get('file_name'):
            enhanced['artist'] = self._guess_artist_from_filename(enhanced['file_name'])
        
        if not enhanced.get('title') and enhanced.get('file_name'):
            enhanced['title'] = self._guess_title_from_filename(enhanced['file_name'])
        
        if not enhanced.get('genre'):
            enhanced['genre'] = self._classify_genre(enhanced)
        
        # 音乐质量评估
        enhanced['quality_score'] = self._assess_audio_quality(enhanced)
        
        # 相似艺术家推荐
        enhanced['similar_artists'] = self._get_similar_artists(enhanced.get('artist', ''))
        
        return enhanced
    
    def _guess_artist_from_filename(self, filename: str) -> str:
        """从文件名猜测艺术家"""
        # 常见的文件名模式：艺术家 - 歌曲名
        if ' - ' in filename:
            parts = filename.split(' - ')
            if len(parts) >= 2:
                return parts[0].strip()
        
        # 其他模式处理
        filename = Path(filename).stem  # 移除扩展名
        
        # 尝试提取艺术家信息
        for separator in ['_', '.', '~']:
            if separator in filename:
                parts = filename.split(separator)
                if len(parts) >= 2:
                    return parts[0].strip()
        
        return "未知艺术家"
    
    def _guess_title_from_filename(self, filename: str) -> str:
        """从文件名猜测歌曲标题"""
        filename = Path(filename).stem  # 移除扩展名
        
        if ' - ' in filename:
            parts = filename.split(' - ')
            if len(parts) >= 2:
                return parts[1].strip()
        
        # 移除常见的数字前缀（如01、02等）
        import re
        filename = re.sub(r'^\d+\s*[-_\s]*', '', filename)
        
        return filename.strip()
    
    def _classify_genre(self, metadata: Dict[str, Any]) -> str:
        """分类音乐流派"""
        # 基于文件名和元数据的简单分类
        filename = metadata.get('file_name', '').lower()
        artist = metadata.get('artist', '').lower()
        
        # 基于关键词的流派分类
        genre_keywords = {
            'pop': ['pop', '流行'],
            'rock': ['rock', '摇滚'],
            'jazz': ['jazz', '爵士'],
            'classical': ['classical', 'classic', '古典'],
            'electronic': ['electronic', 'edm', '电子', '电音'],
            'hiphop': ['hiphop', 'rap', '嘻哈'],
            'country': ['country', '乡村'],
            'folk': ['folk', '民谣'],
            'r&b': ['r&b', 'rb', '节奏布鲁斯']
        }
        
        for genre, keywords in genre_keywords.items():
            if any(keyword in filename or keyword in artist for keyword in keywords):
                return genre
        
        return 'unknown'
    
    def _assess_audio_quality(self, metadata: Dict[str, Any]) -> float:
        """评估音频质量"""
        score = 0.5  # 基础分数
        
        # 基于比特率评分
        bitrate = metadata.get('bitrate', 0)
        if bitrate > 320000:  # 320kbps以上
            score += 0.3
        elif bitrate > 192000:  # 192kbps以上
            score += 0.2
        elif bitrate > 128000:  # 128kbps以上
            score += 0.1
        
        # 基于格式评分
        format_type = metadata.get('format', '')
        if format_type in ['.flac', '.wav']:
            score += 0.2  # 无损格式加分
        elif format_type == '.mp3':
            score += 0.1  # 常见格式加分
        
        return min(1.0, score)
    
    def _get_similar_artists(self, artist: str) -> List[str]:
        """获取相似艺术家"""
        # 简单的相似艺术家推荐（可集成音乐API）
        similar_artists_map = {
            '周杰伦': ['林俊杰', '王力宏', '蔡依林'],
            'Taylor Swift': ['Adele', 'Ed Sheeran', 'Katy Perry'],
            'Coldplay': ['Radiohead', 'U2', 'The Killers'],
            '陈奕迅': ['张学友', '刘德华', '王菲']
        }
        
        return similar_artists_map.get(artist, [])
    
    async def _update_music_database(self, metadata: Dict[str, Any]):
        """更新音乐数据库"""
        artist = metadata.get('artist')
        album = metadata.get('album')
        
        if artist:
            if artist not in self.artist_database:
                self.artist_database[artist] = {
                    'albums': [],
                    'genres': [],
                    'first_seen': str(asyncio.get_event_loop().time()),
                    'track_count': 0
                }
            
            self.artist_database[artist]['track_count'] += 1
            
            # 更新流派信息
            genre = metadata.get('genre')
            if genre and genre not in self.artist_database[artist]['genres']:
                self.artist_database[artist]['genres'].append(genre)
        
        if album and artist:
            album_key = f"{artist} - {album}"
            if album_key not in self.album_database:
                self.album_database[album_key] = {
                    'artist': artist,
                    'title': album,
                    'year': metadata.get('year', ''),
                    'tracks': [],
                    'genre': metadata.get('genre', '')
                }
            
            # 添加曲目信息
            track_info = {
                'title': metadata.get('title', ''),
                'track_number': metadata.get('track_number', ''),
                'duration': metadata.get('duration', 0),
                'file_path': metadata.get('file_path', '')
            }
            
            if track_info not in self.album_database[album_key]['tracks']:
                self.album_database[album_key]['tracks'].append(track_info)
        
        self._save_music_database()
    
    async def create_playlist(self, name: str, tracks: List[str]) -> Dict[str, Any]:
        """创建播放列表"""
        playlist_id = f"playlist_{int(asyncio.get_event_loop().time())}"
        
        playlist = {
            'id': playlist_id,
            'name': name,
            'tracks': tracks,
            'created_at': str(asyncio.get_event_loop().time()),
            'track_count': len(tracks),
            'total_duration': sum(track.get('duration', 0) for track in tracks)
        }
        
        self.playlist_database[playlist_id] = playlist
        self._save_music_database()
        
        return playlist
    
    async def get_artist_discography(self, artist: str) -> Dict[str, Any]:
        """获取艺术家作品集"""
        if artist not in self.artist_database:
            return {"error": "艺术家不存在"}
        
        artist_info = self.artist_database[artist]
        albums = [album for album_key, album in self.album_database.items() 
                 if album['artist'] == artist]
        
        return {
            'artist': artist,
            'albums': albums,
            'track_count': artist_info['track_count'],
            'genres': artist_info['genres']
        }
    
    async def search_music(self, query: str, search_type: str = "all") -> Dict[str, Any]:
        """搜索音乐"""
        results = {
            'artists': [],
            'albums': [],
            'tracks': []
        }
        
        query_lower = query.lower()
        
        # 搜索艺术家
        if search_type in ['all', 'artists']:
            for artist, info in self.artist_database.items():
                if query_lower in artist.lower():
                    results['artists'].append({
                        'name': artist,
                        'track_count': info['track_count'],
                        'genres': info['genres']
                    })
        
        # 搜索专辑
        if search_type in ['all', 'albums']:
            for album_key, album in self.album_database.items():
                if (query_lower in album['title'].lower() or 
                    query_lower in album['artist'].lower()):
                    results['albums'].append(album)
        
        # 搜索曲目（需要读取所有曲目信息）
        # 这里简化实现，实际需要遍历所有文件
        
        return results


# 使用示例
async def demo_music_manager():
    """演示音乐管理器功能"""
    manager = MusicManager()
    
    # 分析音乐文件
    result = await manager.analyze_music_file("example_song.mp3")
    print("音乐分析结果:", json.dumps(result, indent=2, ensure_ascii=False))
    
    # 搜索音乐
    search_results = await manager.search_music("周杰伦")
    print("\n搜索结果:", json.dumps(search_results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(demo_music_manager())