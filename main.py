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
        self.bind_data = self._load_data()
        
        # 使用默认配置
        self.config = DEFAULT_CONFIG.copy()
        
        self.login_sessions = {}  # 存储登录会话信息
        
        logger.info(f"QQ绑定插件已加载，数据条目数: {len(self.bind_data)}")
    
    def _load_data(self):
        """加载绑定数据，如果文件不存在则返回空字典"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_data(self):
        """保存绑定数据到文件"""
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.bind_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def get_config(self, key, default=None):
        """获取配置项的值
        
        Args:
            key (str): 配置项的键
            default: 默认值，如果配置项不存在则返回此值
            
        Returns:
            配置项的值
        """
        return self.config.get(key, default)
    
    def user_openid(self, event):
        """从事件中获取用户OpenID"""
        try:
            # 尝试获取user_id属性(astrbot优先使用)
            if hasattr(event, 'user_id') and event.user_id:
                return event.user_id
                
            # 尝试使用get_sender_id方法
            if hasattr(event, 'get_sender_id') and callable(event.get_sender_id):
                sender_id = event.get_sender_id()
                if sender_id:
                    return sender_id
            
            # 直接尝试获取user_openid属性
            if hasattr(event, 'user_openid'):
                return event.user_openid
                
            # 尝试获取open_id属性
            if hasattr(event, 'open_id'):
                return event.open_id
            
            # 尝试从日志字符串中提取OpenID
            # event_str = str(event)
            # openid_match = re.search(r'\[qq_official_webhook\]\s+([A-F0-9]{32})', event_str)
            # if openid_match:
            #     return openid_match.group(1)
            
            return None
        except Exception:
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
            
            # 使用q.qq.com/qrcode/create接口获取qrcode
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                create_url = "https://q.qq.com/qrcode/create"
                data = {"type": 777}
                
                async with session.post(create_url, json=data, headers=headers) as response:
                    if response.status != 200:
                        return False, f"创建二维码失败，状态码: {response.status}", None
                    
                    try:
                        result = await response.json()
                        qrcode = result.get("qrcode")
                        image_url = result.get("image") or result.get("url") or result.get("qr_image") or result.get("qrImage")
                        ticket = result.get("ticket", "null")
                        
                        if not qrcode:
                            return False, "获取qrcode失败", None
                        
                        # 保存qrcode和ticket用于后续状态检查
                        self.login_sessions[session_id] = {
                            "qrcode": qrcode,
                            "ticket": ticket,
                            "timestamp": time.time()
                        }
                        
                        # 如果API直接返回了图片URL，使用它
                        if image_url:
                            return True, image_url, session_id
                        
                        # 否则，构建登录URL作为替代
                        login_url = f"https://q.qq.com/login/applist?client=qq&code={qrcode}&ticket={ticket}"
                        return True, login_url, session_id
                        
                    except Exception as e:
                        return False, f"解析API响应失败: {e}", None
                
        except Exception as e:
            return False, f"获取二维码过程出错: {str(e)}", None

    async def check_login_status(self, session_id):
        """检查QQ登录状态
        
        Args:
            session_id (str): 会话标识
            
        Returns:
            tuple: (成功与否, 消息, QQ号)
        """
        try:
            if session_id not in self.login_sessions:
                return False, "无效的会话ID", None
            
            session_data = self.login_sessions[session_id]
            qrcode = session_data.get("qrcode")
            ticket = session_data.get("ticket", "null")  # 获取ticket，默认为null
            
            if not qrcode:
                return False, "无效的qrcode", None
            
            # 使用q.qq.com/qrcode/get接口检查登录状态
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                check_url = "https://q.qq.com/qrcode/get"
                params = {  # 使用URL参数传递
                    "qrcode": qrcode,
                    "ticket": ticket
                }
                
                # 使用GET方法请求
                async with session.get(check_url, params=params, headers=headers) as response:
                    if response.status != 200:
                        return False, f"检查登录状态失败，状态码: {response.status}", None
                    
                    try:
                        result = await response.json()
                        status = result.get("status")
                        
                        if status == "scanned":
                            return False, "已扫码，等待确认", None
                        elif status == "confirmed":
                            qq_number = result.get("qq") or result.get("qq_number")
                            if not qq_number:
                                qq_number = f"unknown_{int(time.time())}"
                            return True, "登录成功", qq_number
                        else:
                            return False, "等待扫码", None
                            
                    except Exception as e:
                        return False, f"解析响应失败: {e}", None
                
        except Exception as e:
            return False, f"检查登录状态出错: {str(e)}", None
    
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
            # 尝试使用不同的方法发送图片
            if qrcode_data.startswith("data:image"):
                # 如果是Base64编码的图片
                yield event.image_result(qrcode_data)
            elif qrcode_data.startswith(("http://", "https://")):
                # 如果是URL
                yield event.image_result(qrcode_data)
            else:
                # 其他情况
                yield event.plain_result(f"请访问以下链接获取二维码：\n{qrcode_data}")
                
        except Exception as e:
            # 如果发送图片失败，尝试发送二维码URL
            yield event.plain_result(f"请访问以下链接获取二维码：\n{qrcode_data}")
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
                return
            
            # 检查是否超时
            current_time = time.time()
            if current_time - start_time > timeout_minutes * 60:
                try:
                    await event.reply(f"二维码已过期，请重新发送 /qqbind 获取新的二维码")
                except:
                    # 如果reply方法不可用，尝试使用其他方式回复
                    pass
                del self.login_sessions[user_id]
                return
            
            # 检查登录状态
            success, message, qq_number = await self.check_login_status(session_id)
            
            if success:
                # 检查QQ号是否已被其他用户绑定
                for openid, data in self.bind_data.items():
                    if openid != user_id and data.get("qq_number") == qq_number:
                        try:
                            await event.reply(f"该QQ号已被其他用户绑定，请使用其他QQ号")
                        except:
                            pass
                        del self.login_sessions[user_id]
                        return
                
                # 绑定QQ号到用户的OpenID
                self.bind_data[user_id] = {
                    "qq_number": qq_number,
                    "bind_time": int(time.time()),
                    "verified": True
                }
                self._save_data()
                
                # 清理会话
                del self.login_sessions[user_id]
                
                try:
                    await event.reply(f"QQ登录成功！\n您的QQ号 {qq_number} 已成功绑定")
                except:
                    pass
                return
            
            # 等待3秒后再次检查
            await asyncio.sleep(3)
        
        # 如果达到最大检查次数仍未成功，则超时
        if user_id in self.login_sessions:
            try:
                await event.reply(f"登录超时，请重新发送 /qqbind 获取新的二维码")
            except:
                pass
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
            "verified": True
        }
        self._save_data()
        
        yield event.plain_result(f"已为用户绑定QQ号\n用户ID：{user_id}\nQQ号：{qq_number}")
    
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
        
        bind_time_str = datetime.datetime.fromtimestamp(bind_time).strftime("%Y-%m-%d %H:%M:%S") if bind_time else "未知时间"
        
        yield event.plain_result(f"您的QQID为：{user_id}\n您绑定的QQ为：{qq_number}\n绑定时间：{bind_time_str}")
    
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
            result += "----------\n"
        
        # 如果文本过长，分段发送
        if len(result) > 2000:
            chunks = [result[i:i+2000] for i in range(0, len(result), 2000)]
            for chunk in chunks:
                yield event.plain_result(chunk)
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
        
        yield event.plain_result(f"ID {target_id} 绑定的QQ号为: {qq_number}")

    @filter.command("qqconfig")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def qq_config(self, event: AstrMessageEvent):
        '''查看QQ绑定插件配置 - 仅管理员可用'''
        config_text = "当前配置：\n"
        for key, value in self.config.items():
            config_text += f"{key}: {value}\n"
        
        yield event.plain_result(config_text)
