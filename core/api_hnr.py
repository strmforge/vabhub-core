"""
HNR检测API路由模块
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from .hnr_detector import hnr_detector, HNRVerdict, HNRDetectionResult
from .auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hnr", tags=["HNR Detection"])


class HNRDetectionRequest(BaseModel):
    """HNR检测请求"""

    title: str
    subtitle: Optional[str] = ""
    badges_text: Optional[str] = ""
    list_html: Optional[str] = ""
    site_id: Optional[str] = "default"


class HNRDetectionResponse(BaseModel):
    """HNR检测响应"""

    verdict: str
    confidence: float
    matched_rules: List[str]
    category: str
    penalties: Dict[str, Any]
    message: str
    signature_info: Dict[str, Any]


class SignatureReloadRequest(BaseModel):
    """签名包重载请求"""

    signature_pack_path: str


class SignatureReloadResponse(BaseModel):
    """签名包重载响应"""

    success: bool
    message: str
    signature_info: Dict[str, Any]


@router.post("/detect", response_model=HNRDetectionResponse)
async def detect_hnr(
    request: HNRDetectionRequest, current_user: dict = Depends(get_current_user)
):
    """检测HNR风险"""
    try:
        result = hnr_detector.detect(
            title=request.title,
            subtitle=request.subtitle or "",
            badges_text=request.badges_text or "",
            list_html=request.list_html or "",
            site_id=request.site_id or "default",
        )

        signature_info = hnr_detector.get_signature_info()

        return HNRDetectionResponse(
            verdict=result.verdict.value,
            confidence=result.confidence,
            matched_rules=result.matched_rules,
            category=result.category,
            penalties=result.penalties,
            message=result.message,
            signature_info=signature_info,
        )

    except Exception as e:
        logger.error(f"HNR检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"HNR检测失败: {str(e)}")


@router.post("/signatures/reload", response_model=SignatureReloadResponse)
async def reload_signatures(
    request: SignatureReloadRequest,
    x_api_key: Optional[str] = Header(None),
    current_user: dict = Depends(get_current_user),
):
    """重载签名包"""
    try:
        # 检查API密钥（可选）
        if x_api_key:
            # 这里可以添加API密钥验证逻辑
            pass

        success = hnr_detector.reload_signatures(request.signature_pack_path)

        if success:
            signature_info = hnr_detector.get_signature_info()
            return SignatureReloadResponse(
                success=True, message="签名包重载成功", signature_info=signature_info
            )
        else:
            raise HTTPException(status_code=400, detail="签名包重载失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"签名包重载失败: {e}")
        raise HTTPException(status_code=500, detail=f"签名包重载失败: {str(e)}")


@router.get("/signatures/info", response_model=Dict[str, Any])
async def get_signature_info(current_user: dict = Depends(get_current_user)):
    """获取签名包信息"""
    try:
        return hnr_detector.get_signature_info()

    except Exception as e:
        logger.error(f"获取签名包信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取签名包信息失败: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """健康检查"""
    try:
        signature_info = hnr_detector.get_signature_info()
        return {"status": "healthy", "signature_info": signature_info}

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {"status": "unhealthy", "error": str(e)}


# 批量检测接口
class BatchHNRDetectionRequest(BaseModel):
    """批量HNR检测请求"""

    candidates: List[HNRDetectionRequest]


class BatchHNRDetectionResponse(BaseModel):
    """批量HNR检测响应"""

    results: List[HNRDetectionResponse]
    summary: Dict[str, Any]


@router.post("/detect/batch", response_model=BatchHNRDetectionResponse)
async def batch_detect_hnr(
    request: BatchHNRDetectionRequest, current_user: dict = Depends(get_current_user)
):
    """批量检测HNR风险"""
    try:
        results = []
        blocked_count = 0
        suspected_count = 0
        passed_count = 0

        for candidate in request.candidates:
            result = hnr_detector.detect(
                title=candidate.title,
                subtitle=candidate.subtitle or "",
                badges_text=candidate.badges_text or "",
                list_html=candidate.list_html or "",
                site_id=candidate.site_id or "default",
            )

            signature_info = hnr_detector.get_signature_info()

            response = HNRDetectionResponse(
                verdict=result.verdict.value,
                confidence=result.confidence,
                matched_rules=result.matched_rules,
                category=result.category,
                penalties=result.penalties,
                message=result.message,
                signature_info=signature_info,
            )

            results.append(response)

            # 统计
            if result.verdict == HNRVerdict.BLOCKED:
                blocked_count += 1
            elif result.verdict == HNRVerdict.SUSPECTED:
                suspected_count += 1
            else:
                passed_count += 1

        summary = {
            "total": len(request.candidates),
            "blocked": blocked_count,
            "suspected": suspected_count,
            "passed": passed_count,
            "blocked_percentage": (
                blocked_count / len(request.candidates) * 100
                if request.candidates
                else 0
            ),
        }

        return BatchHNRDetectionResponse(results=results, summary=summary)

    except Exception as e:
        logger.error(f"批量HNR检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量HNR检测失败: {str(e)}")
