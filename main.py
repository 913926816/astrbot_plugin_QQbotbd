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
        
    @filter.event_message_type(EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        '''处理所有QQ消息事件'''
        try:
            # 获取当前对话上下文
            curr_cid = await self.context.conversation_manager.get_curr_conversation_id(event.unified_msg_origin)
            conversation = None
            context = []
            if curr_cid:
                conversation = await self.context.conversation_manager.get_conversation(event.unified_msg_origin, curr_cid)
                context = json.loads(conversation.history)
            
            # 记录消息
            logger.info(f"收到消息: {event.message_str}")
            
            # 调用LLM处理消息
            yield event.request_llm(
                prompt=event.message_str,
                session_id=curr_cid,
                contexts=context,
                conversation=conversation
            )
            
        except Exception as e:
            logger.error(f"处理消息出错: {str(e)}")
            yield event.plain_result("消息处理出现错误,请稍后重试")

    async def handle_webhook_event(self, event_data: Dict[str, Any]):
        """处理QQ Webhook事件"""
        try:
            # 解析事件数据
            self.robot_uin = event_data.get('robot_uin')
            self.robot_appid = event_data.get('robot_appid')
            
            logger.info(f"收到QQ Webhook事件: uin={self.robot_uin}, appid={self.robot_appid}")
            
            # 5秒内返回成功响应
            return {"code": 0, "message": "success"}
            
        except Exception as e:
            logger.error(f"处理Webhook事件出错: {str(e)}")
            return {"code": -1, "message": str(e)}

    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        '''QQ机器人问候指令'''
        try:
            user_name = event.get_sender_name()
            message_str = event.message_str
            
            # 记录消息内容
            logger.info(f"收到用户 {user_name} 的消息: {message_str}")
            
            # 构造消息链
            chain = [
                At(qq=event.get_sender_id()),
                Plain(f"你好, {user_name}! 你发送的消息是: {message_str}")
            ]
            
            # 如果是QQ消息,添加机器人信息
            if self.robot_uin and self.robot_appid:
                chain.append(Plain(f"\n来自机器人: {self.robot_uin}"))
                
            yield event.chain_result(chain)
            
        except Exception as e:
            logger.error(f"处理hello指令出错: {str(e)}")
            yield event.plain_result("指令处理出现错误,请稍后重试")
