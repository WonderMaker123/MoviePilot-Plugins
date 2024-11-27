
import datetime
import threading
from typing import Any, List, Dict, Tuple

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.config import settings
from app.log import logger
from app.plugins import _PluginBase
from app.plugins.dailyreleasepush.parse import *

class DailyReleasePush(_PluginBase):
    # 插件名称
    plugin_name = "今日上映剧集"
    # 插件描述
    plugin_desc = "推送今日上映的剧集信息到消息通知工具"
    # 插件图标
    plugin_icon = "statistic.png"
    # 插件版本
    plugin_version = "0.1.0"
    # 插件作者
    plugin_author = "plsy1"
    # 作者主页
    author_url = "https://github.com/plsy1"
    # 插件配置项ID前缀
    plugin_config_prefix = "daily_release"
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

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._onlyonce = config.get("onlyonce")
            self._cron = config.get("cron")
            self._remove_noCover = config.get("remove_noCover") or False
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
            logger.info(f"当天上映推送服务启动，立即运行一次")
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
                    "id": "DailyRelease",
                    "name": "推送当日上映剧集信息",
                    "trigger": CronTrigger.from_crontab(self._cron),
                    "func": self.job,
                    "kwargs": {},
                }
            ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
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
                                "props": {"cols": 12, "md": 4},
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
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "remove_noCover",
                                            "label": "去除无封面条目",
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
                    }
                ],
            },
        ], {
            "enabled": False,
            "onlyonce": False,
            "cron": "",
            "remove_noCover": True,
        }

    def get_page(self) -> List[dict]:
        pass

    def job(self):
        """
        获取当日上映的剧集信息，推送消息
        """
        today_mmdd = datetime.datetime.now().strftime("%m%d")
        items = parse_items(get_source())
        if self._remove_noCover:
            items_to_process = [
                item
                for item in items
                if item.poster_url != "https://img.huo720.com/files/movie-default.gif"
            ]
        else:
            items_to_process = items
        for item in items_to_process:
            item_mmdd = self.convert_to_mmdd(item.date)
            if item_mmdd == today_mmdd:
                self.post_message(
                    title=f"【今日上映】{item.title.upper()} ({item.english_title})",
                    text=(
                        f"*日期*: {item.date}\n"
                        f"*国家*: {item.country}\n"
                        f"*类型*: {', '.join(item.genres)}\n"
                        f"*介绍*: {item.description}\n"
                    ),
                    image=item.poster_url
                )
    def convert_to_mmdd(self,date_str):
        try:
            date_obj = datetime.datetime.strptime(date_str, "%m月%d日")
            return date_obj.strftime("%m%d")  # 返回 MMDD 格式
        except ValueError as e:
            logger.error(f"日期转换错误")


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
