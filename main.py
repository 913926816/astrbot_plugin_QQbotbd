from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register

@register("astrbot_plugin_QQbotbd", "英一智", "一个扫码登录绑定QQ号的插件", "1.0.0", "https://github.com/913926816/astrbot_plugin_QQbotbd/")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        '''这是一个 hello world 指令''' # 这是 handler 的描述，将会被解析方便用户了解插件内容。非常建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str # 获取消息的纯文本内容
        yield event.plain_result(f"Hello, {user_name}!") # 发送一条纯文本消息
