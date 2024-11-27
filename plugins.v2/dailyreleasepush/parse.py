from bs4 import BeautifulSoup
from app.log import logger
from app.utils.http import RequestUtils
from app.core.config import settings

class Item:
    def __init__(self, title, english_title, poster_url, category, date, country, genres, description):
        self.title = title  # 中文标题
        self.english_title = english_title  # 英文标题
        self.poster_url = poster_url  # 海报链接
        self.category = category  # 类型（如电视、电影）
        self.date = date  # 发布时间
        self.country = country  # 国家
        self.genres = genres  # 类型标签（如喜剧、动画等）
        self.description = description  # 简介
        
        
# 解析单条条目
def parse_item(div):
    try:
        title = div.find("div", class_="fs-5 fw-bold text-truncate").get_text(strip=True)
    except AttributeError:
        title = ""
    
    # 提取英文标题，默认值为空字符串
    try:
        english_title = div.find("div", class_="fs-6 fw-light text-truncate mb-2").get_text(strip=True)
    except AttributeError:
        english_title = ""
    
    # 提取海报链接，默认值为 None
    try:
        poster_url = div.find("img", class_="w-100 rounded-start")["src"]
    except (AttributeError, KeyError):
        poster_url = None
    
    # 提取类型（如电视、电影），默认值为空字符串
    try:
        category = div.find("span", class_="p-1 me-1 border rounded-3").get_text(strip=True)
    except AttributeError:
        category = ""
    
    # 提取发布时间，默认值为空字符串
    try:
        date = div.find("span", class_="me-1 py-1 px-2 border rounded-3").get_text(strip=True)
    except AttributeError:
        try:
            # 如果第一个元素获取不到，尝试第二个元素
            date = div.find("span", class_="me-1 py-1 px-2 border rounded-3 fw-bold").get_text(strip=True)
        except AttributeError:
            date = ""  # 如果两个元素都获取不到，设置为默认空字符串
    
    # 提取国家，默认值为空字符串
    try:
        country = div.find_all("span", class_="me-1 text-secondary")[0].get_text(strip=True)
    except (AttributeError, IndexError):
        country = ""
    
    # 提取类型标签（如喜剧、动画等），默认值为空列表
    try:
        genres = [span.get_text(strip=True) for span in div.find_all("span", class_="me-1 text-secondary")[1:]]
    except AttributeError:
        genres = []
    
    # 提取简介，默认值为空字符串
    try:
        description = div.find("div", class_="pt-2 text-truncate d-none d-md-block").get_text(strip=True)
    except AttributeError:
        description = ""
    
    return Item(title, english_title, poster_url, category, date, country, genres, description)


def parse_items(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        logger.error(f"解析 HTML 时出错: {e}")
    
    item_divs = soup.find_all("div", class_="bg-white rounded-3 border mb-3")
    items = [parse_item(div) for div in item_divs]
    return items

def get_source():
    url = "https://huo720.com/calendar/upcoming"
    try:
        response = RequestUtils(ua=settings.USER_AGENT if settings.USER_AGENT else None,
                           proxies=settings.PROXY if settings.PROXY else None).get(url=url)
        return response
        
    except Exception as e:
        logger.error("从数据源网站获取信息失败",e)