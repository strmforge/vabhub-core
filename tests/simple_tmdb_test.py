#!/usr/bin/env python3
"""
简单测试TMDB API功能
"""

import asyncio
import httpx
import json

async def test_tmdb_api():
    """测试TMDB API连接"""
    print("🔍 测试TMDB API连接...")
    
    # TMDB API配置
    api_key = "db55373b1b8f4f6a8654d6a0c1d37a8f"  # MoviePilot默认密钥
    base_url = "https://api.themoviedb.org/3/"
    
    # 测试热门电影API
    endpoint = "movie/popular"
    url = f"{base_url}{endpoint}?api_key={api_key}&language=zh-CN&page=1"
    
    try:
        # 创建HTTP客户端
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"🌐 发送请求到: {endpoint}")
            
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                print("✅ TMDB API连接成功!")
                print(f"📊 获取到 {len(data.get('results', []))} 部电影")
                
                # 显示前3部电影
                for i, movie in enumerate(data.get('results', [])[:3], 1):
                    print(f"  {i}. {movie.get('title', '未知')} ({movie.get('release_date', '未知')})")
                    print(f"     评分: {movie.get('vote_average', 0)}/10")
                    print(f"     简介: {movie.get('overview', '无')[:50]}...")
                
                return True
                
            else:
                print(f"❌ TMDB API请求失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                return False
                
    except httpx.ConnectError as e:
        print(f"❌ 网络连接错误: {e}")
        print("💡 请检查网络连接和代理设置")
        return False
        
    except httpx.TimeoutException as e:
        print(f"❌ 请求超时: {e}")
        return False
        
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return False

async def test_tmdb_with_proxy():
    """测试带代理的TMDB API"""
    print("\n🔍 测试带代理的TMDB API...")
    
    api_key = "db55373b1b8f4f6a8654d6a0c1d37a8f"
    base_url = "https://api.themoviedb.org/3/"
    endpoint = "movie/popular"
    url = f"{base_url}{endpoint}?api_key={api_key}&language=zh-CN&page=1"
    
    # 测试代理设置（这里使用系统代理）
    proxies = {
        "http://": None,
        "https://": None
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0, proxies=proxies) as client:
            print("🌐 使用系统代理发送请求...")
            
            response = await client.get(url)
            
            if response.status_code == 200:
                print("✅ 带代理的TMDB API连接成功!")
                return True
            else:
                print(f"❌ 带代理的请求失败: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ 带代理测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🚀 开始TMDB代理功能测试")
    print("=" * 50)
    
    # 测试基本API连接
    basic_success = await test_tmdb_api()
    
    # 测试代理功能
    proxy_success = await test_tmdb_with_proxy()
    
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    print(f"  基本API连接: {'✅ 成功' if basic_success else '❌ 失败'}")
    print(f"  代理功能: {'✅ 成功' if proxy_success else '❌ 失败'}")
    
    if basic_success and proxy_success:
        print("\n🎉 TMDB代理功能测试通过!")
        return True
    else:
        print("\n💥 TMDB代理功能测试失败!")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    
    if not result:
        import sys
        sys.exit(1)