"""
GraphQL Schema定义
集成MoviePilot规则的GraphQL + REST双接口支持
"""

import strawberry
from typing import List, Optional, Dict, Any
from datetime import datetime
from strawberry.fastapi import GraphQLRouter

from .site_bundle_manager import SiteBundle
from .hnr_detector import HNRDetectionResult
from .qbittorrent_integration import TorrentInfo, TorrentState


@strawberry.type(description="站点包信息")
class SiteBundleType:
    id: str
    name: str
    description: Optional[str]
    selectors: List[str]
    site_overrides: Dict[str, Any]
    version: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, bundle: SiteBundle):
        return cls(
            id=bundle.id,
            name=bundle.name,
            description=bundle.description,
            selectors=bundle.selectors,
            site_overrides=bundle.site_overrides,
            version=bundle.version,
            created_at=bundle.created_at,
            updated_at=bundle.updated_at,
        )


@strawberry.type(description="HNR检测结果")
class HNRDetectionResultType:
    has_hnr: bool
    confidence: float
    matched_rules: List[str]
    risk_level: str
    suggestions: List[str]

    @classmethod
    def from_model(cls, result: HNRDetectionResult):
        return cls(
            has_hnr=result.has_hnr,
            confidence=result.confidence,
            matched_rules=result.matched_rules,
            risk_level=result.risk_level,
            suggestions=result.suggestions,
        )


@strawberry.enum(description="种子状态枚举")
class TorrentStateType:
    DOWNLOADING = "downloading"
    SEEDING = "seeding"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@strawberry.type(description="种子信息")
class TorrentInfoType:
    hash: str
    name: str
    size: int
    progress: float
    state: TorrentStateType
    download_speed: int
    upload_speed: int
    ratio: float
    eta: int
    added_on: datetime
    tags: List[str]
    category: str
    save_path: str

    @classmethod
    def from_model(cls, torrent: TorrentInfo):
        return cls(
            hash=torrent.hash,
            name=torrent.name,
            size=torrent.size,
            progress=torrent.progress,
            state=TorrentStateType(torrent.state.value),
            download_speed=torrent.download_speed,
            upload_speed=torrent.upload_speed,
            ratio=torrent.ratio,
            eta=torrent.eta,
            added_on=torrent.added_on,
            tags=torrent.tags,
            category=torrent.category,
            save_path=torrent.save_path,
        )


@strawberry.input(description="站点包创建输入")
class SiteBundleCreateInput:
    name: str
    description: Optional[str] = None
    selectors: List[str]
    site_overrides: Optional[Dict[str, Any]] = None
    version: str = "1.0.0"


@strawberry.input(description="站点包更新输入")
class SiteBundleUpdateInput:
    name: Optional[str] = None
    description: Optional[str] = None
    selectors: Optional[List[str]] = None
    site_overrides: Optional[Dict[str, Any]] = None
    version: Optional[str] = None


@strawberry.input(description="HNR检测输入")
class HNRDetectionInput:
    content: str
    site_name: Optional[str] = None


@strawberry.type(description="查询根类型")
class Query:
    @strawberry.field(description="获取所有站点包")
    async def site_bundles(self) -> List[SiteBundleType]:
        from .site_bundle_manager import site_bundle_manager

        bundles = site_bundle_manager.get_all_bundles()
        return [SiteBundleType.from_model(bundle) for bundle in bundles]

    @strawberry.field(description="根据ID获取站点包")
    async def site_bundle(self, id: str) -> Optional[SiteBundleType]:
        from .site_bundle_manager import site_bundle_manager

        bundle = site_bundle_manager.get_bundle(id)
        if bundle:
            return SiteBundleType.from_model(bundle)
        return None

    @strawberry.field(description="检测HNR风险")
    async def detect_hnr(self, input: HNRDetectionInput) -> HNRDetectionResultType:
        from .hnr_detector import hnr_detector

        result = hnr_detector.detect_hnr(input.content, input.site_name)
        return HNRDetectionResultType.from_model(result)

    @strawberry.field(description="获取种子列表")
    async def torrents(
        self, hashes: Optional[List[str]] = None
    ) -> List[TorrentInfoType]:
        from .qbittorrent_integration import QBittorrentIntegration

        async with QBittorrentIntegration() as qb:
            torrents = await qb.get_torrents(hashes)
            return [TorrentInfoType.from_model(torrent) for torrent in torrents]


@strawberry.type(description="变更根类型")
class Mutation:
    @strawberry.mutation(description="创建站点包")
    async def create_site_bundle(self, input: SiteBundleCreateInput) -> SiteBundleType:
        from .site_bundle_manager import SiteBundle, site_bundle_manager

        bundle = SiteBundle(
            id=f"bundle_{len(site_bundle_manager.bundles) + 1}",
            name=input.name,
            description=input.description,
            selectors=input.selectors,
            site_overrides=input.site_overrides or {},
            version=input.version,
        )

        result = site_bundle_manager.create_bundle(bundle)
        return SiteBundleType.from_model(result)

    @strawberry.mutation(description="更新站点包")
    async def update_site_bundle(
        self, id: str, input: SiteBundleUpdateInput
    ) -> SiteBundleType:
        from .site_bundle_manager import site_bundle_manager

        update_data = {}
        if input.name is not None:
            update_data["name"] = input.name
        if input.description is not None:
            update_data["description"] = input.description
        if input.selectors is not None:
            update_data["selectors"] = input.selectors
        if input.site_overrides is not None:
            update_data["site_overrides"] = input.site_overrides
        if input.version is not None:
            update_data["version"] = input.version

        result = site_bundle_manager.update_bundle(id, update_data)
        return SiteBundleType.from_model(result)

    @strawberry.mutation(description="删除站点包")
    async def delete_site_bundle(self, id: str) -> bool:
        from .site_bundle_manager import site_bundle_manager

        existing_bundle = site_bundle_manager.get_bundle(id)
        if not existing_bundle:
            return False

        site_bundle_manager.delete_bundle(id)
        return True

    @strawberry.mutation(description="添加种子")
    async def add_torrent(
        self,
        torrent_url: Optional[str] = None,
        save_path: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        paused: bool = False,
    ) -> bool:
        from .qbittorrent_integration import QBittorrentIntegration

        async with QBittorrentIntegration() as qb:
            return await qb.add_torrent(
                torrent_url=torrent_url,
                save_path=save_path,
                category=category,
                tags=tags,
                paused=paused,
            )

    @strawberry.mutation(description="设置种子标签")
    async def set_torrent_tags(self, hashes: List[str], tags: List[str]) -> bool:
        from .qbittorrent_integration import QBittorrentIntegration

        async with QBittorrentIntegration() as qb:
            return await qb.set_torrent_tags(hashes, tags)

    @strawberry.mutation(description="暂停种子")
    async def pause_torrents(self, hashes: List[str]) -> bool:
        from .qbittorrent_integration import QBittorrentIntegration

        async with QBittorrentIntegration() as qb:
            return await qb.pause_torrents(hashes)

    @strawberry.mutation(description="恢复种子")
    async def resume_torrents(self, hashes: List[str]) -> bool:
        from .qbittorrent_integration import QBittorrentIntegration

        async with QBittorrentIntegration() as qb:
            return await qb.resume_torrents(hashes)


# 创建GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)

# 创建GraphQL路由
graphql_app = GraphQLRouter(schema)
