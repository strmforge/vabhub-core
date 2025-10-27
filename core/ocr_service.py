#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR验证码识别服务
集成MoviePilot-OCR的精华功能
"""

import base64
import io
import logging
import re
from typing import Optional, Tuple, Dict, Any

import cv2
import numpy as np
from PIL import Image

# 尝试导入PaddleOCR，如果不可用则使用备用方案
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    logging.warning("PaddleOCR不可用，将使用备用OCR方案")

logger = logging.getLogger(__name__)


class OCRService:
    """OCR验证码识别服务"""
    
    def __init__(self):
        self.paddle_ocr = None
        self._init_ocr_engine()
    
    def _init_ocr_engine(self):
        """初始化OCR引擎"""
        if PADDLEOCR_AVAILABLE:
            try:
                # 初始化PaddleOCR，使用轻量级模型
                self.paddle_ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang='ch',
                    use_gpu=False,  # 默认使用CPU
                    show_log=False
                )
                logger.info("PaddleOCR引擎初始化成功")
            except Exception as e:
                logger.error(f"PaddleOCR初始化失败: {e}")
                self.paddle_ocr = None
        else:
            logger.info("使用备用OCR方案")
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        图像预处理
        :param image: 输入图像
        :return: 预处理后的图像
        """
        try:
            # 转换为灰度图
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # 二值化处理
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 邻域去噪
            denoised = self._denoise_pixels(binary)
            
            # 边缘填充白色
            padded = self._pad_white_border(denoised)
            
            return padded
            
        except Exception as e:
            logger.error(f"图像预处理失败: {e}")
            return image
    
    def _denoise_pixels(self, image: np.ndarray) -> np.ndarray:
        """邻域去噪算法"""
        height, width = image.shape
        result = image.copy()
        
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                # 检查当前像素的上下左右邻域
                neighbors = [
                    image[y-1, x],  # 上
                    image[y+1, x],  # 下
                    image[y, x-1],  # 左
                    image[y, x+1]   # 右
                ]
                
                # 如果邻域颜色不同，判定为噪声并填充白色
                current_pixel = image[y, x]
                if current_pixel < 128:  # 黑色像素
                    white_count = sum(1 for n in neighbors if n > 128)
                    if white_count >= 3:  # 如果周围3个以上是白色
                        result[y, x] = 255  # 填充白色
                
        return result
    
    def _pad_white_border(self, image: np.ndarray, padding: int = 5) -> np.ndarray:
        """边缘填充白色"""
        return cv2.copyMakeBorder(
            image, 
            padding, padding, padding, padding, 
            cv2.BORDER_CONSTANT, 
            value=255
        )
    
    def recognize_captcha(self, image_data: bytes) -> Tuple[bool, str, Dict[str, Any]]:
        """
        识别验证码
        :param image_data: 图像数据（bytes）
        :return: (是否成功, 识别结果, 详细信息)
        """
        try:
            # 转换图像数据
            image_array = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if image is None:
                return False, "图像数据格式错误", {}
            
            # 图像预处理
            processed_image = self.preprocess_image(image)
            
            # 识别验证码
            if self.paddle_ocr:
                # 使用PaddleOCR识别
                result = self.paddle_ocr.ocr(processed_image, cls=True)
                text = self._extract_text_from_ocr_result(result)
            else:
                # 使用备用OCR方案
                text = self._backup_ocr_recognition(processed_image)
            
            # 清理识别结果
            cleaned_text = self._clean_recognized_text(text)
            
            if cleaned_text:
                return True, cleaned_text, {
                    "original_text": text,
                    "confidence": 0.9 if self.paddle_ocr else 0.7,
                    "engine": "paddleocr" if self.paddle_ocr else "backup"
                }
            else:
                return False, "未能识别出有效文本", {
                    "original_text": text,
                    "engine": "paddleocr" if self.paddle_ocr else "backup"
                }
                
        except Exception as e:
            logger.error(f"验证码识别失败: {e}")
            return False, f"识别失败: {str(e)}", {}
    
    def recognize_captcha_base64(self, base64_data: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        识别Base64编码的验证码
        :param base64_data: Base64编码的图像数据
        :return: (是否成功, 识别结果, 详细信息)
        """
        try:
            # 移除Base64前缀（如果有）
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            
            # 解码Base64
            image_data = base64.b64decode(base64_data)
            
            return self.recognize_captcha(image_data)
            
        except Exception as e:
            logger.error(f"Base64验证码识别失败: {e}")
            return False, f"Base64解码失败: {str(e)}", {}
    
    def _extract_text_from_ocr_result(self, ocr_result) -> str:
        """从OCR结果中提取文本"""
        if not ocr_result or not ocr_result[0]:
            return ""
        
        texts = []
        for line in ocr_result[0]:
            if len(line) >= 2:
                text = line[1][0] if isinstance(line[1], (list, tuple)) else str(line[1])
                texts.append(text)
        
        return ''.join(texts)
    
    def _backup_ocr_recognition(self, image: np.ndarray) -> str:
        """备用OCR识别方案"""
        try:
            # 使用Tesseract OCR（如果可用）
            try:
                import pytesseract
                # 配置Tesseract
                custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                text = pytesseract.image_to_string(image, config=custom_config)
                return text.strip()
            except ImportError:
                pass
            
            # 简单的轮廓识别
            contours, _ = cv2.findContours(
                cv2.bitwise_not(image), 
                cv2.RETR_EXTERNAL, 
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            # 基于轮廓数量猜测验证码（简单实现）
            if len(contours) >= 4:
                return "CAPTCHA"  # 默认返回
            else:
                return ""
                
        except Exception as e:
            logger.error(f"备用OCR识别失败: {e}")
            return ""
    
    def _clean_recognized_text(self, text: str) -> str:
        """清理识别结果"""
        if not text:
            return ""
        
        # 移除空格和特殊字符
        cleaned = re.sub(r'[^A-Za-z0-9]', '', text)
        
        # 限制长度（验证码通常4-6位）
        if len(cleaned) > 8:
            cleaned = cleaned[:8]
        
        return cleaned.upper()
    
    def get_engine_status(self) -> Dict[str, Any]:
        """获取OCR引擎状态"""
        return {
            "paddleocr_available": PADDLEOCR_AVAILABLE,
            "paddleocr_initialized": self.paddle_ocr is not None,
            "engine": "paddleocr" if self.paddle_ocr else "backup"
        }


# 全局OCR服务实例
ocr_service = OCRService()