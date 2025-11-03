"""
HNR检测器 - 智能检测和阻止H&R/H3/H5等PT规则
"""

import re
import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class HNRVerdict(Enum):
    """HNR检测结果"""
    PASS = "pass"  # 通过
    SUSPECTED = "suspected"  # 疑似
    BLOCKED = "blocked"  # 阻止


@dataclass
class HNRDetectionResult:
    """HNR检测结果"""
    verdict: HNRVerdict
    confidence: float
    matched_rules: List[str]
    category: str
    penalties: Dict[str, Any]
    message: str


class HNRDetector:
    """HNR检测器"""
    
    def __init__(self, signature_pack_path: Optional[str] = None):
        self.signatures = {}
        self.site_overrides = {}
        self.version = 0
        
        if signature_pack_path:
            self.load_signatures(signature_pack_path)
    
    def load_signatures(self, signature_pack_path: str) -> bool:
        """加载签名包"""
        try:
            with open(signature_pack_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            self.version = data.get('version', 0)
            self.signatures = {sig['id']: sig for sig in data.get('signatures', [])}
            self.site_overrides = data.get('site_overrides', {})
            
            logger.info(f"加载HNR签名包 v{self.version}, 包含 {len(self.signatures)} 个签名")
            return True
            
        except Exception as e:
            logger.error(f"加载HNR签名包失败: {e}")
            return False
    
    def detect(self, 
               title: str,
               subtitle: str = "",
               badges_text: str = "",
               list_html: str = "",
               site_id: str = "default") -> HNRDetectionResult:
        """检测HNR风险"""
        
        # 合并所有文本内容
        combined_text = f"{title} {subtitle} {badges_text}".lower()
        
        # 应用站点特定规则
        site_rules = self.site_overrides.get(site_id, {})
        
        # 检测逻辑
        matched_rules = []
        confidence = 0.0
        category = ""
        penalties = {}
        
        # 精确匹配检测
        for sig_id, signature in self.signatures.items():
            if self._match_signature(signature, combined_text, list_html, site_rules):
                matched_rules.append(sig_id)
                confidence = max(confidence, signature.get('confidence', 0.8))
                category = signature.get('category', 'HNR')
                penalties = signature.get('penalties', {})
        
        # 启发式检测
        if not matched_rules:
            heuristic_result = self._heuristic_detection(combined_text)
            if heuristic_result:
                matched_rules.append("heuristic")
                confidence = heuristic_result['confidence']
                category = heuristic_result['category']
                penalties = heuristic_result.get('penalties', {})
        
        # 确定结果
        if confidence >= 0.8:
            verdict = HNRVerdict.BLOCKED
            message = f"检测到HNR风险: {', '.join(matched_rules)}"
        elif confidence >= 0.3:
            verdict = HNRVerdict.SUSPECTED
            message = f"疑似HNR风险: {', '.join(matched_rules)}"
        else:
            verdict = HNRVerdict.PASS
            message = "无HNR风险"
        
        return HNRDetectionResult(
            verdict=verdict,
            confidence=confidence,
            matched_rules=matched_rules,
            category=category,
            penalties=penalties,
            message=message
        )
    
    def _match_signature(self, 
                        signature: Dict[str, Any], 
                        text: str, 
                        html: str,
                        site_rules: Dict[str, Any]) -> bool:
        """匹配签名规则"""
        
        # 检查文本模式
        patterns = signature.get('patterns', {})
        
        # 精确文本匹配
        for pattern in patterns.get('text', []):
            if pattern.lower() in text:
                return True
        
        # 正则表达式匹配
        for regex_pattern in patterns.get('regex', []):
            if re.search(regex_pattern, text, re.IGNORECASE):
                return True
        
        # HTML选择器匹配（如果提供了HTML）
        if html and 'selectors' in site_rules:
            for selector in site_rules['selectors']:
                # 简化的选择器匹配逻辑
                if selector.lower() in html.lower():
                    return True
        
        return False
    
    def _heuristic_detection(self, text: str) -> Optional[Dict[str, Any]]:
        """启发式检测"""
        
        # H-数字模式检测（避免H.264/HDR10误识别）
        h_patterns = [
            (r'\bH[\s\-/:：]?([1-9]|10)\b', 0.7),  # H3, H-5, H/10等
            (r'\bH[\s\-/:：]?R\b', 0.9),  # H&R, H-R等
        ]
        
        for pattern, conf in h_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # 避免误识别
                if not self._is_false_positive(text):
                    return {
                        'confidence': conf,
                        'category': 'HNR_HEURISTIC',
                        'penalties': {'base': -30, 'per_level': -5}
                    }
        
        # 关键词组合检测
        keywords_sets = [
            (['考核', '小时'], 0.6),
            (['命中', '做种'], 0.7),
            (['强制', '保种'], 0.8),
        ]
        
        for keywords, conf in keywords_sets:
            if all(keyword in text for keyword in keywords):
                return {
                    'confidence': conf,
                    'category': 'HNR_KEYWORDS',
                    'penalties': {'base': -20, 'per_level': -3}
                }
        
        return None
    
    def _is_false_positive(self, text: str) -> bool:
        """检查是否为误识别"""
        false_positive_patterns = [
            r'H\.?26[45]',  # H.264, H265
            r'HDR10',       # HDR10
            r'H\.?26[45]',  # H.264, H265
        ]
        
        for pattern in false_positive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def reload_signatures(self, signature_pack_path: str) -> bool:
        """重新加载签名包"""
        return self.load_signatures(signature_pack_path)
    
    def get_signature_info(self) -> Dict[str, Any]:
        """获取签名包信息"""
        return {
            'version': self.version,
            'signature_count': len(self.signatures),
            'site_count': len(self.site_overrides)
        }


# 全局HNR检测器实例
hnr_detector = HNRDetector()