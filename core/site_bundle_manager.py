"""
站点包管理器 - 管理站点配置和选择器规则
"""

import json
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class SiteBundleStatus(Enum):
    """站点包状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


@dataclass
class SiteBundle:
    """站点包定义"""

    id: str
    name: str
    selectors: List[str]
    meta: Dict[str, Any]
    status: SiteBundleStatus = SiteBundleStatus.ACTIVE
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "selectors": self.selectors,
            "meta": self.meta,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class SiteBundleManager:
    """站点包管理器"""

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or "data/site_bundles")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.bundles: Dict[str, SiteBundle] = {}
        self.load_bundles()

    def load_bundles(self) -> bool:
        """加载所有站点包"""
        try:
            bundle_files = list(self.storage_path.glob("*.json"))

            for bundle_file in bundle_files:
                try:
                    with open(bundle_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    bundle = SiteBundle(
                        id=data["id"],
                        name=data["name"],
                        selectors=data["selectors"],
                        meta=data.get("meta", {}),
                        status=SiteBundleStatus(data.get("status", "active")),
                        created_at=data.get("created_at"),
                        updated_at=data.get("updated_at"),
                    )

                    self.bundles[bundle.id] = bundle

                except Exception as e:
                    logger.error(f"加载站点包失败 {bundle_file}: {e}")

            logger.info(f"加载 {len(self.bundles)} 个站点包")
            return True

        except Exception as e:
            logger.error(f"加载站点包失败: {e}")
            return False

    def save_bundle(self, bundle: SiteBundle) -> bool:
        """保存站点包"""
        try:
            bundle_file = self.storage_path / f"{bundle.id}.json"

            with open(bundle_file, "w", encoding="utf-8") as f:
                json.dump(bundle.to_dict(), f, ensure_ascii=False, indent=2)

            self.bundles[bundle.id] = bundle
            return True

        except Exception as e:
            logger.error(f"保存站点包失败 {bundle.id}: {e}")
            return False

    def create_bundle(
        self, name: str, selectors: List[str], meta: Optional[Dict[str, Any]] = None
    ) -> Optional[SiteBundle]:
        """创建新站点包"""
        try:
            bundle_id = str(uuid.uuid4())

            bundle = SiteBundle(
                id=bundle_id,
                name=name,
                selectors=selectors,
                meta=meta or {},
                created_at=self._get_current_timestamp(),
                updated_at=self._get_current_timestamp(),
            )

            if self.save_bundle(bundle):
                logger.info(f"创建站点包: {bundle_id} - {name}")
                return bundle
            else:
                return None

        except Exception as e:
            logger.error(f"创建站点包失败: {e}")
            return None

    def update_bundle(
        self,
        bundle_id: str,
        name: Optional[str] = None,
        selectors: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Optional[SiteBundle]:
        """更新站点包"""
        try:
            if bundle_id not in self.bundles:
                return None

            bundle = self.bundles[bundle_id]

            if name is not None:
                bundle.name = name

            if selectors is not None:
                bundle.selectors = selectors

            if meta is not None:
                bundle.meta = meta

            bundle.updated_at = self._get_current_timestamp()

            if self.save_bundle(bundle):
                logger.info(f"更新站点包: {bundle_id}")
                return bundle
            else:
                return None

        except Exception as e:
            logger.error(f"更新站点包失败 {bundle_id}: {e}")
            return None

    def delete_bundle(self, bundle_id: str) -> bool:
        """删除站点包"""
        try:
            if bundle_id not in self.bundles:
                return False

            bundle_file = self.storage_path / f"{bundle_id}.json"

            if bundle_file.exists():
                bundle_file.unlink()

            del self.bundles[bundle_id]

            logger.info(f"删除站点包: {bundle_id}")
            return True

        except Exception as e:
            logger.error(f"删除站点包失败 {bundle_id}: {e}")
            return False

    def get_bundle(self, bundle_id: str) -> Optional[SiteBundle]:
        """获取站点包"""
        return self.bundles.get(bundle_id)

    def list_bundles(
        self, status_filter: Optional[SiteBundleStatus] = None
    ) -> List[SiteBundle]:
        """列出站点包"""
        bundles = list(self.bundles.values())

        if status_filter:
            bundles = [b for b in bundles if b.status == status_filter]

        return sorted(bundles, key=lambda b: b.name)

    def bulk_upsert_bundles(self, bundles_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量创建或更新站点包"""
        results = {"created": 0, "updated": 0, "errors": 0, "details": []}

        for bundle_data in bundles_data:
            try:
                bundle_id = bundle_data.get("id")

                if bundle_id and bundle_id in self.bundles:
                    # 更新现有站点包
                    bundle = self.update_bundle(
                        bundle_id=bundle_id,
                        name=bundle_data.get("name"),
                        selectors=bundle_data.get("selectors", []),
                        meta=bundle_data.get("meta", {}),
                    )

                    if bundle:
                        results["updated"] += 1
                        results["details"].append(
                            {"id": bundle_id, "action": "updated", "success": True}
                        )
                    else:
                        results["errors"] += 1
                        results["details"].append(
                            {
                                "id": bundle_id,
                                "action": "update",
                                "success": False,
                                "error": "更新失败",
                            }
                        )
                else:
                    # 创建新站点包
                    bundle = self.create_bundle(
                        name=bundle_data["name"],
                        selectors=bundle_data.get("selectors", []),
                        meta=bundle_data.get("meta", {}),
                    )

                    if bundle:
                        results["created"] += 1
                        results["details"].append(
                            {"id": bundle.id, "action": "created", "success": True}
                        )
                    else:
                        results["errors"] += 1
                        results["details"].append(
                            {
                                "id": bundle_id or "unknown",
                                "action": "create",
                                "success": False,
                                "error": "创建失败",
                            }
                        )

            except Exception as e:
                results["errors"] += 1
                results["details"].append(
                    {
                        "id": bundle_data.get("id", "unknown"),
                        "action": "process",
                        "success": False,
                        "error": str(e),
                    }
                )

        return results

    def import_from_file(self, file_path: str, format: str = "json") -> Dict[str, Any]:
        """从文件导入站点包"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if format.lower() == "yaml" or file_path.endswith((".yaml", ".yml")):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            # 支持多种格式
            if isinstance(data, list):
                bundles_data = data
            elif isinstance(data, dict) and "bundles" in data:
                bundles_data = data["bundles"]
            else:
                return {"success": False, "error": "文件格式不支持"}

            return self.bulk_upsert_bundles(bundles_data)

        except Exception as e:
            logger.error(f"导入站点包失败: {e}")
            return {"success": False, "error": str(e)}

    def export_to_file(self, file_path: str, format: str = "json") -> bool:
        """导出站点包到文件"""
        try:
            bundles_data = {
                "bundles": [bundle.to_dict() for bundle in self.bundles.values()]
            }

            with open(file_path, "w", encoding="utf-8") as f:
                if format.lower() == "yaml" or file_path.endswith((".yaml", ".yml")):
                    yaml.dump(bundles_data, f, allow_unicode=True, indent=2)
                else:
                    json.dump(bundles_data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            logger.error(f"导出站点包失败: {e}")
            return False

    def validate_bundle(self, bundle_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证站点包数据"""
        errors = []

        # 必需字段检查
        if not bundle_data.get("name"):
            errors.append("name字段不能为空")

        if not bundle_data.get("selectors"):
            errors.append("selectors字段不能为空")

        # 字段类型检查
        if not isinstance(bundle_data.get("selectors", []), list):
            errors.append("selectors必须是列表")

        if not isinstance(bundle_data.get("meta", {}), dict):
            errors.append("meta必须是字典")

        return {"valid": len(errors) == 0, "errors": errors}

    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime

        return datetime.now().isoformat()


# 全局站点包管理器实例
site_bundle_manager = SiteBundleManager()
