import aiohttp
import os
import base64
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
            # 测试用的base64图片数据
            base64_data = "iVBORw0KGgoAAAANSUhEUgAAAZAAAAGQCAIAAAAP3aGbAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAHwklEQVR4nO3d240jORBFQWnR/rs868ACTSyInDxVEQa0So8+4M8Fv3/+/PkAFPzztx8A4JRgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQIZgARnrtoQvX29N7gSH3Xqkyb3hwqskX/4P4oQFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQIZgARmCBWQIFpCxbkvoltArJr/Ww/e17Zd24tZXNvzeH7xIdcICMgQLyBAsIEOwgAzBAjIEC8gQLCBDsIAMwQIyBAvIECwg4+dvP8D/Mbk3PJxBFUdnw8+87Y6/yWnnwrnltq/jkBMWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGaP3Ek6O1x58v+GJ4rbx0PAj8quLH9G2+wRvcS8h8EaCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkHFtS1icJg1fzbZtSvlgxV/1oW3j3+G1qRMWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGckt4Ynh9/XmhdfFj+jlv6ITC2+KnOSEBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQMbolvDWmmzhnCr62E81+WsctnAl+quLz+yEBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQMbP5Is9eOF1IvrYvzpcihW//YX3Et6y8JFOOGEBGYIFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQMbP5Is9eOF1IvrYvzpcihW//YX3Et6y8JFOOGEBGYIFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAxuj4+UT0RtJtU9LJO2sP33vxGt1tz3PRtp35IScsIEOwgAzBAjIEC8gQLCBDsIAMwQIyBAvIECwgQ7CADMECMka3hA++lnJSdAV265Fu/Z2Tj3F4Jzj5D7Lw7Z9wwgIyBAvIECwgQ7CADMECMgQLyBAsIEOwgAzBAjIEC8gQLCDj2pZw2wxqcnF28eW2Wfi+ir+0haO8yW/24tt3wgIyBAvIECwgQ7CADMECMgQLyBAsIEOwgAzBAjIEC8gQLCDj2pZwclE1OYNaOKbb5uLccttOkG2csIAMwQIyBAvIECwgQ7CADMECMgQLyBAsIEOwgAzBAjIEC8j4Ti6qHrwme/N47eLccvLGyRPD69fiNYjDz+OEBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQEbyXsJbhkdwt2wb0w1/rZODu+FbKV2C+SsnLCBDsIAMwQIyBAvIECwgQ7CADMECMgQLyBAsIEOwgAzBAjKubQm37QS3Pc/n3lIsuluM3ji56rU+r98bOmEBGYIFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQMXov4YPdur9v28e4cJJZ/BgPnye6Ep3khAVkCBaQIVhAhmABGYIFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZ18bPJxYuaX91cSM6eQNo8dLWz72P6OUf44nihvzjhAWECBaQIVhAhmABGYIFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZo1vC4rVrLzf8lZ0M026N16KzzW37PvcSAvw3wQIyBAvIECwgQ7CADMECMgQLyBAsIEOwgAzBAjIEC8j4upwOqHDCAjIEC8gQLCBDsIAMwQIyBAvIECwgQ7CADMECMgQLyBAsIEOwgAzBAjIEC8gQLCBDsIAMwQIyBAvIECwgQ7CADMECMgQLyBAsIEOwgIx/AdaLDUS95ey3AAAAAElFTkSuQmCC"
            
            # 解码base64数据并保存为图片
            img_data = base64.b64decode(base64_data)
            img_path = os.path.join(self.img_dir, f"test_{event.get_user_id()}.png")
            
            with open(img_path, "wb") as f:
                f.write(img_data)
            
            # 构建富媒体消息
            rich_media = {
                "type": "rich_media",
                "title": "测试图片",
                "description": "这是一个测试用的二维码图片",
                "image": {
                    "path": img_path,
                    "type": "image/png"
                }
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
