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

@register("qqbind", "QQ绑定插件", "一个通过登录验证绑定QQ号的插件", "1.0.0", "https://github.com/yourusername/astrbot_plugin_QQbotbd")
class QQBindPlugin(Star):
    def __init__(self, context: Context):
        """初始化QQ绑定插件
        
        Args:
            context (Context): AstrBot上下文对象，包含大多数组件
        """
        super().__init__(context)
        self.data_file = os.path.join(os.path.dirname(__file__), "qqbind_data.json")
        self.bind_data = self._load_data()
        self.login_sessions = {}  # 存储登录会话信息
        self.api_url = "https://api.yuafeng.cn/API/ly/music_login.php"
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
    
    async def verify_qq_login(self, qq, password):
        """验证QQ登录
        
        Args:
            qq (str): QQ号
            password (str): 密码
            
        Returns:
            tuple: (成功与否, 消息, QQ号)
        """
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "type": "qq",  # 根据API文档，需要提供type参数
                    "uin": qq,
                    "pwd": password
                }
                
                async with session.get(self.api_url, params=params) as response:
                    if response.status != 200:
                        return False, f"API请求失败，状态码: {response.status}", None
                    
                    data = await response.json()
                    logger.debug(f"QQ登录API返回: {data}")
                    
                    if data.get("code") == 1:  # 假设1是成功状态码
                        return True, "登录成功", qq
                    else:
                        return False, data.get("msg", "登录失败，未知原因"), None
        except Exception as e:
            logger.error(f"验证QQ登录时出错: {e}")
            return False, f"验证过程出错: {str(e)}", None
    
    @filter.command("qqbind")
    async def qq_bind(self, event: AstrMessageEvent):
        '''开始QQ绑定流程 - 使用方法: /qqbind'''
        user_id = self.user_openid(event)
        if not user_id:
            yield event.plain_result("无法获取您的用户ID，绑定失败")
            return
        
        # 生成会话ID
        session_id = self.generate_session_id()
        self.login_sessions[user_id] = {
            "session_id": session_id,
            "step": "waiting_qq",
            "timestamp": time.time()
        }
        
        # 发送绑定指引
        yield event.plain_result(
            "请按照以下步骤进行QQ绑定：\n"
            "1. 请发送您的QQ号\n"
            "2. 然后我们会要求您提供验证信息\n"
            "3. 验证成功后，您的QQ号将被绑定到您的账号\n\n"
            "您可以随时发送 'cancel' 取消绑定流程"
        )
    
    @filter.message()
    async def handle_bind_flow(self, event: AstrMessageEvent):
        '''处理绑定流程中的消息'''
        user_id = self.user_openid(event)
        if not user_id or user_id not in self.login_sessions:
            return  # 不是绑定流程中的消息
        
        message = event.message_str.strip()
        
        # 检查是否取消
        if message.lower() == 'cancel':
            del self.login_sessions[user_id]
            yield event.plain_result("已取消绑定流程")
            return
        
        session = self.login_sessions[user_id]
        
        # 检查会话是否过期（30分钟）
        if time.time() - session["timestamp"] > 1800:
            del self.login_sessions[user_id]
            yield event.plain_result("绑定会话已过期，请重新开始绑定流程")
            return
        
        # 根据当前步骤处理消息
        if session["step"] == "waiting_qq":
            # 验证QQ号格式
            if not re.match(r'^\d{5,11}$', message):
                yield event.plain_result("请输入有效的QQ号（5-11位数字）")
                return
            
            # 保存QQ号并进入下一步
            session["qq"] = message
            session["step"] = "waiting_password"
            session["timestamp"] = time.time()
            
            yield event.plain_result(
                f"已记录QQ号: {message}\n"
                "请输入您的QQ密码进行验证\n"
                "注意：我们不会存储您的密码，仅用于验证您是QQ号的所有者"
            )
            
        elif session["step"] == "waiting_password":
            # 保存密码并进行验证
            password = message
            qq = session["qq"]
            
            # 发送验证中消息
            yield event.plain_result("正在验证QQ登录信息，请稍候...")
            
            # 验证QQ登录
            success, msg, verified_qq = await self.verify_qq_login(qq, password)
            
            # 清除会话中的敏感信息
            if "password" in session:
                del session["password"]
            
            if success:
                # 绑定QQ号
                self.bind_data[user_id] = {
                    "qq_number": verified_qq,
                    "bind_time": int(time.time()),
                    "verified": True
                }
                self._save_data()
                
                # 清除会话
                del self.login_sessions[user_id]
                
                logger.info(f"用户 {user_id} 通过登录验证绑定QQ号 {verified_qq} 成功")
                yield event.plain_result(f"验证成功！\n您的QQID为：{user_id}\n您绑定的QQ为：{verified_qq}")
            else:
                # 验证失败，返回错误信息
                yield event.plain_result(f"验证失败: {msg}\n请重新尝试或发送 'cancel' 取消绑定")
                # 重置到等待QQ号步骤
                session["step"] = "waiting_qq"
                session["timestamp"] = time.time()
    
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
1. 开始绑定流程：/qqbind
2. 解绑QQ号：/qqunbind
3. 查询绑定信息：/qqinfo
4. 查看帮助：/qqhelp

管理员命令：
1. 查询所有绑定记录：/qqlist
2. 查询指定ID的QQ号：/whoisqq [ID]

注意：绑定QQ号需要进行登录验证，以确保您是QQ号的所有者。"""
        
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
