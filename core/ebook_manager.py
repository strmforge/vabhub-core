#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电子书管理器
智能电子书识别、分类和阅读管理
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import ebooklib
from ebooklib import epub
import PyPDF2
import chardet

from core.config import settings


class EbookManager:
    """电子书管理器"""
    
    def __init__(self):
        self.supported_formats = ['.epub', '.pdf', '.mobi', '.azw3', '.txt', '.doc', '.docx']
        self.author_database = {}
        self.book_database = {}
        self.library_database = {}
        
        self._load_ebook_database()
    
    def _load_ebook_database(self):
        """加载电子书数据库"""
        try:
            with open('ebook_database.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.author_database = data.get('authors', {})
                self.book_database = data.get('books', {})
                self.library_database = data.get('libraries', {})
        except:
            pass
    
    def _save_ebook_database(self):
        """保存电子书数据库"""
        data = {
            'authors': self.author_database,
            'books': self.book_database,
            'libraries': self.library_database
        }
        try:
            with open('ebook_database.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    async def analyze_ebook_file(self, file_path: str) -> Dict[str, Any]:
        """分析电子书文件"""
        try:
            file_path = Path(file_path)
            if file_path.suffix.lower() not in self.supported_formats:
                return {"error": "不支持的电子书格式"}
            
            # 提取电子书元数据
            metadata = await self._extract_metadata(file_path)
            
            # 内容分析和智能分类
            analysis_result = await self._analyze_ebook_content(file_path)
            
            # 智能增强
            enhanced_metadata = await self._enhance_with_ai(metadata, analysis_result)
            
            # 更新电子书数据库
            await self._update_ebook_database(enhanced_metadata)
            
            return enhanced_metadata
            
        except Exception as e:
            return {"error": f"电子书分析失败: {str(e)}"}
    
    async def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """提取电子书元数据"""
        try:
            file_extension = file_path.suffix.lower()
            metadata = {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'file_size': file_path.stat().st_size,
                'format': file_extension,
                'created_time': datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                'modified_time': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            }
            
            # 根据格式提取特定元数据
            if file_extension == '.epub':
                metadata.update(await self._extract_epub_metadata(file_path))
            elif file_extension == '.pdf':
                metadata.update(await self._extract_pdf_metadata(file_path))
            elif file_extension in ['.txt', '.doc', '.docx']:
                metadata.update(await self._extract_text_metadata(file_path))
            
            return metadata
            
        except Exception as e:
            return {"error": f"元数据提取失败: {str(e)}"}
    
    async def _extract_epub_metadata(self, file_path: Path) -> Dict[str, Any]:
        """提取EPUB格式元数据"""
        try:
            book = epub.read_epub(str(file_path))
            
            metadata = {
                'title': '',
                'author': '',
                'publisher': '',
                'language': '',
                'isbn': '',
                'publication_date': '',
                'description': ''
            }
            
            # 提取DC元数据
            for item in book.get_metadata('DC', ''):
                if item[0] == 'title':
                    metadata['title'] = item[1]
                elif item[0] == 'creator':
                    metadata['author'] = item[1]
                elif item[0] == 'publisher':
                    metadata['publisher'] = item[1]
                elif item[0] == 'language':
                    metadata['language'] = item[1]
                elif item[0] == 'identifier':
                    if 'isbn' in str(item[1]).lower():
                        metadata['isbn'] = item[1]
                elif item[0] == 'date':
                    metadata['publication_date'] = item[1]
                elif item[0] == 'description':
                    metadata['description'] = item[1]
            
            # 估算页数（基于文件大小和格式）
            file_size = file_path.stat().st_size
            metadata['estimated_pages'] = max(10, file_size // 5000)  # 粗略估算
            
            return metadata
            
        except Exception as e:
            return {"error": f"EPUB元数据提取失败: {str(e)}"}
    
    async def _extract_pdf_metadata(self, file_path: Path) -> Dict[str, Any]:
        """提取PDF格式元数据"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                metadata = {
                    'title': '',
                    'author': '',
                    'subject': '',
                    'keywords': '',
                    'producer': '',
                    'creator': '',
                    'creation_date': '',
                    'modification_date': '',
                    'page_count': len(pdf_reader.pages)
                }
                
                if pdf_reader.metadata:
                    info = pdf_reader.metadata
                    metadata.update({
                        'title': info.get('/Title', ''),
                        'author': info.get('/Author', ''),
                        'subject': info.get('/Subject', ''),
                        'keywords': info.get('/Keywords', ''),
                        'producer': info.get('/Producer', ''),
                        'creator': info.get('/Creator', ''),
                        'creation_date': info.get('/CreationDate', ''),
                        'modification_date': info.get('/ModDate', '')
                    })
                
                # 从文件名猜测信息
                if not metadata['title']:
                    metadata['title'] = self._guess_title_from_filename(file_path.name)
                
                return metadata
                
        except Exception as e:
            return {"error": f"PDF元数据提取失败: {str(e)}"}
    
    async def _extract_text_metadata(self, file_path: Path) -> Dict[str, Any]:
        """提取文本格式元数据"""
        try:
            # 检测文件编码
            with open(file_path, 'rb') as file:
                raw_data = file.read(10000)  # 读取前10KB用于编码检测
                encoding_result = chardet.detect(raw_data)
                encoding = encoding_result['encoding'] or 'utf-8'
            
            # 读取文件内容（限制大小）
            with open(file_path, 'r', encoding=encoding, errors='ignore') as file:
                content = file.read(5000)  # 只读取前5KB
            
            metadata = {
                'title': self._guess_title_from_filename(file_path.name),
                'encoding': encoding,
                'content_preview': content[:200] + '...' if len(content) > 200 else content,
                'word_count': len(content.split()),
                'character_count': len(content)
            }
            
            return metadata
            
        except Exception as e:
            return {"error": f"文本文件元数据提取失败: {str(e)}"}
    
    def _guess_title_from_filename(self, filename: str) -> str:
        """从文件名猜测书名"""
        filename = Path(filename).stem  # 移除扩展名
        
        # 常见的命名模式
        separators = [' - ', '_', '.']
        for sep in separators:
            if sep in filename:
                parts = filename.split(sep)
                if len(parts) >= 2:
                    # 通常作者在前，书名在后
                    return parts[-1].strip()
        
        # 移除常见的数字前缀
        import re
        filename = re.sub(r'^\d+\s*[-_\s]*', '', filename)
        
        return filename.strip()
    
    async def _analyze_ebook_content(self, file_path: Path) -> Dict[str, Any]:
        """分析电子书内容"""
        try:
            analysis_result = {
                'content_type': '',
                'genre': '',
                'reading_level': '',
                'estimated_reading_time': 0,
                'language_complexity': 0.0,
                'key_topics': []
            }
            
            # 基于文件格式和内容分析
            file_extension = file_path.suffix.lower()
            
            if file_extension == '.epub':
                analysis_result.update(await self._analyze_epub_content(file_path))
            elif file_extension == '.pdf':
                analysis_result.update(await self._analyze_pdf_content(file_path))
            elif file_extension in ['.txt', '.doc', '.docx']:
                analysis_result.update(await self._analyze_text_content(file_path))
            
            return analysis_result
            
        except Exception as e:
            return {"error": f"电子书内容分析失败: {str(e)}"}
    
    async def _analyze_epub_content(self, file_path: Path) -> Dict[str, Any]:
        """分析EPUB内容"""
        # 简化实现，实际需要解析EPUB内容
        return {
            'content_type': 'ebook',
            'genre': self._classify_genre_from_filename(file_path.name),
            'reading_level': 'general',
            'estimated_reading_time': 120,  # 分钟
            'language_complexity': 0.6
        }
    
    async def _analyze_pdf_content(self, file_path: Path) -> Dict[str, Any]:
        """分析PDF内容"""
        # 简化实现
        filename = file_path.name.lower()
        
        result = {
            'content_type': 'document',
            'genre': self._classify_genre_from_filename(filename),
            'reading_level': 'general',
            'estimated_reading_time': 60,
            'language_complexity': 0.7
        }
        
        # 基于文件名的内容类型判断
        if any(keyword in filename for keyword in ['manual', 'guide', 'tutorial']):
            result['content_type'] = 'manual'
        elif any(keyword in filename for keyword in ['report', 'paper', 'thesis']):
            result['content_type'] = 'academic'
        elif any(keyword in filename for keyword in ['novel', 'fiction', 'story']):
            result['content_type'] = 'fiction'
        
        return result
    
    async def _analyze_text_content(self, file_path: Path) -> Dict[str, Any]:
        """分析文本内容"""
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read(10000)  # 读取前10KB
            
            # 简单的文本分析
            words = content.split()
            sentences = content.split('.')
            
            result = {
                'content_type': 'text',
                'genre': self._classify_genre_from_filename(file_path.name),
                'reading_level': self._assess_reading_level(content),
                'estimated_reading_time': len(words) // 200,  # 假设200字/分钟
                'language_complexity': min(1.0, len(words) / 1000),
                'word_count': len(words),
                'sentence_count': len([s for s in sentences if s.strip()])
            }
            
            return result
            
        except Exception as e:
            return {"error": f"文本内容分析失败: {str(e)}"}
    
    def _classify_genre_from_filename(self, filename: str) -> str:
        """从文件名分类书籍类型"""
        filename_lower = filename.lower()
        
        genre_keywords = {
            'fiction': ['novel', 'fiction', 'story', '小说', '故事'],
            'science_fiction': ['scifi', 'science fiction', '科幻'],
            'fantasy': ['fantasy', '奇幻', '魔幻'],
            'mystery': ['mystery', 'thriller', '悬疑', '惊悚'],
            'romance': ['romance', 'love', '浪漫', '爱情'],
            'biography': ['biography', 'memoir', '传记', '自传'],
            'history': ['history', 'historical', '历史'],
            'science': ['science', 'scientific', '科学', '科技'],
            'business': ['business', 'finance', '经济', '商业'],
            'self_help': ['self help', 'self-help', '自助', '励志'],
            'academic': ['academic', 'research', '论文', '学术'],
            'technical': ['technical', 'manual', 'guide', '技术', '手册']
        }
        
        for genre, keywords in genre_keywords.items():
            if any(keyword in filename_lower for keyword in keywords):
                return genre
        
        return 'general'
    
    def _assess_reading_level(self, content: str) -> str:
        """评估阅读难度"""
        # 简单的评估逻辑
        words = content.split()
        if len(words) < 100:
            return 'easy'
        elif len(words) < 1000:
            return 'medium'
        else:
            return 'advanced'
    
    async def _enhance_with_ai(self, metadata: Dict[str, Any], analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """使用AI增强电子书分析"""
        enhanced = metadata.copy()
        enhanced.update(analysis_result)
        
        # 智能推荐相关书籍
        enhanced['similar_books'] = self._get_similar_books(enhanced)
        
        # 阅读进度跟踪
        enhanced['reading_progress'] = {
            'current_page': 0,
            'total_pages': enhanced.get('page_count', 0) or enhanced.get('estimated_pages', 0),
            'last_read': None,
            'bookmarks': []
        }
        
        # 智能标签
        enhanced['ai_tags'] = self._generate_ai_tags(enhanced)
        
        # 格式转换建议
        enhanced['conversion_suggestions'] = self._get_conversion_suggestions(enhanced)
        
        return enhanced
    
    def _get_similar_books(self, metadata: Dict[str, Any]) -> List[str]:
        """获取相似书籍推荐"""
        # 简化实现
        author = metadata.get('author', '')
        genre = metadata.get('genre', '')
        
        similar_books = []
        
        if author:
            similar_books.append(f"{author}的其他作品")
        
        if genre:
            similar_books.append(f"同类{genre}书籍")
        
        return similar_books
    
    def _generate_ai_tags(self, metadata: Dict[str, Any]) -> List[str]:
        """生成AI标签"""
        tags = []
        
        # 基于类型
        content_type = metadata.get('content_type', '')
        if content_type:
            tags.append(content_type)
        
        # 基于流派
        genre = metadata.get('genre', '')
        if genre:
            tags.append(genre)
        
        # 基于阅读难度
        reading_level = metadata.get('reading_level', '')
        if reading_level:
            tags.append(reading_level)
        
        # 基于格式
        file_format = metadata.get('format', '')
        if file_format:
            tags.append(file_format.replace('.', ''))
        
        return tags
    
    def _get_conversion_suggestions(self, metadata: Dict[str, Any]) -> List[str]:
        """获取格式转换建议"""
        current_format = metadata.get('format', '')
        suggestions = []
        
        if current_format == '.pdf':
            suggestions.append('转换为EPUB以获得更好的阅读体验')
        elif current_format == '.epub':
            suggestions.append('转换为PDF以便打印')
        elif current_format in ['.txt', '.doc', '.docx']:
            suggestions.append('转换为EPUB或PDF格式')
        
        return suggestions
    
    async def _update_ebook_database(self, metadata: Dict[str, Any]):
        """更新电子书数据库"""
        author = metadata.get('author')
        title = metadata.get('title')
        
        if author:
            if author not in self.author_database:
                self.author_database[author] = {
                    'books': [],
                    'genres': [],
                    'first_seen': str(asyncio.get_event_loop().time()),
                    'book_count': 0
                }
            
            self.author_database[author]['book_count'] += 1
            
            # 更新流派信息
            genre = metadata.get('genre')
            if genre and genre not in self.author_database[author]['genres']:
                self.author_database[author]['genres'].append(genre)
        
        if title:
            book_key = f"{author or '未知作者'} - {title}"
            if book_key not in self.book_database:
                self.book_database[book_key] = {
                    'author': author,
                    'title': title,
                    'genre': metadata.get('genre', ''),
                    'format': metadata.get('format', ''),
                    'file_path': metadata.get('file_path', ''),
                    'added_at': str(asyncio.get_event_loop().time())
                }
        
        self._save_ebook_database()
    
    async def create_library(self, name: str, books: List[str]) -> Dict[str, Any]:
        """创建电子书库"""
        library_id = f"library_{int(asyncio.get_event_loop().time())}"
        
        library = {
            'id': library_id,
            'name': name,
            'books': books,
            'created_at': str(asyncio.get_event_loop().time()),
            'book_count': len(books),
            'cover_book': books[0] if books else None
        }
        
        self.library_database[library_id] = library
        self._save_ebook_database()
        
        return library
    
    async def search_ebooks(self, query: str, search_type: str = "all") -> Dict[str, Any]:
        """搜索电子书"""
        results = {
            'by_title': [],
            'by_author': [],
            'by_genre': []
        }
        
        query_lower = query.lower()
        
        # 搜索书名
        if search_type in ['all', 'title']:
            for book_key, book in self.book_database.items():
                if query_lower in book['title'].lower():
                    results['by_title'].append(book)
        
        # 搜索作者
        if search_type in ['all', 'author']:
            for author, info in self.author_database.items():
                if query_lower in author.lower():
                    results['by_author'].append({
                        'author': author,
                        'book_count': info['book_count'],
                        'genres': info['genres']
                    })
        
        return results


# 使用示例
async def demo_ebook_manager():
    """演示电子书管理器功能"""
    manager = EbookManager()
    
    # 分析电子书文件
    result = await manager.analyze_ebook_file("example_book.epub")
    print("电子书分析结果:", json.dumps(result, indent=2, ensure_ascii=False))
    
    # 搜索电子书
    search_results = await manager.search_ebooks("小说")
    print("\n搜索结果:", json.dumps(search_results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(demo_ebook_manager())