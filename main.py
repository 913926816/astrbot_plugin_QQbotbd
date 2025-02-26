from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import re
import json
import os
import time
import datetime
import aiohttp
import asyncio
import hashlib
import random
import string
import base64

# 定义默认配置
DEFAULT_CONFIG = {
    "qq_access_token": "",  # QQ API访问令牌
    "auto_verify": True,    # 是否自动验证扫码登录的QQ号
    "qrcode_timeout": 5     # 二维码有效期(分钟)
}

@register("qqbind", "QQ绑定插件", "一个通过二维码登录绑定QQ号的插件", "1.0.0", "https://github.com/yourusername/astrbot_plugin_QQbotbd")
class QQBindPlugin(Star):
    def __init__(self, context: Context):
        """初始化QQ绑定插件
        
        Args:
            context (Context): AstrBot上下文对象，包含大多数组件
        """
        super().__init__(context)
        self.data_file = os.path.join(os.path.dirname(__file__), "qqbind_data.json")
        self.config_file = os.path.join(os.path.dirname(__file__), "config.json")
        self.bind_data = self._load_data()
        
        # 尝试从AstrBot配置系统中读取配置
        try:
            if hasattr(context, 'get_plugin_config') and callable(context.get_plugin_config):
                # 如果AstrBot提供了get_plugin_config方法，使用它获取配置
                astrbot_config = context.get_plugin_config("astrbot_plugin_QQbotbd")
                if astrbot_config:
                    # 将AstrBot配置合并到本地配置
                    self.config = self._merge_config(astrbot_config)
                    logger.info("已从AstrBot配置系统加载配置")
                else:
                    # 如果AstrBot没有配置，使用本地配置
                    self.config = self._load_config()
            else:
                # 如果AstrBot没有提供get_plugin_config方法，使用本地配置
                self.config = self._load_config()
        except Exception as e:
            logger.error(f"从AstrBot配置系统加载配置失败: {e}")
            self.config = self._load_config()
        
        self.login_sessions = {}  # 存储登录会话信息
        self.api_base_url = "https://api.yuafeng.cn/API/ly"
        self.qrcode_api_url = f"{self.api_base_url}/qrcode.php"  # 二维码获取接口
        self.check_login_api_url = f"{self.api_base_url}/check_login.php"  # 检查登录状态接口
        
        logger.info(f"QQ绑定插件已加载，数据条目数: {len(self.bind_data)}")
    
    def _load_data(self):
        """加载绑定数据，如果文件不存在则返回空字典"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载QQ绑定数据失败: {e}")
                return {}
        return {}
    
    def _save_data(self):
        """保存绑定数据到文件"""
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.bind_data, f, ensure_ascii=False, indent=2)
            logger.debug("QQ绑定数据保存成功")
        except Exception as e:
            logger.error(f"保存QQ绑定数据失败: {e}")
    
    def _load_config(self):
        """加载配置，如果文件不存在则创建默认配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # 确保所有默认配置项都存在
                    for key, value in DEFAULT_CONFIG.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                logger.error(f"加载配置失败: {e}")
                return DEFAULT_CONFIG.copy()
        else:
            # 创建默认配置文件
            try:
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
                logger.info("已创建默认配置文件")
            except Exception as e:
                logger.error(f"创建默认配置文件失败: {e}")
            return DEFAULT_CONFIG.copy()
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.debug("配置保存成功")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    def get_config(self, key, default=None):
        """获取配置项的值
        
        Args:
            key (str): 配置项的键
            default: 默认值，如果配置项不存在则返回此值
            
        Returns:
            配置项的值
        """
        return self.config.get(key, default)
    
    def set_config(self, key, value):
        """设置配置项的值
        
        Args:
            key (str): 配置项的键
            value: 配置项的值
        """
        self.config[key] = value
        self._save_config()
    
    def user_openid(self, event):
        """从事件中获取用户OpenID"""
        try:
            # 尝试使用get_sender_id方法
            if hasattr(event, 'get_sender_id') and callable(event.get_sender_id):
                sender_id = event.get_sender_id()
                logger.debug(f"从get_sender_id方法获取: {sender_id}")
                if sender_id:
                    return sender_id
            
            # 直接尝试获取user_openid属性
            if hasattr(event, 'user_openid'):
                openid = event.user_openid
                logger.debug(f"直接从user_openid属性获取: {openid}")
                return openid
            
            # 记录事件类型和属性，帮助调试
            event_type = type(event).__name__
            event_attrs = dir(event)
            logger.debug(f"事件类型: {event_type}, 属性: {event_attrs}")
            
            # 尝试从日志字符串中提取OpenID
            event_str = str(event)
            openid_match = re.search(r'\[qq_official_webhook\]\s+([A-F0-9]{32})', event_str)
            if openid_match:
                openid = openid_match.group(1)
                logger.debug(f"从事件字符串中提取OpenID: {openid}")
                return openid
            
            # 记录无法获取OpenID的情况
            logger.error(f"无法从事件中获取用户OpenID: {event_type}")
            return None
        except Exception as e:
            logger.error(f"获取用户OpenID时出错: {e}")
            return None
    
    def get_qq_by_openid(self, openid):
        """根据OpenID获取QQ号
        
        Args:
            openid (str): 用户的OpenID
            
        Returns:
            str or None: 查找到的QQ号，如果未找到则返回None
        """
        if openid and openid in self.bind_data:
            return self.bind_data[openid]["qq_number"]
        return None
    
    def generate_session_id(self):
        """生成随机会话ID"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    async def get_qrcode(self):
        """获取QQ登录二维码
        
        Returns:
            tuple: (成功与否, 二维码图片数据或错误消息, 会话标识)
        """
        try:
            # 生成一个唯一的会话ID
            session_id = self.generate_session_id()
            
            # 构建API请求URL
            api_url = f"{self.api_base_url}/qrcode.php"
            
            async with aiohttp.ClientSession() as session:
                params = {
                    "type": "qq",
                    "session": session_id,
                    "return_type": "json"  # 尝试请求JSON格式的响应
                }
                
                async with session.get(api_url, params=params) as response:
                    if response.status != 200:
                        return False, f"API请求失败，状态码: {response.status}", None
                    
                    # 尝试解析响应
                    try:
                        # 首先尝试解析为JSON
                        data = await response.json()
                        logger.debug(f"获取二维码API返回JSON: {data}")
                        
                        # 检查是否包含qr_Img字段
                        if "qr_Img" in data:
                            qr_img = data["qr_Img"]
                            logger.debug(f"从JSON响应中获取到二维码图片: {qr_img[:30]}...")
                            return True, qr_img, session_id
                    except:
                        # 如果解析JSON失败，尝试获取原始响应
                        content = await response.read()
                        logger.debug(f"获取二维码API返回二进制数据，长度: {len(content)}")
                        
                        # 假设返回的是图片数据
                        if content and len(content) > 100:  # 简单检查是否是有效的图片数据
                            # 将二进制数据转换为Base64编码
                            qr_img_base64 = base64.b64encode(content).decode('utf-8')
                            return True, f"data:image/png;base64,{qr_img_base64}", session_id
            
            # 如果上述方法都失败，回退到直接使用URL
            qrcode_url = f"{api_url}?type=qq&session={session_id}"
            logger.debug(f"回退到使用二维码URL: {qrcode_url}")
            return True, qrcode_url, session_id
        except Exception as e:
            logger.error(f"获取QQ登录二维码时出错: {e}")
            return False, f"获取二维码过程出错: {str(e)}", None
    
    async def check_login_status(self, session_id):
        """检查QQ登录状态
        
        Args:
            session_id (str): 会话标识
            
        Returns:
            tuple: (成功与否, 消息, QQ号)
        """
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "session": session_id,
                    "type": "qq"
                }
                
                check_url = f"{self.api_base_url}/check_login.php"
                async with session.get(check_url, params=params) as response:
                    if response.status != 200:
                        return False, f"API请求失败，状态码: {response.status}", None
                    
                    # 尝试以文本方式读取响应
                    text = await response.text()
                    logger.debug(f"检查登录状态API返回: {text}")
                    
                    # 检查是否包含成功登录的标识
                    if "登录成功" in text or "success" in text.lower():
                        # 尝试从响应中提取QQ号
                        qq_match = re.search(r'QQ号[：:]\s*(\d{5,11})', text)
                        if qq_match:
                            qq_number = qq_match.group(1)
                        else:
                            # 如果无法提取，使用一个随机QQ号作为占位符
                            qq_number = f"unknown_{int(time.time())}"
                        
                        return True, "登录成功", qq_number
                    elif "等待扫码" in text or "waiting" in text.lower():
                        return False, "等待扫码登录", None
                    else:
                        return False, "检查登录状态失败，未知响应", None
        except Exception as e:
            logger.error(f"检查QQ登录状态时出错: {e}")
            return False, f"检查登录状态过程出错: {str(e)}", None
    
    @filter.command("qqbind")
    async def qq_bind(self, event: AstrMessageEvent):
        '''开始QQ绑定流程 - 使用方法: /qqbind'''
        user_id = self.user_openid(event)
        if not user_id:
            yield event.plain_result("无法获取您的用户ID，绑定失败")
            return
        
        # 检查是否已经绑定
        if user_id in self.bind_data:
            qq_number = self.bind_data[user_id]["qq_number"]
            yield event.plain_result(f"您已绑定QQ号: {qq_number}\n如需重新绑定，请先使用 /qqunbind 解绑")
            return
        
        # 获取QQ登录二维码
        success, qrcode_data, session_id = await self.get_qrcode()
        
        if not success:
            yield event.plain_result(f"获取QQ登录二维码失败: {qrcode_data}")
            return
        
        # 保存会话信息
        self.login_sessions[user_id] = {
            "session_id": session_id,
            "timestamp": time.time(),
            "qrcode_data": qrcode_data
        }
        
        # 发送二维码图片
        try:
            # 尝试使用QQ开放平台API发送图片
            app_id = self.get_config("app_id", "")
            app_secret = self.get_config("app_secret", "")
            
            if app_id and app_secret:
                # 如果qrcode_data是URL，尝试上传并发送
                if qrcode_data.startswith(('http://', 'https://')):
                    # 上传图片获取media_id
                    upload_success, media_id = await self.upload_image_to_qq(qrcode_data)
                    
                    if upload_success:
                        # 使用media_id发送图片消息
                        send_success, response = await self.send_image_message(user_id, media_id)
                        
                        if send_success:
                            logger.info(f"使用QQ开放平台API成功发送二维码图片")
                        else:
                            # 如果发送失败，回退到使用AstrBot的方法
                            logger.warning(f"使用QQ开放平台API发送图片失败: {response}，回退到使用AstrBot方法")
                            yield event.image_result(qrcode_data)
                    else:
                        # 如果上传失败，回退到使用AstrBot的方法
                        logger.warning(f"上传图片到QQ服务器失败: {media_id}，回退到使用AstrBot方法")
                        yield event.image_result(qrcode_data)
                else:
                    # 如果不是URL，直接使用AstrBot的方法
                    yield event.image_result(qrcode_data)
            else:
                # 如果没有配置app_id或app_secret，使用AstrBot的方法
                logger.info("未配置app_id或app_secret，使用AstrBot方法发送图片")
                
                # 根据qrcode_data的格式选择合适的发送方式
                if qrcode_data.startswith('data:image'):
                    # 如果是Base64编码的图片数据，直接发送
                    yield event.image_result(qrcode_data)
                elif qrcode_data.startswith(('http://', 'https://')):
                    # 如果是URL，直接发送
                    yield event.image_result(qrcode_data)
                else:
                    # 尝试作为Base64编码处理
                    try:
                        # 检查是否已经是Base64编码
                        base64.b64decode(qrcode_data)
                        # 如果解码成功，说明是有效的Base64编码
                        yield event.image_result(f"data:image/png;base64,{qrcode_data}")
                    except:
                        # 如果解码失败，可能不是Base64编码，尝试作为URL发送
                        logger.warning(f"无法解析二维码数据，尝试作为URL发送: {qrcode_data[:30]}...")
                        yield event.image_result(qrcode_data)
        except Exception as e:
            logger.error(f"发送二维码图片时出错: {e}")
            # 如果发送图片失败，尝试发送二维码URL
            yield event.plain_result(f"发送二维码图片失败，请访问以下链接获取二维码：\n{self.qrcode_api_url}?type=qq&session={session_id}")
            return
        
        # 获取配置的超时时间
        timeout_minutes = self.get_config("qrcode_timeout", 5)
        
        yield event.plain_result(
            f"请使用QQ扫描上方二维码登录\n"
            f"登录成功后，您的QQ号将自动绑定到您的账号\n"
            f"二维码有效期为{timeout_minutes}分钟，请尽快扫码\n\n"
            f"您可以发送 'cancel' 取消绑定流程"
        )
        
        # 启动异步任务检查登录状态
        asyncio.create_task(self.poll_login_status(event, user_id))
    
    async def poll_login_status(self, event, user_id):
        """轮询检查登录状态
        
        Args:
            event (AstrMessageEvent): 原始消息事件
            user_id (str): 用户的OpenID
        """
        if user_id not in self.login_sessions:
            logger.error(f"用户 {user_id} 没有活跃的登录会话")
            return
        
        session_id = self.login_sessions[user_id]["session_id"]
        start_time = self.login_sessions[user_id]["timestamp"]
        
        # 获取配置的超时时间（分钟）
        timeout_minutes = self.get_config("qrcode_timeout", 5)
        
        # 每3秒检查一次，最多检查timeout_minutes分钟
        max_checks = timeout_minutes * 20  # 每分钟20次检查
        for i in range(max_checks):
            # 检查会话是否已被取消
            if user_id not in self.login_sessions:
                logger.info(f"用户 {user_id} 的登录会话已被取消")
                return
            
            # 检查是否超时
            current_time = time.time()
            if current_time - start_time > timeout_minutes * 60:
                await event.reply(f"二维码已过期，请重新发送 /qqbind 获取新的二维码")
                del self.login_sessions[user_id]
                return
            
            # 检查登录状态
            success, message, qq_number = await self.check_login_status(session_id)
            
            if success:
                # 检查QQ号是否已被其他用户绑定
                for openid, data in self.bind_data.items():
                    if openid != user_id and data.get("qq_number") == qq_number:
                        await event.reply(f"该QQ号已被其他用户绑定，请使用其他QQ号")
                        del self.login_sessions[user_id]
                        return
                
                # 绑定QQ号到用户的OpenID
                self.bind_data[user_id] = {
                    "qq_number": qq_number,
                    "bind_time": int(time.time()),
                    "verified": self.get_config("auto_verify", True)  # 根据配置决定是否自动验证
                }
                self._save_data()
                
                # 清理会话
                del self.login_sessions[user_id]
                
                logger.info(f"用户 {user_id} 绑定QQ号 {qq_number} 成功")
                await event.reply(f"QQ登录成功！\n您的QQ号 {qq_number} 已成功绑定")
                return
            
            # 等待3秒后再次检查
            await asyncio.sleep(3)
        
        # 如果达到最大检查次数仍未成功，则超时
        if user_id in self.login_sessions:
            await event.reply(f"登录超时，请重新发送 /qqbind 获取新的二维码")
            del self.login_sessions[user_id]
    
    @filter.regex(r'.*')
    async def handle_all_messages(self, event: AstrMessageEvent):
        '''处理所有消息，包括绑定流程中的消息'''
        # 忽略命令消息，因为它们会被其他处理器处理
        message = event.message_str.strip()
        if message.startswith('/'):
            return
        
        user_id = self.user_openid(event)
        if not user_id or user_id not in self.login_sessions:
            return  # 不是绑定流程中的消息
        
        # 检查是否取消
        if message.lower() == 'cancel':
            del self.login_sessions[user_id]
            yield event.plain_result("已取消绑定流程")
            return
    
    @filter.command("qqbindsimple")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def qq_bind_simple(self, event: AstrMessageEvent):
        '''简单绑定QQ号（无需验证）- 仅管理员可用 - 使用方法: /qqbindsimple [QQ号]'''
        user_id = self.user_openid(event)
        if not user_id:
            yield event.plain_result("无法获取您的用户ID，绑定失败")
            return
            
        message_str = event.message_str.strip()
        
        # 更灵活的正则表达式，尝试多种可能的格式
        match = re.search(r'(?:/qqbindsimple|qqbindsimple)\s*(\d{5,11})', message_str)
        if not match:
            # 尝试直接提取数字
            digits_match = re.search(r'(\d{5,11})', message_str)
            if digits_match:
                qq_number = digits_match.group(1)
            else:
                yield event.plain_result("请提供正确的QQ号，格式：/qqbindsimple [QQ号]")
                return
        else:
            qq_number = match.group(1)
        
        # 绑定QQ号到用户的OpenID
        self.bind_data[user_id] = {
            "qq_number": qq_number,
            "bind_time": int(time.time()),
            "verified": False  # 标记为未验证
        }
        self._save_data()
        
        logger.info(f"管理员为用户 {user_id} 绑定QQ号 {qq_number}")
        yield event.plain_result(f"已为用户绑定QQ号\n用户ID：{user_id}\nQQ号：{qq_number}\n(未验证)")
    
    @filter.command("qqunbind")
    async def qq_unbind(self, event: AstrMessageEvent):
        '''解绑QQ号 - 使用方法: /qqunbind'''
        user_id = self.user_openid(event)
        
        if not user_id:
            yield event.plain_result("无法获取您的用户ID，解绑失败")
            return
        
        if user_id not in self.bind_data:
            yield event.plain_result("您尚未绑定QQ号")
            return
        
        qq_number = self.bind_data[user_id]["qq_number"]
        del self.bind_data[user_id]
        self._save_data()
        
        logger.info(f"用户 {user_id} 解绑QQ号 {qq_number} 成功")
        yield event.plain_result(f"成功解绑QQ号: {qq_number}")
    
    @filter.command("qqinfo")
    async def qq_info(self, event: AstrMessageEvent):
        '''查询已绑定的QQ号 - 使用方法: /qqinfo'''
        user_id = self.user_openid(event)
        if not user_id:
            yield event.plain_result("无法获取您的用户ID，查询失败")
            return
        
        if user_id not in self.bind_data:
            yield event.plain_result("您尚未绑定QQ号，请使用 /qqbind 进行绑定")
            return
        
        qq_data = self.bind_data[user_id]
        qq_number = qq_data["qq_number"]
        bind_time = qq_data.get("bind_time", 0)
        verified = qq_data.get("verified", False)
        
        bind_time_str = datetime.datetime.fromtimestamp(bind_time).strftime("%Y-%m-%d %H:%M:%S") if bind_time else "未知时间"
        verified_str = "已验证" if verified else "未验证"
        
        yield event.plain_result(f"您的QQID为：{user_id}\n您绑定的QQ为：{qq_number}\n绑定时间：{bind_time_str}\n验证状态：{verified_str}")
    
    @filter.command("qqlist", priority=1)
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def qq_list(self, event: AstrMessageEvent):
        '''列出所有绑定记录 - 仅管理员可用'''
        if len(self.bind_data) == 0:
            yield event.plain_result("当前没有任何绑定记录")
            return
        
        result = "所有QQ绑定记录：\n"
        for openid, data in self.bind_data.items():
            result += f"ID: {openid}\nQQ号: {data['qq_number']}\n"
            if 'bind_time' in data:
                bind_time_str = datetime.datetime.fromtimestamp(data['bind_time']).strftime("%Y-%m-%d %H:%M:%S")
                result += f"绑定时间: {bind_time_str}\n"
            verified = data.get("verified", False)
            result += f"验证状态: {'已验证' if verified else '未验证'}\n"
            result += "----------\n"
        
        # 如果文本过长，转为图片发送
        if len(result) > 1000:
            try:
                url = await self.text_to_image(result)
                yield event.image_result(url)
            except Exception as e:
                logger.error(f"转换文本到图片失败: {e}")
                yield event.plain_result("绑定记录过多，转换图片失败，请查看日志")
        else:
            yield event.plain_result(result)
    
    @filter.command("qqhelp")
    async def qq_help(self, event: AstrMessageEvent):
        '''QQ绑定插件帮助 - 使用方法: /qqhelp'''
        help_text = """QQ绑定插件使用帮助：
