import datetime
import threading
from typing import Any, List, Dict, Tuple
import json
import pytz
import re
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.config import settings
from app.log import logger
from app.plugins import _PluginBase
from app.core.metainfo import MetaInfo
from app.chain.media import MediaChain
from app.utils.http import RequestUtils

class Item:
    def __init__(self, title, link, ep, date, status):
        self.title = title
        self.link = link
        self.ep = ep
        self.date = date
        self.status = status

    def to_dict(self):
        return {
            "title": self.title,
            "link": self.link,
            "ep": self.ep,
            "date": self.date,
            "status": self.status,
        }

    def __repr__(self):
        return f"Item(title={self.title}, link={self.link}, ep={self.ep}, date={self.date},status={self.status})"


class yysubDailyReleasePush(_PluginBase):
    # 插件名称
    plugin_name = "YYSUB今日上映"
    # 插件描述
    plugin_desc = "推送今日上映的美剧信息"
    # 插件图标
    plugin_icon = "statistic.png"
    # 插件版本
    plugin_version = "0.0.1"
    # 插件作者
    plugin_author = "plsy1"
    # 作者主页
    author_url = "https://github.com/plsy1"
    # 插件配置项ID前缀
    plugin_config_prefix = "yysub_daily_release"
    # 加载顺序
    plugin_order = 1
    # 可使用的用户级别
    auth_level = 1

    # 退出事件
    _event = threading.Event()

    # 私有属性
    _scheduler = None
    _enabled = False
    _onlyonce = False
    _cron = None
    _remove_noCover = False
    _push_category: list = []

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._onlyonce = config.get("onlyonce")
            self._cron = config.get("cron")
            self._remove_noCover = config.get("remove_noCover") or False
            self._push_category = config.get("push_category") or []

        # 停止现有任务
        self.stop_service()

        # 启动服务
        if self._onlyonce:
            self._scheduler = BackgroundScheduler(timezone=settings.TZ)
            self._scheduler.add_job(
                func=self.job,
                trigger="date",
                run_date=datetime.datetime.now(tz=pytz.timezone(settings.TZ))
                + datetime.timedelta(seconds=3),
            )
            logger.info(f"YYSUB 当天上映推送服务启动，立即运行一次")
            # 关闭一次性开关
            self._onlyonce = False
            # 保存配置
            self.__update_config()
            # 启动服务
            if self._scheduler.get_jobs():
                self._scheduler.print_jobs()
                self._scheduler.start()

    def __update_config(self):
        """
        更新配置
        """
        self.update_config(
            {
                "enabled": self._enabled,
                "onlyonce": self._onlyonce,
                "cron": self._cron,
                "remove_noCover": self._remove_noCover,
                "push_category": self._push_category,
            }
        )

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        [{
            "id": "服务ID",
            "name": "服务名称",
            "trigger": "触发器：cron/interval/date/CronTrigger.from_crontab()",
            "func": self.xxx,
            "kwargs": {} # 定时器参数
        }]
        """
        if self._enabled and self._cron:
            return [
                {
                    "id": "YYSUBDailyRelease",
                    "name": "yysub今日播出",
                    "trigger": CronTrigger.from_crontab(self._cron),
                    "func": self.job,
                    "kwargs": {},
                }
            ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        option_category = [
            {"title": "剧集", "value": 1},
            {"title": "电影", "value": 2},
        ]

        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "enabled",
                                            "label": "启用插件",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "onlyonce",
                                            "label": "立即运行一次",
                                        },
                                    }
                                ],
                            },
                        ],
                    }
                ],
            },
            {
                "component": "VRow",
                "content": [
                    {
                        "component": "VCol",
                        "props": {"cols": 12, "md": 6},
                        "content": [
                            {
                                "component": "VTextField",
                                "props": {
                                    "model": "cron",
                                    "label": "服务执行周期",
                                    "placeholder": "5位cron表达式",
                                },
                            }
                        ],
                    },
                ],
            },
        ], {
            "enabled": False,
            "onlyonce": False,
            "cron": "",
            "remove_noCover": True,
            "push_category": [],
        }

    def get_page(self) -> List[dict]:
        pass

    
    def job(self):
        html_content = self.get_series_source()
        items = self.parse_items(html_content)
        message = ""
        for item in items:
            if item.status:
                message += f"{item.title} {item.ep} {item.status}\n"
            else:
                message += f"{item.title} {item.ep}\n"
        self.post_message(
            title="【今日播出】",
            text=(
                message
            ),
            image=None
        )
    

    def parse_items(self,html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        days = table.find_all("td", class_="ihbg")

        schedule = []

        for day in days:
            date_info = day.find("dt")
            if not date_info:
                continue

            date_text = date_info.get_text(strip=True)
            episodes = day.find_all("dd")

            for episode in episodes:
                a_tag = episode.find("a")
                if a_tag:
                    title = "".join(a_tag.find_all(string=True, recursive=False)).strip()
                    link = a_tag["href"]

                spans = a_tag.find_all("span")
                if len(spans) >= 2:
                    ep = spans[0].get_text(strip=True)
                    status = spans[1].get_text(strip=True)
                else:
                    ep = spans[0].get_text(strip=True)
                    status = None

                date = date_text
                
                if date.split(" ")[0].replace("号", "") == datetime.datetime.now().strftime("%d"):
                    schedule.append(Item(title, f'https://yysub.net{link}', ep, date, status))
                    
        return schedule
    
    def get_series_source(self):
        url = "https://yysub.net/tv/schedule"
        try:
            response_text = RequestUtils(
                ua=settings.USER_AGENT if settings.USER_AGENT else None,
                proxies=settings.PROXY if settings.PROXY else None,
            ).get(url=url)
            return response_text
        except Exception as e:
            logger.error(f"从 yysub 获取数据失败: {e}")
            return None

    def stop_service(self):
        """
        停止服务
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._event.set()
                    self._scheduler.shutdown()
                    self._event.clear()
                self._scheduler = None
        except Exception as e:
            logger.error(str(e))
