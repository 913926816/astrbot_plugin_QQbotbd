from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.all import *
from astrbot.api.message_components import *
from typing import Dict, Any

@register("astrbot_plugin_QQbotbd", "QQ机器人", "QQ官方机器人Webhook插件", "1.0.0", "https://github.com/913926816/astrbot_plugin_QQbotbd")
class QQWebhookPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.robot_uin = None
        self.robot_appid = None

    @filter.event_message_type(EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        '''处理所有QQ消息事件'''
        try:
            # 设置不调用LLM
            event.should_call_llm(False)
            
            # 记录消息
            logger.info(f"收到消息: {event.message_str}")
            
            # 返回固定回复
            yield event.plain_result("收到消息,但我暂时无法理解,请尝试其他指令。")
            
        except Exception as e:
            logger.error(f"处理消息出错: {str(e)}")
            yield event.plain_result("消息处理出现错误,请稍后重试")

    @command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        chain = [
            At(qq=event.get_sender_id()), # At 消息发送者
            Plain("来看这个图："), 
            Image.fromURL("https://example.com/image.jpg"), # 从 URL 发送图片
            Image.fromFileSystem("path/to/image.jpg"), # 从本地文件目录发送图片
            Plain("这是一个图片。")
        ]
        yield event.chain_result(chain)
