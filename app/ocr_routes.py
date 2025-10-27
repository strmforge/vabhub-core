#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR验证码识别API路由
提供验证码识别功能接口
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from core.ocr_service import ocr_service

router = APIRouter()


class OCRRecognizeRequest(BaseModel):
    """OCR识别请求模型"""
    base64_data: str


class OCRRecognizeResponse(BaseModel):
    """OCR识别响应模型"""
    success: bool
    result: str
    message: str
    details: Dict[str, Any]


@router.post("/ocr/recognize", response_model=OCRRecognizeResponse)
async def recognize_captcha(request: OCRRecognizeRequest):
    """
    识别Base64编码的验证码
    """
    try:
        success, result, details = ocr_service.recognize_captcha_base64(
            request.base64_data
        )
        
        return OCRRecognizeResponse(
            success=success,
            result=result,
            message="识别成功" if success else "识别失败",
            details=details
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"识别失败: {str(e)}")


@router.post("/ocr/recognize/file", response_model=OCRRecognizeResponse)
async def recognize_captcha_file(file: UploadFile = File(...)):
    """
    通过文件上传识别验证码
    """
    try:
        # 读取文件内容
        image_data = await file.read()
        
        if not image_data:
            raise HTTPException(status_code=400, detail="文件内容为空")
        
        success, result, details = ocr_service.recognize_captcha(image_data)
        
        return OCRRecognizeResponse(
            success=success,
            result=result,
            message="识别成功" if success else "识别失败",
            details=details
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"识别失败: {str(e)}")


@router.get("/ocr/status")
async def get_ocr_status():
    """
    获取OCR服务状态
    """
    try:
        status = ocr_service.get_engine_status()
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/ocr/test")
async def test_ocr_connection():
    """
    测试OCR服务连接
    """
    try:
        # 创建一个简单的测试图像
        import numpy as np
        
        # 创建一个简单的验证码图像（4位数字）
        test_image = np.ones((50, 150, 3), dtype=np.uint8) * 255
        cv2.putText(test_image, "1234", (30, 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        # 转换为bytes
        _, buffer = cv2.imencode('.png', test_image)
        image_data = buffer.tobytes()
        
        success, result, details = ocr_service.recognize_captcha(image_data)
        
        return {
            "success": True,
            "test_result": {
                "recognized": result,
                "expected": "1234",
                "match": result == "1234",
                "details": details
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")


@router.post("/ocr/preprocess")
async def preprocess_image(file: UploadFile = File(...)):
    """
    图像预处理（用于调试）
    """
    try:
        import base64
        import cv2
        import numpy as np
        
        # 读取文件内容
        image_data = await file.read()
        
        # 转换图像数据
        image_array = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="图像数据格式错误")
        
        # 预处理图像
        processed_image = ocr_service.preprocess_image(image)
        
        # 转换为Base64返回
        _, buffer = cv2.imencode('.png', processed_image)
        processed_base64 = base64.b64encode(buffer).decode()
        
        # 原始图像也转换为Base64
        _, orig_buffer = cv2.imencode('.png', image)
        original_base64 = base64.b64encode(orig_buffer).decode()
        
        return {
            "success": True,
            "original": f"data:image/png;base64,{original_base64}",
            "processed": f"data:image/png;base64,{processed_base64}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预处理失败: {str(e)}")