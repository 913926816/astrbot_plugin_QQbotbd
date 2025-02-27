from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register

@register("qqbot", "QQ机器人", "QQ机器人消息处理插件 - 支持文本和图片回复", "1.0.0", "https://github.com/your-repo")
class QQBotPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
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

    @filter.command("qq.image")
    async def handle_image(self, event: AstrMessageEvent) -> MessageEventResult:
        '''
        回复QQ图片消息
        用法: /qq.image <图片URL>
        '''
        image_url = event.message_str
        if not image_url:
            yield event.plain_result("请提供图片URL")
            return
            
        try:
            # 使用AstrBot的图片消息回复
            yield event.image_result(image_url)
        except Exception as e:
            self.logger.error(f"发送图片失败: {str(e)}")
            yield event.plain_result(f"❌ 图片发送失败: {str(e)}")

    @filter.command("qq.help")
    async def show_help(self, event: AstrMessageEvent) -> MessageEventResult:
        '''显示QQ机器人插件帮助信息'''
        help_text = """
        QQ机器人消息处理插件使用帮助:
        
        1. 回复文本消息
           命令: /qq.reply <消息内容>
           
        2. 回复图片消息
           命令: /qq.image <图片URL>
           支持的图片格式: jpg, png, gif
           
        3. 查看帮助
           命令: /qq.help
        """
        yield event.plain_result(help_text)
