#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片库管理器
智能图片识别、分类和相册管理
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import cv2
import numpy as np
from PIL import Image, ExifTags

from core.config import settings


class ImageManager:
    """图片库管理器"""
    
    def __init__(self):
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        self.face_database = {}
        self.album_database = {}
        self.tag_database = {}
        
        # 初始化OpenCV人脸识别
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        self._load_image_database()
    
    def _load_image_database(self):
        """加载图片数据库"""
        try:
            with open('image_database.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.face_database = data.get('faces', {})
                self.album_database = data.get('albums', {})
                self.tag_database = data.get('tags', {})
        except:
            pass
    
    def _save_image_database(self):
        """保存图片数据库"""
        data = {
            'faces': self.face_database,
            'albums': self.album_database,
            'tags': self.tag_database
        }
        try:
            with open('image_database.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    async def analyze_image_file(self, file_path: str) -> Dict[str, Any]:
        """分析图片文件"""
        try:
            file_path = Path(file_path)
            if file_path.suffix.lower() not in self.supported_formats:
                return {"error": "不支持的图片格式"}
            
            # 提取图片元数据
            metadata = await self._extract_metadata(file_path)
            
            # 人脸识别和物体检测
            analysis_result = await self._analyze_image_content(file_path)
            
            # 智能分类和标签
            enhanced_metadata = await self._enhance_with_ai(metadata, analysis_result)
            
            # 更新图片数据库
            await self._update_image_database(enhanced_metadata)
            
            return enhanced_metadata
            
        except Exception as e:
            return {"error": f"图片分析失败: {str(e)}"}
    
    async def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """提取图片元数据"""
        try:
            with Image.open(file_path) as img:
                # 基础信息
                metadata = {
                    'file_path': str(file_path),
                    'file_name': file_path.name,
                    'file_size': file_path.stat().st_size,
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,  # (width, height)
                    'resolution': f"{img.size[0]}x{img.size[1]}",
                    'created_time': datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                    'modified_time': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                }
                
                # EXIF信息
                exif_data = {}
                if hasattr(img, '_getexif') and img._getexif():
                    for tag, value in img._getexif().items():
                        tag_name = ExifTags.TAGS.get(tag, tag)
                        exif_data[tag_name] = value
                
                metadata['exif'] = exif_data
                
                # 从EXIF中提取更多信息
                if 'DateTime' in exif_data:
                    metadata['capture_time'] = exif_data['DateTime']
                if 'Make' in exif_data:
                    metadata['camera_make'] = exif_data['Make']
                if 'Model' in exif_data:
                    metadata['camera_model'] = exif_data['Model']
                
                return metadata
                
        except Exception as e:
            return {"error": f"元数据提取失败: {str(e)}"}
    
    async def _analyze_image_content(self, file_path: Path) -> Dict[str, Any]:
        """分析图片内容"""
        try:
            # 使用OpenCV进行图像分析
            img = cv2.imread(str(file_path))
            if img is None:
                return {"error": "无法读取图片"}
            
            analysis_result = {
                'faces_detected': 0,
                'face_locations': [],
                'dominant_colors': [],
                'brightness': 0,
                'contrast': 0,
                'sharpness': 0
            }
            
            # 人脸检测
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            analysis_result['faces_detected'] = len(faces)
            analysis_result['face_locations'] = [{
                'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h)
            } for (x, y, w, h) in faces]
            
            # 主色调分析
            analysis_result['dominant_colors'] = self._get_dominant_colors(img)
            
            # 图像质量评估
            analysis_result.update(self._assess_image_quality(img))
            
            return analysis_result
            
        except Exception as e:
            return {"error": f"图片内容分析失败: {str(e)}"}
    
    def _get_dominant_colors(self, img: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
        """获取图片主色调"""
        try:
            # 将图片转换为RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # 重塑为2D数组
            pixels = img_rgb.reshape((-1, 3))
            pixels = np.float32(pixels)
            
            # K-means聚类
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
            _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
            
            # 计算每个颜色的比例
            unique, counts = np.unique(labels, return_counts=True)
            color_percentages = counts / counts.sum()
            
            dominant_colors = []
            for i, color in enumerate(centers):
                dominant_colors.append({
                    'rgb': [int(c) for c in color],
                    'hex': f"#{int(color[0]):02x}{int(color[1]):02x}{int(color[2]):02x}",
                    'percentage': float(color_percentages[i])
                })
            
            return dominant_colors
            
        except Exception as e:
            return []
    
    def _assess_image_quality(self, img: np.ndarray) -> Dict[str, float]:
        """评估图片质量"""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 亮度评估
            brightness = np.mean(gray)
            
            # 对比度评估
            contrast = np.std(gray)
            
            # 锐度评估（使用拉普拉斯算子）
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            sharpness = np.var(laplacian)
            
            return {
                'brightness': float(brightness),
                'contrast': float(contrast),
                'sharpness': float(sharpness)
            }
            
        except Exception as e:
            return {'brightness': 0, 'contrast': 0, 'sharpness': 0}
    
    async def _enhance_with_ai(self, metadata: Dict[str, Any], analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """使用AI增强图片分析"""
        enhanced = metadata.copy()
        enhanced.update(analysis_result)
        
        # 智能场景分类
        enhanced['scene_category'] = self._classify_scene(enhanced)
        
        # 人脸识别（如果检测到人脸）
        if enhanced.get('faces_detected', 0) > 0:
            enhanced['face_analysis'] = await self._analyze_faces(enhanced)
        
        # 智能标签生成
        enhanced['ai_tags'] = self._generate_ai_tags(enhanced)
        
        # 图片质量评分
        enhanced['quality_score'] = self._calculate_quality_score(enhanced)
        
        return enhanced
    
    def _classify_scene(self, metadata: Dict[str, Any]) -> str:
        """分类图片场景"""
        # 基于文件名和元数据的简单分类
        filename = metadata.get('file_name', '').lower()
        
        scene_keywords = {
            'portrait': ['portrait', '人像', '人物', 'face', '自拍'],
            'landscape': ['landscape', '风景', '山水', '自然', 'scenery'],
            'cityscape': ['city', '城市', '建筑', 'urban', 'skyline'],
            'food': ['food', '美食', '餐饮', 'cooking', 'recipe'],
            'animal': ['animal', '宠物', '猫', '狗', 'bird', 'wildlife'],
            'travel': ['travel', '旅游', 'vacation', 'journey', 'trip'],
            'event': ['wedding', '婚礼', 'party', '聚会', 'celebration'],
            'document': ['document', '文档', '扫描', 'scan', 'paper']
        }
        
        for scene, keywords in scene_keywords.items():
            if any(keyword in filename for keyword in keywords):
                return scene
        
        # 基于人脸检测
        if metadata.get('faces_detected', 0) > 0:
            return 'portrait'
        
        return 'general'
    
    async def _analyze_faces(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """分析人脸特征"""
        # 这里可以集成更高级的人脸识别API
        return {
            'face_count': metadata.get('faces_detected', 0),
            'analysis_method': 'basic_detection',
            'features': ['face_detected']  # 简化实现
        }
    
    def _generate_ai_tags(self, metadata: Dict[str, Any]) -> List[str]:
        """生成AI标签"""
        tags = []
        
        # 基于场景分类
        scene = metadata.get('scene_category', '')
        if scene:
            tags.append(scene)
        
        # 基于人脸检测
        if metadata.get('faces_detected', 0) > 0:
            tags.append('people')
            tags.append(f"{metadata['faces_detected']}_people")
        
        # 基于图片质量
        quality_score = metadata.get('quality_score', 0)
        if quality_score > 0.8:
            tags.append('high_quality')
        elif quality_score < 0.4:
            tags.append('low_quality')
        
        # 基于分辨率
        size = metadata.get('size', (0, 0))
        if size[0] >= 3840 or size[1] >= 2160:
            tags.append('4k')
        elif size[0] >= 1920 or size[1] >= 1080:
            tags.append('hd')
        
        return tags
    
    def _calculate_quality_score(self, metadata: Dict[str, Any]) -> float:
        """计算图片质量评分"""
        score = 0.5  # 基础分数
        
        # 基于分辨率
        size = metadata.get('size', (0, 0))
        if size[0] >= 3840 or size[1] >= 2160:
            score += 0.2  # 4K加分
        elif size[0] >= 1920 or size[1] >= 1080:
            score += 0.1  # HD加分
        
        # 基于锐度
        sharpness = metadata.get('sharpness', 0)
        if sharpness > 1000:
            score += 0.15
        elif sharpness > 500:
            score += 0.1
        
        # 基于对比度
        contrast = metadata.get('contrast', 0)
        if contrast > 50:
            score += 0.15
        
        return min(1.0, score)
    
    async def _update_image_database(self, metadata: Dict[str, Any]):
        """更新图片数据库"""
        file_path = metadata.get('file_path')
        if not file_path:
            return
        
        # 更新人脸数据库
        if metadata.get('faces_detected', 0) > 0:
            face_key = f"face_{Path(file_path).stem}"
            self.face_database[face_key] = {
                'file_path': file_path,
                'face_count': metadata['faces_detected'],
                'face_locations': metadata.get('face_locations', []),
                'detected_at': str(asyncio.get_event_loop().time())
            }
        
        # 更新标签数据库
        for tag in metadata.get('ai_tags', []):
            if tag not in self.tag_database:
                self.tag_database[tag] = []
            if file_path not in self.tag_database[tag]:
                self.tag_database[tag].append(file_path)
        
        self._save_image_database()
    
    async def create_album(self, name: str, images: List[str]) -> Dict[str, Any]:
        """创建相册"""
        album_id = f"album_{int(asyncio.get_event_loop().time())}"
        
        album = {
            'id': album_id,
            'name': name,
            'images': images,
            'created_at': str(asyncio.get_event_loop().time()),
            'image_count': len(images),
            'cover_image': images[0] if images else None
        }
        
        self.album_database[album_id] = album
        self._save_image_database()
        
        return album
    
    async def search_images(self, query: str, search_type: str = "all") -> Dict[str, Any]:
        """搜索图片"""
        results = {
            'by_filename': [],
            'by_tags': [],
            'by_scene': []
        }
        
        query_lower = query.lower()
        
        # 这里简化实现，实际需要遍历所有图片文件
        # 基于文件名的搜索
        # 基于标签的搜索
        # 基于场景的搜索
        
        return results


# 使用示例
async def demo_image_manager():
    """演示图片管理器功能"""
    manager = ImageManager()
    
    # 分析图片文件
    result = await manager.analyze_image_file("example_photo.jpg")
    print("图片分析结果:", json.dumps(result, indent=2, ensure_ascii=False))
    
    # 创建相册
    album = await manager.create_album("我的相册", ["photo1.jpg", "photo2.jpg"])
    print("\n创建的相册:", json.dumps(album, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(demo_image_manager())