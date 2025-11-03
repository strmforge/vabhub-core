"""
RSS API路由模块
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any

from .rss_engine import RSSManager, RSSRule, RSSItem

# from .auth import get_current_user  # Commented out for now

router = APIRouter(prefix="/rss", tags=["RSS"])

# 全局RSS管理器
rss_manager = RSSManager()


@router.post("/feeds", response_model=Dict[str, Any])
async def add_feed(
    name: str,
    url: str,
    interval: int = 3600,
    # current_user: dict = Depends(get_current_user)  # 暂时注释掉认证
):
    """添加RSS源"""
    try:
        rss_manager.add_feed(name, url, interval)
        return {"message": f"RSS feed '{name}' added successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/feeds", response_model=List[Dict[str, Any]])
async def get_feeds():
    """获取所有RSS源"""
    return [{"name": name, **info} for name, info in rss_manager.feeds.items()]


@router.post("/rules", response_model=Dict[str, Any])
async def add_rule(
    rule: RSSRule,
    # current_user: dict = Depends(get_current_user)  # 暂时注释掉认证
):
    """添加RSS规则"""
    try:
        rss_manager.add_rule(rule)
        return {"message": f"RSS rule '{rule.name}' added successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/rules", response_model=List[RSSRule])
async def get_rules():
    """获取所有RSS规则"""
    return rss_manager.rules


@router.post("/fetch", response_model=List[RSSItem])
async def fetch_all_feeds():
    """抓取所有RSS源"""
    try:
        items = await rss_manager.fetch_all_feeds()
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/items", response_model=List[RSSItem])
async def get_filtered_items():
    """获取过滤后的RSS条目"""
    # 这里可以返回最近抓取的条目
    return []


@router.delete("/feeds/{name}", response_model=Dict[str, Any])
async def delete_feed(
    name: str,
    # current_user: dict = Depends(get_current_user)  # 暂时注释掉认证
):
    """删除RSS源"""
    if name not in rss_manager.feeds:
        raise HTTPException(status_code=404, detail="Feed not found")

    del rss_manager.feeds[name]
    return {"message": f"RSS feed '{name}' deleted successfully"}


@router.delete("/rules/{name}", response_model=Dict[str, Any])
async def delete_rule(
    name: str,
    # current_user: dict = Depends(get_current_user)  # 暂时注释掉认证
):
    """删除RSS规则"""
    for i, rule in enumerate(rss_manager.rules):
        if rule.name == name:
            rss_manager.rules.pop(i)
            return {"message": f"RSS rule '{name}' deleted successfully"}

    raise HTTPException(status_code=404, detail="Rule not found")
