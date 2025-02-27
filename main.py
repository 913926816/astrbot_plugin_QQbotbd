from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.all import *
from astrbot.api.message_components import *
from typing import Dict, Any
import json

@register("astrbot_plugin_QQbotbd", "QQ机器人", "QQ官方机器人Webhook插件", "1.0.0", "https://github.com/913926816/astrbot_plugin_QQbotbd")
class QQWebhookPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.robot_uin = None
        self.robot_appid = None
        
    @command("helloworld")
async def helloworld(self, event: AstrMessageEvent):
    chain = [
        At(qq=event.get_sender_id()), # At 消息发送者
        Plain("来看这个图："), 
        Image.fromURL("https://pan.zhil.cc/image/123.png"), # 从 URL 发送图片
        Image.fromFileSystem("path/to/image.jpg"), # 从本地文件目录发送图片
        Plain("这是一个图片。")
    ]
    yield event.chain_result(chain)
