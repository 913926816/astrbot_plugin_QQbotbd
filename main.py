from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult, EventFilter
from astrbot.api.star import Context, Star, register

@register(
    name="astrbot_plugin_QQbotbd",
    author="913926816",
    description="一个通过二维码登录绑定QQ号的插件",
    version="1.0.0",
    repository="https://github.com/913926816/astrbot_plugin_QQbotbd"
)
class QQBotPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 预设的图片URL
        self.default_image_url = "https://pan.zhil.cc/image/123.png"
    
    @filter.command("qq.reply")
    async def handle_qq_message(self, event: AstrMessageEvent) -> MessageEventResult:
        '''
        回复QQ文本消息
        用法: /qq.reply <消息内容>
        '''
        message_content = event.message_str
        if not message_content:
            yield event.plain_result("请输入要回复的消息内容")
            return
            
        try:
            # 这里只需要处理消息内容,不需要关心QQ机器人的认证
            yield event.plain_result(f"收到消息: {message_content}")
        except Exception as e:
            self.logger.error(f"处理消息失败: {str(e)}")
            yield event.plain_result(f"❌ 消息处理失败: {str(e)}")

    @filter.startswith("/qqbing")
    async def handle_bing(self, event: AstrMessageEvent) -> MessageEventResult:
        '''
        发送预设的图片
        用法: /qqbing
        '''
        try:
            # 直接发送预设的图片
            yield event.image_result(self.default_image_url)
        except Exception as e:
            self.logger.error(f"发送图片失败: {str(e)}")
            yield event.plain_result(f"❌ 图片发送失败: {str(e)}")

    @filter.startswith("/qq.help")
    async def show_help(self, event: AstrMessageEvent) -> MessageEventResult:
        '''显示QQ机器人插件帮助信息'''
        help_text = """
        QQ绑定插件使用帮助:
        
        1. 发送预设图片
           命令: /qqbing
           将发送固定的图片
           
        2. 查看帮助
           命令: /qq.help
        """
        yield event.plain_result(help_text)
