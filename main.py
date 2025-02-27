from astrbot.api.all import *
from typing import Dict
import aiohttp
import os
import hashlib
import asyncio
import json
from pathlib import Path
from datetime import datetime

@register("astrbot_plugin_QQbotbd", "QQ机器人", "QQ官方机器人Webhook插件", "1.0.0", "https://github.com/913926816/astrbot_plugin_QQbotbd")
class QQWebhookPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.robot_uin = None
        self.robot_appid = None
        self.cache_dir = Path("data/cache/images")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.login_codes = {} # 存储用户登录code
        
    async def delete_file_after_delay(self, file_path: Path, delay: int = 30):
        """延迟删除文件"""
        await asyncio.sleep(delay)
        try:
            if file_path.exists():
                os.remove(file_path)
                logger.info(f"已删除缓存文件: {file_path}")
        except Exception as e:
            logger.error(f"删除缓存文件失败: {str(e)}")
        
    async def download_image(self, url: str, user_id: str) -> str:
        """下载图片并缓存到本地"""
        # 使用用户ID和URL的组合作为缓存文件名
        file_name = f"{user_id}_{hashlib.md5(url.encode()).hexdigest()}.jpg"
        cache_path = self.cache_dir / file_name
        
        # 下载并缓存图片
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(cache_path, "wb") as f:
                        f.write(content)
                    
                    # 启动定时删除任务
                    asyncio.create_task(self.delete_file_after_delay(cache_path))
                    
                    return str(cache_path)
                else:
                    raise Exception(f"下载图片失败: {response.status}")
        
    async def get_login_qr(self, user_id: str) -> Dict:
        """获取QQ登录二维码"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.yuafeng.cn/API/ly/music_login.php?type=getCode") as response:
                if response.status == 200:
                    data = await response.json()
                    if data["code"] == 0:
                        # 保存code用于后续验证
                        self.login_codes[user_id] = data["data"]["code"]
                        return {
                            "qr_img": data["data"]["qr_Img"],
                            "code": data["data"]["code"]
                        }
                raise Exception("获取登录二维码失败")

    async def check_login_status(self, user_id: str) -> Dict:
        """检查登录状态"""
        code = self.login_codes.get(user_id)
        if not code:
            raise Exception("未找到登录code,请先获取二维码")
            
        async with aiohttp.ClientSession() as session:
            url = f"https://api.yuafeng.cn/API/ly/music_login.php?type=getTicket&code={code}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                raise Exception("检查登录状态失败")

    @command("login")
    async def login(self, event: AstrMessageEvent):
        """QQ登录指令"""
        try:
            user_id = event.get_sender_id()
            
            # 获取登录二维码
            login_data = await self.get_login_qr(user_id)
            
            # 下载并缓存二维码图片
            qr_path = await self.download_image(login_data["qr_img"], user_id)
            
            # 发送二维码和提示
            chain = [
                At(qq=user_id),
                Plain("请扫描二维码登录(30秒内有效):\n"),
                Image.fromFileSystem(qr_path),
                Plain("\n扫码后请等待系统验证...")
            ]
            yield event.chain_result(chain)
            
            # 等待并检查登录状态
            for _ in range(6): # 最多等待30秒
                await asyncio.sleep(5)
                try:
                    status = await self.check_login_status(user_id)
                    if status.get("code") == 0:
                        # 登录成功,绑定UIN
                        self.robot_uin = status.get("data", {}).get("uin")
                        yield event.plain_result(f"登录成功! UIN: {self.robot_uin}")
                        return
                except Exception:
                    continue
                    
            # 超时未登录
            yield event.plain_result("登录超时,请重新尝试")
            
        except Exception as e:
            logger.error(f"登录出错: {str(e)}")
            yield event.plain_result(f"登录失败: {str(e)}")
        finally:
            # 清理登录code
            self.login_codes.pop(user_id, None)

    @command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        try:
            # 获取发送者ID
            user_id = event.get_sender_id()
            
            # 图片URL
            image_url = "https://www.aidroplet.cn/wp-content/uploads/2024/12/screenshot-20241225-094651.png"
            
            # 下载并缓存图片
            image_path = await self.download_image(image_url, user_id)
            
            # 构造消息链
            chain = [
                At(qq=user_id), # At 消息发送者
                Plain("来看这个图："), 
                Image.fromFileSystem(image_path), # 发送缓存的图片
                Plain("这是一个缓存的图片,将在30秒后自动删除。")
            ]
            yield event.chain_result(chain)
            
        except Exception as e:
            logger.error(f"处理图片出错: {str(e)}")
            yield event.plain_result("抱歉,图片处理出现错误。")
