from astrbot.api.all import *
from typing import Dict
import aiohttp
import os
import hashlib
from pathlib import Path

@register("astrbot_plugin_QQbotbd", "QQ机器人", "QQ官方机器人Webhook插件", "1.0.0", "https://github.com/913926816/astrbot_plugin_QQbotbd")
class QQWebhookPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.robot_uin = None
        self.robot_appid = None
        self.cache_dir = Path("data/cache/images")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    async def download_image(self, url: str) -> str:
        """下载图片并缓存到本地"""
        # 使用URL的MD5作为缓存文件名
        file_name = hashlib.md5(url.encode()).hexdigest() + ".jpg"
        cache_path = self.cache_dir / file_name
        
        # 如果缓存存在则直接返回
        if cache_path.exists():
            return str(cache_path)
            
        # 下载并缓存图片
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(cache_path, "wb") as f:
                        f.write(content)
                    return str(cache_path)
                else:
                    raise Exception(f"下载图片失败: {response.status}")
        
    @command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        try:
            # 图片URL
            image_url = "https://example.com/image.jpg"
            
            # 下载并缓存图片
            image_path = await self.download_image(image_url)
            
            # 构造消息链
            chain = [
                At(qq=event.get_sender_id()), # At 消息发送者
                Plain("来看这个图："), 
                Image.fromFileSystem(image_path), # 发送缓存的图片
                Plain("这是一个缓存的图片。")
            ]
            yield event.chain_result(chain)
            
        except Exception as e:
            logger.error(f"处理图片出错: {str(e)}")
            yield event.plain_result("抱歉,图片处理出现错误。")
