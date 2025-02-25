from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import re
import json
import os

@register("astrbot_plugin_QQbotbd", "QQ绑定插件", "一个用于绑定用户OpenID与QQ号的插件", "1.0.0", "https://github.com/yourusername/astrbot_plugin_QQbotbd")
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
    
    def get_qq_by_openid(self, openid):
        """根据OpenID获取QQ号
        
        Args:
            openid (str): 用户的OpenID
            
        Returns:
            str or None: 查找到的QQ号，如果未找到则返回None
        """
        if openid in self.bind_data:
            return self.bind_data[openid]["qq_number"]
        return None
    
    @filter.command("qqbind")
    async def qq_bind(self, event: AstrMessageEvent):
        '''绑定QQ号 - 使用方法: /qqbind [QQ号]'''
        user_id = event.get_user_id()  # 获取用户的OpenID
        message_str = event.message_str.strip()
        
        # 检查是否提供了QQ号
        match = re.search(r'/qqbind\s+(\d{5,11})', message_str)
        if not match:
            yield event.plain_result("请提供正确的QQ号，格式：/qqbind [QQ号]")
            return
        
        qq_number = match.group(1)
        
        # 检查QQ号是否已被其他用户绑定
        for openid, data in self.bind_data.items():
            if openid != user_id and data.get("qq_number") == qq_number:
                yield event.plain_result(f"该QQ号已被其他用户绑定，请使用其他QQ号")
                return
        
        # 绑定QQ号到用户的OpenID
        self.bind_data[user_id] = {
            "qq_number": qq_number,
            "bind_time": event.timestamp
        }
        self._save_data()
        
        logger.info(f"用户 {user_id} 绑定QQ号 {qq_number} 成功")
        yield event.plain_result(f"成功将QQ号 {qq_number} 绑定到您的账号")
    
    @filter.command("qqunbind")
    async def qq_unbind(self, event: AstrMessageEvent):
        '''解绑QQ号 - 使用方法: /qqunbind'''
        user_id = event.get_user_id()  # 获取用户的OpenID
        
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
        user_id = event.get_user_id()  # 获取用户的OpenID
        user_name = event.get_sender_name()
        
        if user_id not in self.bind_data:
            yield event.plain_result("您尚未绑定QQ号，请使用 /qqbind [QQ号] 进行绑定")
            return
        
        qq_data = self.bind_data[user_id]
        qq_number = qq_data["qq_number"]
        bind_time = qq_data["bind_time"]
        
        # 将时间戳转换为可读格式
        import datetime
        bind_time_str = datetime.datetime.fromtimestamp(bind_time).strftime("%Y-%m-%d %H:%M:%S")
        
        yield event.plain_result(f"用户 {user_name} 已绑定QQ号: {qq_number}\n绑定时间: {bind_time_str}\nOpenID: {user_id}")
    
    @filter.command("qqlist", priority=1)
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def qq_list(self, event: AstrMessageEvent):
        '''列出所有绑定记录 - 仅管理员可用'''
        if len(self.bind_data) == 0:
            yield event.plain_result("当前没有任何绑定记录")
            return
        
        result = "所有QQ绑定记录：\n"
        for openid, data in self.bind_data.items():
            result += f"OpenID: {openid}\nQQ号: {data['qq_number']}\n"
            if 'bind_time' in data:
                import datetime
                bind_time_str = datetime.datetime.fromtimestamp(data['bind_time']).strftime("%Y-%m-%d %H:%M:%S")
                result += f"绑定时间: {bind_time_str}\n"
            result += "----------\n"
        
        # 如果文本过长，转为图片发送
        if len(result) > 1000:
            url = await self.text_to_image(result)
            yield event.image_result(url)
        else:
            yield event.plain_result(result)
    
    @filter.command("qqhelp")
    async def qq_help(self, event: AstrMessageEvent):
        '''QQ绑定插件帮助 - 使用方法: /qqhelp'''
        help_text = """QQ绑定插件使用帮助：
1. 绑定QQ号：/qqbind [QQ号]
2. 解绑QQ号：/qqunbind
3. 查询绑定信息：/qqinfo
4. 查看帮助：/qqhelp

管理员命令：
1. 查询所有绑定记录：/qqlist
2. 查询指定OpenID的QQ号：/whoisqq [OpenID]"""
        
        yield event.plain_result(help_text)
    
    # 添加一个用于被其他插件调用的API，通过OpenID查询QQ号
    @filter.command("whoisqq")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def who_is_qq(self, event: AstrMessageEvent):
        '''查询指定OpenID对应的QQ号 - 仅管理员可用'''
        user_id = event.get_user_id()
        message_str = event.message_str.strip()
        
        # 检查是否提供了OpenID
        match = re.search(r'/whoisqq\s+([A-F0-9]{32})', message_str)
        if not match:
            yield event.plain_result("请提供正确的OpenID，格式：/whoisqq [OpenID]")
            return
        
        target_openid = match.group(1)
        
        if target_openid not in self.bind_data:
            yield event.plain_result(f"未找到OpenID {target_openid} 绑定的QQ号")
            return
        
        qq_number = self.bind_data[target_openid]["qq_number"]
        yield event.plain_result(f"OpenID {target_openid} 绑定的QQ号为: {qq_number}")