1. 开始绑定流程：/qqbind (将生成二维码，扫码登录后自动绑定)
2. 解绑QQ号：/qqunbind
3. 查询绑定信息：/qqinfo
4. 查看帮助：/qqhelp

管理员命令：
1. 查询所有绑定记录：/qqlist
2. 查询指定ID的QQ号：/whoisqq [ID]
3. 简单绑定（无需验证）：/qqbindsimple [QQ号]

注意：绑定QQ号需要扫描二维码登录，以确保您是QQ号的所有者。
如果二维码登录失败，管理员可以使用简单绑定命令帮助您绑定。"""
        
        yield event.plain_result(help_text)
    
    @filter.command("whoisqq")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def who_is_qq(self, event: AstrMessageEvent):
        '''查询指定ID对应的QQ号 - 仅管理员可用'''
        message_str = event.message_str.strip()
        
        # 检查是否提供了ID
        match = re.search(r'/whoisqq\s+(.+)', message_str)
        if not match:
            yield event.plain_result("请提供正确的ID，格式：/whoisqq [ID]")
            return
        
        target_id = match.group(1)
        
        if target_id not in self.bind_data:
            yield event.plain_result(f"未找到ID {target_id} 绑定的QQ号")
            return
        
        qq_data = self.bind_data[target_id]
        qq_number = qq_data["qq_number"]
        verified = qq_data.get("verified", False)
        
        yield event.plain_result(f"ID {target_id} 绑定的QQ号为: {qq_number}\n验证状态: {'已验证' if verified else '未验证'}")

    async def upload_image_to_qq(self, image_path_or_url):
        """将图片上传到QQ服务器获取media_id
        
        Args:
            image_path_or_url (str): 图片路径或URL
            
        Returns:
            tuple: (成功与否, media_id或错误消息)
        """
        try:
            # 获取access_token
            token_success, token_result = await self.get_access_token()
            if not token_success:
                return False, token_result
            
            access_token = token_result
            
            # 构建API请求URL
            api_url = "https://api.q.qq.com/api/media/upload"
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {access_token}"}
                
                # 根据输入类型选择上传方式
                if image_path_or_url.startswith(('http://', 'https://')):
                    # 如果是URL，先下载图片
                    async with session.get(image_path_or_url) as response:
                        if response.status != 200:
                            return False, f"下载图片失败，状态码: {response.status}"
                        
                        image_data = await response.read()
                        
                        # 准备上传
                        data = aiohttp.FormData()
                        data.add_field('media', image_data, 
                                      filename='qrcode.png',
                                      content_type='image/png')
                        data.add_field('type', 'image')
                        
                        # 上传图片
                        async with session.post(api_url, headers=headers, data=data) as upload_response:
                            if upload_response.status != 200:
                                return False, f"上传图片失败，状态码: {upload_response.status}"
                            
                            result = await upload_response.json()
                            if "media_id" in result:
                                return True, result["media_id"]
                            else:
                                return False, f"上传图片失败: {result}"
                else:
                    # 如果是本地路径，直接上传
                    if os.path.exists(image_path_or_url):
                        with open(image_path_or_url, 'rb') as f:
                            image_data = f.read()
                        
                        # 准备上传
                        data = aiohttp.FormData()
                        data.add_field('media', image_data, 
                                      filename=os.path.basename(image_path_or_url),
                                      content_type='image/png')
                        data.add_field('type', 'image')
                        
                        # 上传图片
                        async with session.post(api_url, headers=headers, data=data) as upload_response:
                            if upload_response.status != 200:
                                return False, f"上传图片失败，状态码: {upload_response.status}"
                            
                            result = await upload_response.json()
                            if "media_id" in result:
                                return True, result["media_id"]
                            else:
                                return False, f"上传图片失败: {result}"
                    else:
                        return False, f"图片路径不存在: {image_path_or_url}"
        except Exception as e:
            logger.error(f"上传图片到QQ服务器时出错: {e}")
            return False, f"上传图片过程出错: {str(e)}"

    async def send_image_message(self, target_openid, media_id):
        """使用media_id发送图片消息
        
        Args:
            target_openid (str): 目标用户的OpenID
            media_id (str): 图片的media_id
            
        Returns:
            tuple: (成功与否, 响应或错误消息)
        """
        try:
            # 获取access_token
            token_success, token_result = await self.get_access_token()
            if not token_success:
                return False, token_result
            
            access_token = token_result
            
            # 构建API请求URL
            api_url = "https://api.q.qq.com/api/v2/bot/message/send"
            
            # 准备请求数据
            data = {
                "access_token": access_token,
                "msg_type": "image",
                "content": {"media_id": media_id},
                "target": {"openid": target_openid}
            }
            
            # 发送请求
            async with aiohttp.ClientSession() as session:
                headers = {"Content-Type": "application/json"}
                async with session.post(api_url, headers=headers, json=data) as response:
                    if response.status != 200:
                        return False, f"发送图片消息失败，状态码: {response.status}"
                    
                    result = await response.json()
                    return True, result
        except Exception as e:
            logger.error(f"发送图片消息时出错: {e}")
            return False, f"发送图片消息过程出错: {str(e)}"

    @filter.command("qqconfig")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def qq_config(self, event: AstrMessageEvent):
        '''设置或查看QQ绑定插件配置 - 仅管理员可用 - 使用方法: /qqconfig [key] [value]'''
        message_str = event.message_str.strip()
        
        # 检查是否提供了参数
        match = re.search(r'/qqconfig\s+([a-zA-Z_]+)(?:\s+(.+))?', message_str)
        
        if not match:
            # 如果没有提供参数，显示所有配置
            config_text = "当前配置：\n"
            for key, value in self.config.items():
                config_text += f"{key}: {value}\n"
            
            config_text += "\n可用配置项：\n"
            config_text += "qq_access_token: QQ API访问令牌\n"
            config_text += "auto_verify: 是否自动验证扫码登录的QQ号 (true/false)\n"
            config_text += "qrcode_timeout: 二维码有效期(分钟)\n"
            
            config_text += "\n使用方法：\n"
            config_text += "/qqconfig [key] [value] - 设置配置项\n"
            config_text += "/qqconfig [key] - 查看配置项\n"
            
            yield event.plain_result(config_text)
            return
        
        key = match.group(1)
        value = match.group(2) if match.group(2) else None
        
        if key not in DEFAULT_CONFIG:
            yield event.plain_result(f"未知配置项: {key}\n可用配置项: {', '.join(DEFAULT_CONFIG.keys())}")
            return
        
        if value is None:
            # 如果没有提供值，显示当前配置
            current_value = self.get_config(key)
            yield event.plain_result(f"配置项 {key} 的当前值为: {current_value}")
            return
        
        # 根据配置项类型转换值
        if key == "auto_verify":
            value = value.lower() in ("true", "yes", "1", "on")
        elif key == "qrcode_timeout":
            try:
                value = int(value)
            except ValueError:
                yield event.plain_result(f"无效的值: {value}，应为整数")
                return
        
        # 设置配置项
        self.set_config(key, value)
        yield event.plain_result(f"已设置配置项 {key} 的值为: {value}")

    def _merge_config(self, astrbot_config):
        """将AstrBot配置合并到本地配置
        
        Args:
            astrbot_config (dict): AstrBot配置
            
        Returns:
            dict: 合并后的配置
        """
        # 加载本地配置
        local_config = self._load_config()
        
        # 将AstrBot配置合并到本地配置
        for key, value in astrbot_config.items():
            if key in DEFAULT_CONFIG:
                local_config[key] = value
        
        # 保存合并后的配置
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(local_config, f, ensure_ascii=False, indent=2)
            logger.debug("配置保存成功")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
        
        return local_config

    async def get_access_token(self):
        """获取QQ API access_token
        
        Returns:
            tuple: (成功与否, access_token或错误消息)
        """
        try:
            app_id = self.get_config("app_id", "")
            app_secret = self.get_config("app_secret", "")
            
            if not app_id or not app_secret:
                logger.error("未配置app_id或app_secret，无法获取access_token")
                return False, "未配置app_id或app_secret，无法获取access_token"
            
            # 检查是否已有有效的access_token
            if hasattr(self, 'access_token') and hasattr(self, 'token_expires_at'):
                # 如果token还有超过10分钟的有效期，直接使用
                if time.time() + 600 < self.token_expires_at:
                    return True, self.access_token
            
            # 获取新的access_token
            url = "https://api.q.qq.com/api/getToken"
            params = {
                "grant_type": "client_credential",
                "appid": app_id,
                "secret": app_secret
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"获取access_token失败，状态码: {response.status}")
                        return False, f"获取access_token失败，状态码: {response.status}"
                    
                    result = await response.json()
                    if "access_token" not in result:
                        logger.error(f"获取access_token失败: {result}")
                        return False, f"获取access_token失败: {result}"
                    
                    # 保存access_token和过期时间
                    self.access_token = result["access_token"]
                    # 假设token有效期为2小时，提前10分钟刷新
                    self.token_expires_at = time.time() + 7200 - 600
                    logger.info("成功获取access_token")
                    return True, self.access_token
        except Exception as e:
            logger.error(f"获取access_token时出错: {e}")
            return False, f"获取access_token时出错: {str(e)}"
