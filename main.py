from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import re
import json
import os
import time
import datetime

@register("qqbind", "QQ绑定插件", "一个用于绑定用户OpenID与QQ号的插件", "1.0.0", "https://github.com/yourusername/astrbot_plugin_QQbotbd")
class QQBindPlugin(Star):
    def __init__(self, context: Context):
        """初始化QQ绑定插件
        
        Args:
            context (Context): AstrBot上下文对象，包含大多数组件
        """
        super().__init__(context)
        self.data_file = os.path.join(os.path.dirname(__file__), "qqbind_data.json")
        self.bind_data = self._load_data()
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
        """从事件中获取用户OpenID
        
        适配多种事件类型，包括QQ官方Webhook事件
        """
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
            
            # 针对QQOfficialWebhookMessageEvent的特殊处理
            if event_type == "QQOfficialWebhookMessageEvent":
                # 尝试获取event_id属性
                if hasattr(event, 'event_id') and event.event_id:
                    logger.debug(f"从event_id属性获取: {event.event_id}")
                    return event.event_id
            
            # 临时解决方案：从消息内容中提取QQ号作为ID
            if hasattr(event, 'message_str'):
                message = event.message_str
                qq_match = re.search(r'(?:/qqbind|qqbind)\s*(\d{5,11})', message)
                if qq_match:
                    qq_number = qq_match.group(1)
                    logger.debug(f"从消息内容中提取QQ号作为ID: {qq_number}")
                    return f"qq_{qq_number}"  # 添加前缀避免冲突
            
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
    
    @filter.command("qqbind")
    async def qq_bind(self, event: AstrMessageEvent):
        '''绑定QQ号 - 使用方法: /qqbind [QQ号]'''
        message_str = event.message_str.strip()
        
        # 打印原始消息和事件信息，帮助调试
        logger.debug(f"收到绑定命令，原始消息: '{message_str}'")
        
        # 更灵活的正则表达式，尝试多种可能的格式
        match = re.search(r'(?:/qqbind|qqbind)\s*(\d{5,11})', message_str)
        if not match:
            # 尝试直接提取数字
            digits_match = re.search(r'(\d{5,11})', message_str)
            if digits_match:
                qq_number = digits_match.group(1)
                logger.debug(f"通过数字匹配提取到QQ号: {qq_number}")
            else:
                yield event.plain_result("请提供正确的QQ号，格式：/qqbind [QQ号]")
                return
        else:
            qq_number = match.group(1)
            logger.debug(f"通过命令匹配提取到QQ号: {qq_number}")
        
        # 优先尝试使用get_sender_id方法
        if hasattr(event, 'get_sender_id') and callable(event.get_sender_id):
            user_id = event.get_sender_id()
            if user_id:
                logger.debug(f"从get_sender_id方法获取: {user_id}")
            else:
                # 如果get_sender_id返回空值，尝试其他方法
                user_id = self.user_openid(event)
        else:
            # 如果没有get_sender_id方法，使用辅助方法
            user_id = self.user_openid(event)
        
        # 如果仍然无法获取用户ID，使用QQ号作为临时ID
        if not user_id:
            user_id = f"qq_{qq_number}"
            logger.warning(f"无法获取用户ID，使用QQ号作为临时ID: {user_id}")
        
        # 检查QQ号是否已被其他用户绑定
        for openid, data in self.bind_data.items():
            if openid != user_id and data.get("qq_number") == qq_number:
                yield event.plain_result(f"该QQ号已被其他用户绑定，请使用其他QQ号")
                return
        
        # 绑定QQ号到用户的OpenID或临时ID
        self.bind_data[user_id] = {
            "qq_number": qq_number,
            "bind_time": int(time.time())
        }
        self._save_data()
        
        logger.info(f"用户 {user_id} 绑定QQ号 {qq_number} 成功")
        
        # 确保显示正确的OpenID
        yield event.plain_result(f"您的QQID为：{user_id}\n您绑定的QQ为：{qq_number}")
    
    @filter.command("qqunbind")
    async def qq_unbind(self, event: AstrMessageEvent):
        '''解绑QQ号 - 使用方法: /qqunbind'''
        user_id = self.user_openid(event)
        
        # 如果无法获取用户ID，尝试从已绑定的QQ号中查找
        if not user_id:
            # 提示用户使用QQ号解绑
            yield event.plain_result("无法获取您的用户ID，请使用 /qqunbind [QQ号] 进行解绑")
            return
        
        if user_id not in self.bind_data:
            yield event.plain_result("您尚未绑定QQ号")
            return
        
        qq_number = self.bind_data[user_id]["qq_number"]
        del self.bind_data[user_id]
        self._save_data()
        
        logger.info(f"用户 {user_id} 解绑QQ号 {qq_number} 成功")
        yield event.plain_result(f"成功解绑QQ号: {qq_number}")
    
    @filter.command("qqunbindqq")
    async def qq_unbind_by_qq(self, event: AstrMessageEvent):
        '''通过QQ号解绑 - 使用方法: /qqunbindqq [QQ号]'''
        message_str = event.message_str.strip()
        logger.debug(f"收到QQ解绑命令，原始消息: '{message_str}'")
        
        # 更灵活的正则表达式
        match = re.search(r'(?:/qqunbindqq|qqunbindqq)\s*(\d{5,11})', message_str)
        if not match:
            # 尝试直接提取数字
            digits_match = re.search(r'(\d{5,11})', message_str)
            if digits_match:
                qq_number = digits_match.group(1)
            else:
                yield event.plain_result("请提供正确的QQ号，格式：/qqunbindqq [QQ号]")
                return
        else:
            qq_number = match.group(1)
        
        found = False
        
        # 查找绑定了该QQ号的用户ID
        for openid, data in list(self.bind_data.items()):
            if data.get("qq_number") == qq_number:
                del self.bind_data[openid]
                found = True
                logger.info(f"通过QQ号解绑成功: {qq_number}, 用户ID: {openid}")
        
        self._save_data()
        
        if found:
            yield event.plain_result(f"成功解绑QQ号: {qq_number}")
        else:
            yield event.plain_result(f"未找到绑定QQ号 {qq_number} 的记录")
    
    @filter.command("qqinfo")
    async def qq_info(self, event: AstrMessageEvent):
        '''查询已绑定的QQ号 - 使用方法: /qqinfo [可选:QQ号]'''
        message_str = event.message_str.strip()
        logger.debug(f"收到查询命令，原始消息: '{message_str}'")
        
        # 更灵活的正则表达式
        match = re.search(r'(?:/qqinfo|qqinfo)\s*(\d{5,11})', message_str)
        
        if match:
            # 通过QQ号查询
            qq_number = match.group(1)
            found = False
            
            for openid, data in self.bind_data.items():
                if data.get("qq_number") == qq_number:
                    bind_time = data.get("bind_time", 0)
                    bind_time_str = datetime.datetime.fromtimestamp(bind_time).strftime("%Y-%m-%d %H:%M:%S") if bind_time else "未知时间"
                    yield event.plain_result(f"QQ号 {qq_number} 已绑定\nQQID为：{openid}\n绑定时间：{bind_time_str}")
                    found = True
                    break
            
            if not found:
                yield event.plain_result(f"未找到QQ号 {qq_number} 的绑定记录")
            return
        
        # 尝试通过用户ID查询
        user_id = self.user_openid(event)
        if not user_id:
            yield event.plain_result("无法获取您的用户ID，请使用 /qqinfo [QQ号] 查询特定QQ号的绑定信息")
            return
            
        user_name = event.get_sender_name() if hasattr(event, 'get_sender_name') and callable(event.get_sender_name) else "用户"
        
        if user_id not in self.bind_data:
            yield event.plain_result("您尚未绑定QQ号，请使用 /qqbind [QQ号] 进行绑定")
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
1. 绑定QQ号：/qqbind [QQ号]
2. 解绑QQ号：/qqunbind
3. 通过QQ号解绑：/qqunbindqq [QQ号]
4. 查询绑定信息：/qqinfo [可选:QQ号]
5. 查看帮助：/qqhelp

管理员命令：
1. 查询所有绑定记录：/qqlist
2. 查询指定ID的QQ号：/whoisqq [ID]"""
        
        yield event.plain_result(help_text)
    
    # 添加一个用于被其他插件调用的API，通过OpenID查询QQ号
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
        
        qq_number = self.bind_data[target_id]["qq_number"]
        yield event.plain_result(f"ID {target_id} 绑定的QQ号为: {qq_number}")
