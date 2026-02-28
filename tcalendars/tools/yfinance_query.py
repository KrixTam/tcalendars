from playwright.sync_api import sync_playwright
from typing import Optional, Dict
import urllib.parse

# 全局内存缓存，用于存储请求结果
_API_CACHE: Dict[str, Dict] = {}

def search_yahoo_finance(
    query: str,
    region: str = "HK",
    lang: str = "zh_HK",
    quotes_count: int = 1,
    use_cache: bool = True,
    timeout: int = 10,
) -> Optional[Dict]:
    """
    使用 Playwright (Sync) 搜索 Yahoo Finance 并返回 JSON 对象。
    
    参数:
        query: 搜索关键词 (例如 "ANJI MICRO TECH" 或 "688019.SS")
        region: 地区代码 (默认 "HK", 可选 "US", "CN" 等)
        lang: 语言 (默认 "zh_HK", 可选 "en-US" 等)
        quotes_count: 返回的行情数量
        use_cache: 是否使用内存缓存 (避免重复请求相同 URL)
        timeout: 超时时间 (秒)
    
    返回:
        成功返回字典对象，失败返回 None
    """
    
    # 1. 构造基础 URL 和参数
    base_url = "https://query2.finance.yahoo.com/v1/finance/search"
    
    # 这些是 Yahoo Finance API 的标准参数，保留你原始 URL 中的大部分配置
    params = {
        "q": query,
        "lang": lang,
        "region": region,
        "quotesCount": quotes_count,
        "newsCount": 3,
        "listsCount": 2,
        "enableFuzzyQuery": "false",
        "quotesQueryId": "tss_match_phrase_query",
        "multiQuoteQueryId": "multi_quote_single_token_query",
        "newsQueryId": "news_cie_vespa",
        "enableCb": "false",
        "enableNavLinks": "true",
        "enableEnhancedTrivialQuery": "true",
        "enableResearchReports": "true",
        "enableCulturalAssets": "true",
        "enableLogoUrl": "true",
        "enableLists": "false",
        "recommendCount": 5,
        "enableCccBoost": "true",
        "enablePrivateCompany": "true"
    }
    
    # 编码 URL 参数
    query_string = urllib.parse.urlencode(params)
    full_url = f"{base_url}?{query_string}"
    
    # 2. 检查缓存
    if use_cache and full_url in _API_CACHE:
        print(f"[Cache Hit] 使用缓存数据: {query}")
        return _API_CACHE[full_url]

    # 3. 使用 Playwright 发送请求
    result_data = None
    
    # 启动同步 Playwright 上下文
    with sync_playwright() as p:
        # 启动浏览器 (headless=True 无头模式)
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                # 设置 User-Agent 伪装成 Mac Chrome
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # 发送请求 (timeout 单位为毫秒)
            response = page.goto(full_url, wait_until='networkidle', timeout=timeout * 1000)
            
            if response.ok:
                try:
                    result_data = response.json()
                    # 4. 写入缓存
                    if use_cache and result_data:
                        _API_CACHE[full_url] = result_data
                except Exception as e:
                    print(f"解析 JSON 失败: {e}")
            else:
                print(f"请求失败 [{response.status}]: {full_url}")

        except Exception as e:
            print(f"Playwright 执行出错: {e}")
        finally:
            browser.close()
            
    return result_data

# --- 主程序入口 (测试代码) ---
if __name__ == '__main__':
    # 测试案例 1: 搜索 ANJI MICRO TECH
    print("--- Test 1: Searching for ANJI MICRO TECH ---")
    data = search_yahoo_finance(
        query="ANJI MICRO TECH",
        region="US", # 注意原 URL region 是 US
        lang="zh_HK",
        quotes_count=6
    )

    if data:
        print(f"Total Count: {data.get('count')}")
        quotes = data.get('quotes', [])
        if quotes:
            print(f"Top Result: {quotes[0].get('symbol')} - {quotes[0].get('shortname')}")
    
    print("\n" + "="*40 + "\n")

    # 测试案例 2: 再次搜索相同内容 (验证缓存)
    print("--- Test 2: Testing Cache ---")
    data_cached = search_yahoo_finance(
        query="ANJI MICRO TECH",
        region="US",
        lang="zh_HK",
        quotes_count=6
    )
    
    print("\n" + "="*40 + "\n")

    # 测试案例 3: 搜索另一只股票 (例如 Apple)
    print("--- Test 3: Searching for AAPL ---")
    data_aapl = search_yahoo_finance("AAPL")
    if data_aapl:
        quotes = data_aapl.get('quotes', [])
        if quotes:
            print(f"Top Result: {quotes[0].get('symbol')} - {quotes[0].get('shortname')}")