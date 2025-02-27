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
        self.login_codes = {}  # 存储用户ID和登录code的映射
        
    async def get_login_qrcode(self, user_id: str) -> tuple[str, str]:
        """获取登录二维码"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.yuafeng.cn/API/ly/music_login.php?type=getCode") as response:
                    if response.status == 200:
                        # 先获取原始文本
                        text = await response.text()
                        logger.info(f"获取二维码原始响应: {text}")
                        
                        try:
                            data = json.loads(text)
                            logger.info(f"解析JSON响应: {data}")
                            
                            if "data" in data and "qr_Img" in data["data"]:
                                qr_img_base64 = data["data"]["qr_Img"]
                                login_code = data["data"]["code"]
                                
                                # 将base64转换为图片并保存
                                import base64
                                img_data = base64.b64decode(qr_img_base64)
                                
                                # 使用用户ID和时间戳作为文件名
                                file_name = f"qrcode_{user_id}_{int(datetime.now().timestamp())}.jpg"
                                cache_path = self.cache_dir / file_name
                                
                                # 保存图片
                                with open(cache_path, "wb") as f:
                                    f.write(img_data)
                                    
                                # 启动定时删除任务
                                asyncio.create_task(self.delete_file_after_delay(cache_path))
                                
                                # 保存code用于后续验证
                                self.login_codes[user_id] = login_code
                                return str(cache_path), login_code
                                
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON解析失败: {e}, 原始响应: {text}")
                            
                    logger.error(f"获取二维码失败: status={response.status}, content_type={response.content_type}")
        except Exception as e:
            logger.error(f"获取二维码异常: {str(e)}")
        raise Exception("获取登录二维码失败")

    async def check_login_status(self, user_id: str) -> bool:
        """检查登录状态"""
        try:
            if user_id not in self.login_codes:
                logger.warning(f"用户 {user_id} 的登录code不存在")
                return False
                
            code = self.login_codes[user_id]
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.yuafeng.cn/API/ly/music_login.php?type=getTicket&code={code}") as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"检查登录状态响应: {data}")
                        if data.get("code") == 0:
                            self.robot_uin = data.get("data", {}).get("uin")
                            return True
                    return False
        except Exception as e:
            logger.error(f"检查登录状态异常: {str(e)}")
            return False

    async def login_check_loop(self, event: AstrMessageEvent, user_id: str):
        """循环检查登录状态"""
        try:
            for i in range(30):  # 30秒超时
                if await self.check_login_status(user_id):
                    yield event.plain_result(f"登录成功! UIN: {self.robot_uin}")
                    return
                if i % 5 == 0:  # 每5秒提示一次
                    yield event.plain_result("正在等待扫码...")
                await asyncio.sleep(1)
            yield event.plain_result("登录超时,请重试")
        except Exception as e:
            logger.error(f"登录检查循环异常: {str(e)}")
            yield event.plain_result("登录检查出现错误")
        finally:
            # 清理登录code
            self.login_codes.pop(user_id, None)
        
    @command("login")
    async def login(self, event: AstrMessageEvent):
        """QQ登录指令"""
        try:
            user_id = event.get_sender_id()
            logger.info(f"用户 {user_id} 开始登录流程")
            
            # 获取登录二维码并保存到本地
            image_path, login_code = await self.get_login_qrcode(user_id)
            logger.info(f"二维码已保存到: {image_path}, code: {login_code}")
            
            # 发送二维码
            chain = [
                At(qq=user_id),
                Plain("请扫描二维码登录(30秒内有效)：\n"), 
                Image.fromFileSystem(image_path),
                Plain("\n正在等待扫码...")
            ]
            yield event.chain_result(chain)
            
            # 启动登录状态检查
            await self.login_check_loop(event, user_id)
            
        except Exception as e:
            logger.error(f"登录处理出错: {str(e)}")
            yield event.plain_result("登录过程出现错误,请稍后重试")
            # 清理登录code
            self.login_codes.pop(user_id, None)

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
