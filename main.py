import json
import os
from typing import Dict
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

class BindManager:
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.bindings: Dict[str, str] = {}
        self._load_data()

    def _load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.bindings = json.load(f)
            except Exception as e:
                logger.error(f"加载绑定数据失败: {e}")

    def _save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.bindings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存绑定数据失败: {e}")

    def bind(self, open_id: str, qq_number: str) -> bool:
        self.bindings[open_id] = qq_number
        self._save_data()
        return True

    def get_qq(self, open_id: str) -> str:
        return self.bindings.get(open_id)

@register("helloworld", "Your Name", "一个简单的 Hello World 插件", "1.0.0", "repo url")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        '''这是一个 hello world 指令''' # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!") # 发送一条纯文本消息

@register("qqbind", "QQ绑定器", "QQ号码与开放平台ID绑定工具", "1.0.0", "")
class QQBindPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        data_path = os.path.join(context.get_plugin_data_path(), "bindings.json")
        self.bind_manager = BindManager(data_path)

    @filter.command("bind")
    async def bind_qq(self, event: AstrMessageEvent):
        '''绑定QQ号码，格式：/bind QQ号码'''
        sender_id = event.get_user_id()
        args = event.message_str.split()
        
        if len(args) != 2:
            yield event.plain_result("请使用正确的格式：/bind QQ号码")
            return

        qq_number = args[1]
        if not qq_number.isdigit():
            yield event.plain_result("请输入有效的QQ号码")
            return

        if self.bind_manager.bind(sender_id, qq_number):
            yield event.plain_result(f"绑定成功！已将你的账号与QQ号 {qq_number} 绑定")
        else:
            yield event.plain_result("绑定失败，请稍后重试")

    @filter.command("checkbind")
    async def check_bind(self, event: AstrMessageEvent):
        '''查询当前绑定的QQ号码'''
        sender_id = event.get_user_id()
        qq_number = self.bind_manager.get_qq(sender_id)
        
        if qq_number:
            yield event.plain_result(f"你当前绑定的QQ号是：{qq_number}")
        else:
            yield event.plain_result("你还没有绑定QQ号，请使用 /bind 命令进行绑定")
