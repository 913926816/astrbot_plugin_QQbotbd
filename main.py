import aiohttp
import os
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register

@register("qqlogin", "AstrBot Team", "QQ登录二维码生成插件", "1.0.0", "https://github.com/AstrBot/astrbot_plugin_QQbotbd")
class QQLoginPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 确保图片保存目录存在
        self.img_dir = os.path.join(os.path.dirname(__file__), "temp")
        if not os.path.exists(self.img_dir):
            os.makedirs(self.img_dir)
    
    @filter.command("test_image")
    async def handle_test_image(self, event: AstrMessageEvent):
        '''测试图片发送功能'''
        try:
            # 测试图片URL
            test_image_url = "https://pan.zhil.cc/image/123.png"
            
            # 获取并保存测试图片
            async with aiohttp.ClientSession() as session:
                async with session.get(test_image_url) as img_resp:
                    img_data = await img_resp.read()
                    img_path = os.path.join(self.img_dir, f"test_{event.get_user_id()}.png")
                    
                    # 保存图片到本地
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                    
                    # 构建富媒体消息
                    rich_media = {
                        "type": "rich_media",
                        "title": "测试图片",
                        "description": "这是一个测试用的图片",
                        "image": {
                            "path": img_path,
                            "type": "image/png"
                        },
                        "url": test_image_url
                    }
                    
                    # 发送富媒体消息
                    yield event.rich_media_result(rich_media)
                    
                    # 作为备用，同时发送普通图片
                    yield event.image_result(img_path)
                    
                    # 清理临时文件
                    try:
                        os.remove(img_path)
                    except:
                        pass
                
        except Exception as e:
            yield event.plain_result(f"测试图片发送失败: {str(e)}")
    
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
                    
                    # 获取并保存二维码图片
                    async with session.get(login_url) as img_resp:
                        img_data = await img_resp.read()
                        img_path = os.path.join(self.img_dir, f"qrcode_{event.get_user_id()}.png")
                        
                        # 保存图片到本地
                        with open(img_path, "wb") as f:
                            f.write(img_data)
                        
                        # 构建富媒体消息
                        rich_media = {
                            "type": "rich_media",
                            "title": "QQ登录二维码",
                            "description": "请使用QQ扫描二维码登录",
                            "image": {
                                "path": img_path,
                                "type": "image/png"
                            },
                            "url": login_url
                        }
                        
                        # 发送富媒体消息
                        yield event.rich_media_result(rich_media)
                        
                        # 作为备用，同时发送普通图片
                        yield event.image_result(img_path)
                        
                        # 清理临时文件
                        try:
                            os.remove(img_path)
                        except:
                            pass
                    
        except Exception as e:
            yield event.plain_result(f"获取二维码时发生错误: {str(e)}")
