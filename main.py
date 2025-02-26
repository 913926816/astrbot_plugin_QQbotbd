import aiohttp
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register

@register("qqlogin", "AstrBot Team", "QQ登录二维码生成插件", "1.0.0", "https://github.com/AstrBot/astrbot_plugin_QQbotbd")
class QQLoginPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    @filter.command("qqlogin")
    async def handle_qqlogin(self, event: AstrMessageEvent):
        '''生成QQ登录二维码'''
        try:
            # 调用QQ API获取二维码
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://q.qq.com/qrcode/create",
                    json={"type": "777"}
                ) as resp:
                    data = await resp.json()
                    if "qrcode" not in data:
                        yield event.plain_result("获取二维码失败，请稍后重试")
                        return
                    
                    qrcode_str = data["qrcode"]
                    login_url = f"https://q.qq.com/login/applist?client=qq&code={qrcode_str}&ticket=null"
                    
                    # 直接获取二维码图片
                    async with session.get(login_url) as img_resp:
                        img_data = await img_resp.read()
                        yield event.image_result(img_data)
                    
        except Exception as e:
            yield event.plain_result(f"获取二维码时发生错误: {str(e)}")
