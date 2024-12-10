import datetime
import threading
from typing import Any, List, Dict, Tuple
import json
import pytz
import re
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.config import settings
from app.log import logger
from app.plugins import _PluginBase
from app.utils.http import RequestUtils


class dailyReleaseSourceFromTMDB(_PluginBase):
    # 插件名称
    plugin_name = "今日上映"
    # 插件描述
    plugin_desc = "推送TMDB今日上映的剧集信息到消息通知工具。"
    # 插件图标
    plugin_icon = "tmdb.svg"
    # 插件版本
    plugin_version = "0.4.0"
    # 插件作者
    plugin_author = "plsy1"
    # 作者主页
    author_url = "https://github.com/plsy1"
    # 插件配置项ID前缀
    plugin_config_prefix = "daily_release_tmdb"
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
    _removeNoCoverSeries = False
    _removeNoCoverMovies = False
    _series_Chinese_Title = False
    _movie_Chinese_Title = False
    _push_series_languages: list = []
    _push_movies_languages: list = []
    _pass_series_genre: list = []
    _pass_movies_genre: list = []

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._onlyonce = config.get("onlyonce")
            self._cron = config.get("cron")
            self._removeNoCoverSeries = config.get("removeNoCoverSeries") or False
            self._removeNoCoverMovies = config.get("removeNoCoverMovies") or False
            self._movie_Chinese_Title = config.get("movie_Chinese_Title") or False
            self._series_Chinese_Title = config.get("series_Chinese_Title") or False
            self._push_series_languages = config.get("push_series_languages") or []
            self._push_movies_languages = config.get("push_movies_languages") or []
            self._pass_series_genre = config.get("pass_series_genre") or []
            self._pass_movies_genre = config.get("pass_movies_genre") or []
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
                "removeNoCoverSeries": self._removeNoCoverSeries,
                "removeNoCoverMovies": self._removeNoCoverMovies,
                "movie_Chinese_Title": self._movie_Chinese_Title,
                "series_Chinese_Title": self._series_Chinese_Title,
                "push_series_languages": self._push_series_languages,
                "push_movies_languages" : self._push_movies_languages,
                "pass_series_genre" : self._pass_series_genre,
                "pass_movies_genre" : self._pass_movies_genre,
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
                    "id": "dailyReleaseSourceFromTMDB",
                    "name": "推送当日上映剧集信息（TMDB）",
                    "trigger": CronTrigger.from_crontab(self._cron),
                    "func": self.job,
                    "kwargs": {},
                }
            ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        series_language = [
            {"title": "汉语", "value": "zh"},
            {"title": "英语", "value": "en"},
            {"title": "日语", "value": "ja"},
            {"title": "韩语", "value": "ko"},
            {"title": "泰语", "value": "th"},
            {"title": "德语", "value": "de"},
            {"title": "法语", "value": "fr"},
            {"title": "西语", "value": "es"},
            {"title": "葡语", "value": "pt"},
            {"title": "俄语", "value": "ru"},
            {"title": "意语", "value": "it"},
            {"title": "荷兰语", "value": "nl"},
            {"title": "波兰语", "value": "pl"},
            {"title": "印地语", "value": "hi"},
            {"title": "土耳其语", "value": "tr"},
            {"title": "瑞典语", "value": "sv"},
            {"title": "挪威语", "value": "no"},
            {"title": "芬兰语", "value": "fi"},
        ]
        ## 添加语言
        movies_language = [
            {"title": "汉语", "value": "zh"},
            {"title": "英语", "value": "en"},
            {"title": "日语", "value": "ja"},
            {"title": "韩语", "value": "ko"},
            {"title": "泰语", "value": "th"},
            {"title": "德语", "value": "de"},
            {"title": "法语", "value": "fr"},
            {"title": "西语", "value": "es"},
            {"title": "葡语", "value": "pt"},
            {"title": "俄语", "value": "ru"},
            {"title": "意语", "value": "it"},
            {"title": "荷兰语", "value": "nl"},
            {"title": "波兰语", "value": "pl"},
            {"title": "印地语", "value": "hi"},
            {"title": "土耳其语", "value": "tr"},
            {"title": "瑞典语", "value": "sv"},
            {"title": "挪威语", "value": "no"},
            {"title": "芬兰语", "value": "fi"},
        ]
        
        pass_series_genre = [
            {"title": "动作", "value": 28},
            {"title": "冒险", "value": 12},
            {"title": "动画", "value": 16},
            {"title": "喜剧", "value": 35},
            {"title": "犯罪", "value": 80},
            {"title": "纪录", "value": 99},
            {"title": "剧情", "value": 18},
            {"title": "家庭", "value": 10751},
            {"title": "奇幻", "value": 14},
            {"title": "历史", "value": 36},
            {"title": "恐怖", "value": 27},
            {"title": "音乐", "value": 10402},
            {"title": "悬疑", "value": 9648},
            {"title": "爱情", "value": 10749},
            {"title": "科幻", "value": 878},
            {"title": "电视电影", "value": 10770},
            {"title": "惊悚", "value": 53},
            {"title": "战争", "value": 10752},
            {"title": "西部", "value": 37},
            {"title": "动作与冒险", "value": 10759},
            {"title": "儿童", "value": 10762},
            {"title": "新闻", "value": 10763},
            {"title": "真人秀", "value": 10764},
            {"title": "科幻与奇幻", "value": 10765},
            {"title": "肥皂剧", "value": 10766},
            {"title": "脱口秀", "value": 10767},
            {"title": "战争与政治", "value": 10768},
        ]
        
        pass_movies_genre = [
            {"title": "动作", "value": 28},
            {"title": "冒险", "value": 12},
            {"title": "动画", "value": 16},
            {"title": "喜剧", "value": 35},
            {"title": "犯罪", "value": 80},
            {"title": "纪录", "value": 99},
            {"title": "剧情", "value": 18},
            {"title": "家庭", "value": 10751},
            {"title": "奇幻", "value": 14},
            {"title": "历史", "value": 36},
            {"title": "恐怖", "value": 27},
            {"title": "音乐", "value": 10402},
            {"title": "悬疑", "value": 9648},
            {"title": "爱情", "value": 10749},
            {"title": "科幻", "value": 878},
            {"title": "电视电影", "value": 10770},
            {"title": "惊悚", "value": 53},
            {"title": "战争", "value": 10752},
            {"title": "西部", "value": 37},
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
                                            "model": "removeNoCoverSeries",
                                            "label": "仅横向背景图剧集",
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
                                            "model": "removeNoCoverMovies",
                                            "label": "仅横向背景图电影",
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
                                            "model": "series_Chinese_Title",
                                            "label": "仅中文标题剧集",
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
                                            "model": "movie_Chinese_Title",
                                            "label": "仅中文标题电影",
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
            {
                "component": "VRow",
                "content": [
                    {
                        "component": "VCol",
                        "props": {"cols": 12, "md": 6},
                        "content": [
                            {
                                "component": "VSelect",
                                "props": {
                                    "chips": True,
                                    "multiple": True,
                                    "model": "push_series_languages",
                                    "label": "剧集语言",
                                    "items": series_language,
                                },
                            }
                        ],
                    },
                    {
                        "component": "VCol",
                        "props": {"cols": 12, "md": 6},
                        "content": [
                            {
                                "component": "VSelect",
                                "props": {
                                    "chips": True,
                                    "multiple": True,
                                    "model": "push_movies_languages",
                                    "label": "电影语言",
                                    "items": movies_language,
                                },
                            }
                        ],
                    },
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
                                "component": "VSelect",
                                "props": {
                                    "chips": True,
                                    "multiple": True,
                                    "model": "pass_series_genre",
                                    "label": "排除剧集标签",
                                    "items": pass_series_genre,
                                },
                            }
                        ],
                    },
                    {
                        "component": "VCol",
                        "props": {"cols": 12, "md": 6},
                        "content": [
                            {
                                "component": "VSelect",
                                "props": {
                                    "chips": True,
                                    "multiple": True,
                                    "model": "pass_movies_genre",
                                    "label": "排除电影标签",
                                    "items": pass_movies_genre,
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
            "removeNoCoverSeries": True,
            "removeNoCoverMovies": True,
            "movie_Chinese_Title": True,
            "series_Chinese_Title": True,
            "push_series_languages": [],
            "push_movies_languages": [],
            "pass_series_genre": [],
            "pass_movies_genre": [],
        }

    def get_page(self) -> List[dict]:
        pass

    def job(self):
        """
        获取当日上映的剧集信息，推送消息
        """
        items = self.get_series_source()
        if items:
            for item in items:
                original_language = item.get("original_language")

                if original_language is not None and original_language not in self._push_series_languages:
                    continue

                if self._removeNoCoverSeries == True and item.get("backdrop_path") is None:
                    continue
                
                if self._series_Chinese_Title == True and item.get("name") == item.get("original_name") and original_language != "zh":
                    continue
                
                if any(genre_id in self._pass_series_genre for genre_id in item.get('genre_ids', [])):
                    continue

                imgage_base = "https://image.tmdb.org/t/p/w1280"
                image_name = item.get("backdrop_path") or item.get("poster_path")
                if not image_name:
                    image_url = None
                else:
                    image_url = imgage_base + image_name

                self.post_message(
                    title="【今日上映】",
                    text=(
                        f"名称: {item.get('name') or item.get('original_name', '')}\n"
                        f"类型: {'剧集'}\n"
                        f"语言: {item.get('original_language_zh')}\n"
                        + (
                            f"地区: {', '.join([str(origin_country) for origin_country in item.get('origin_country', [])])}\n"
                            if item.get("origin_country")
                            else ""
                        )
                        + (
                            f"标签: {', '.join([str(genre_id) for genre_id in item.get('genre_ids_zh', [])])}\n"
                            if item.get("genre_ids_zh")
                            else ""
                        )
                        # + f"日期: {item.get('first_air_date', '')}\n"
                        + (
                            f"简介: {item.get('overview')}\n"
                            if item.get("overview")
                            else ""
                        )
                    ),
                    image=image_url,
                )
        else:
            logger.info("未获取到今日剧集数据，跳过处理")
            
        items = self.get_movies_source()
        if items:
            for item in items:
                original_language = item.get("original_language")
                
                if self._movie_Chinese_Title == True and item.get("original_title") == item.get("title") and original_language != "zh":
                    continue

                if original_language is not None and original_language not in self._push_movies_languages:
                    continue

                if self._removeNoCoverMovies == True and item.get("backdrop_path") is None:
                    continue
                
                if any(genre_id in self._pass_movies_genre for genre_id in item.get('genre_ids', [])):
                    continue

                imgage_base = "https://image.tmdb.org/t/p/w1280"
                image_name = item.get("backdrop_path") or item.get("poster_path")
                if not image_name:
                    image_url = None
                else:
                    image_url = imgage_base + image_name
                
                self.post_message(
                    title="【今日上映】",
                    text=(
                        f"名称: {item.get('title') or item.get('original_title', '')}\n"
                        f"类型: {'电影'}\n"
                        f"语言: {item.get('original_language_zh')}\n"
                        + (
                            f"标签: {', '.join([str(genre_id) for genre_id in item.get('genre_ids_zh', [])])}\n"
                            if item.get("genre_ids_zh")
                            else ""
                        )
                        # + f"日期: {item.get('first_air_date', '')}\n"
                        + (
                            f"简介: {item.get('overview')}\n"
                            if item.get("overview")
                            else ""
                        )
                    ),
                    image=image_url,
                )
        else:
            logger.info("未获取到今日电影数据，跳过处理")

    def clean_spaces(self, text):
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def get_series_source(self):
        base = "https://plsy1.github.io/dailyrelease/data/tmdb/series"
        date = datetime.datetime.now().strftime("%Y%m%d")
        url = f"{base}/{date}.json"
        try:
            response_text = RequestUtils(
                ua=settings.USER_AGENT if settings.USER_AGENT else None,
                proxies=settings.PROXY if settings.PROXY else None,
            ).get(url=url)
            items = json.loads(response_text)
            return items
        except Exception as e:
            logger.error(f"请求失败: {e}")
            return None
        
        
    def get_movies_source(self):
        base = "https://plsy1.github.io/dailyrelease/data/tmdb/movies"
        date = datetime.datetime.now().strftime("%Y%m%d")
        url = f"{base}/{date}.json"
        try:
            response_text = RequestUtils(
                ua=settings.USER_AGENT if settings.USER_AGENT else None,
                proxies=settings.PROXY if settings.PROXY else None,
            ).get(url=url)
            items = json.loads(response_text)
            return items
        except Exception as e:
            logger.error(f"请求失败: {e}")
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
