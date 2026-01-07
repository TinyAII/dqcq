from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import requests
import json

# API配置
API_URL = "http://api.tinyaii.top/api/command"

@register("astrbot_plugin_xiuxian", "开发者", "一个基于QQ机器人的修仙文字游戏插件", "1.0.0")
class XiuxianPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 使用KV存储来保存用户的player_id映射
        self.user_player_map = {}
        
    # API通信核心函数
    async def call_api(self, command: str, player_id: str = None, params: dict = None) -> dict:
        """调用修仙游戏API"""
        payload = {
            "command": command
        }
        
        if player_id:
            payload["player_id"] = player_id
        
        if params:
            payload["params"] = params
        
        try:
            response = requests.post(API_URL, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API调用失败: {e}")
            return {
                "status": "error",
                "message": f"API调用失败: {str(e)}",
                "data": None
            }
    
    # 修仙帮助指令
    @filter.command("修仙帮助", alias={"帮助", "修仙指令"})
    async def xiuxian_help(self, event: AstrMessageEvent):
        """查看所有修仙指令的详细说明"""
        result = await self.call_api("修仙帮助")
        
        if result["status"] == "success":
            commands = result["data"]["commands"]
            help_text = "【修仙文字游戏指令列表】\n\n"
            
            for cmd in commands:
                help_text += f"🔹 **{cmd['command']}**\n"
                help_text += f"   别名: {', '.join(cmd['aliases'])}\n"
                help_text += f"   描述: {cmd['description']}\n"
                help_text += f"   冷却: {cmd['cooldown']}\n\n"
            
            yield event.plain_result(help_text)
        else:
            yield event.plain_result(f"❌ 获取帮助失败: {result['message']}")
    
    # 创建角色指令
    @filter.command("创建角色", alias={"注册", "开始修仙"})
    async def create_character(self, event: AstrMessageEvent, name: str):
        """创建新的修仙角色"""
        if not name:
            yield event.plain_result("❌ 请提供角色名称，格式：/创建角色 [名称]")
            return
        
        # 检查用户是否已有角色
        sender_id = event.get_sender_id()
        if sender_id in self.user_player_map:
            yield event.plain_result("❌ 你已经有角色了，无需重复创建")
            return
        
        result = await self.call_api("创建角色", params={"name": name})
        
        if result["status"] == "success":
            # 保存用户与角色的映射关系
            player_id = result["data"]["player_id"]
            self.user_player_map[sender_id] = player_id
            
            # 保存到KV存储
            await self.put_kv_data(f"user_{sender_id}", player_id)
            
            # 格式化输出
            data = result["data"]
            response_text = f"🎉 角色创建成功！\n\n"
            response_text += f"📋 角色信息\n"
            response_text += f"   姓名: {data['name']}\n"
            response_text += f"   等级: {data['level']}\n"
            response_text += f"   境界: {data['cultivation_stage']}\n\n"
            response_text += f"💡 开始你的修仙之旅吧！使用 /打坐 开始修炼。"
            
            yield event.plain_result(response_text)
        else:
            yield event.plain_result(f"❌ 创建角色失败: {result['message']}")
    
    # 获取用户的player_id
    async def get_player_id(self, sender_id: str) -> str:
        """获取用户的角色ID，如果本地没有则从KV存储中读取"""
        if sender_id in self.user_player_map:
            return self.user_player_map[sender_id]
        
        # 从KV存储中读取
        player_id = await self.get_kv_data(f"user_{sender_id}", None)
        if player_id:
            self.user_player_map[sender_id] = player_id
            return player_id
        
        return None
    
    # 状态指令
    @filter.command("状态", alias={"我的状态", "查看状态"})
    async def check_status(self, event: AstrMessageEvent):
        """查看角色的基本修仙状态"""
        sender_id = event.get_sender_id()
        player_id = await self.get_player_id(sender_id)
        
        if not player_id:
            yield event.plain_result("❌ 你还没有创建角色，请先使用 /创建角色 [名称] 开始修仙")
            return
        
        result = await self.call_api("状态", player_id)
        
        if result["status"] == "success":
            data = result["data"]
            status_text = f"📊 【{data['name']}的修仙状态】\n\n"
            status_text += f"🔸 境界: {data['cultivation_stage']}\n"
            status_text += f"🔸 等级: {data['level']}\n"
            status_text += f"🔸 修为: {data['cultivation_points']}\n"
            status_text += f"🔸 生命值: {data['health']}\n"
            status_text += f"🔸 灵力值: {data['mana']}\n"
            
            yield event.plain_result(status_text)
        else:
            yield event.plain_result(f"❌ 获取状态失败: {result['message']}")
    
    # 个人信息指令
    @filter.command("个人信息", alias={"信息", "我的信息"})
    async def personal_info(self, event: AstrMessageEvent):
        """查看角色的详细信息"""
        sender_id = event.get_sender_id()
        player_id = await self.get_player_id(sender_id)
        
        if not player_id:
            yield event.plain_result("❌ 你还没有创建角色，请先使用 /创建角色 [名称] 开始修仙")
            return
        
        result = await self.call_api("个人信息", player_id)
        
        if result["status"] == "success":
            data = result["data"]
            info_text = f"📋 【{data['name']}的详细信息】\n\n"
            info_text += f"🔸 角色ID: {data['id']}\n"
            info_text += f"🔸 姓名: {data['name']}\n"
            info_text += f"🔸 等级: {data['level']}\n"
            info_text += f"🔸 经验: {data['experience']}\n"
            info_text += f"🔸 境界: {data['cultivation_stage']}\n"
            info_text += f"🔸 修为: {data['cultivation_points']}\n"
            info_text += f"🔸 生命值: {data['health']}\n"
            info_text += f"🔸 灵力值: {data['mana']}\n"
            info_text += f"🔸 创建时间: {data['created_at']}\n"
            
            yield event.plain_result(info_text)
        else:
            yield event.plain_result(f"❌ 获取个人信息失败: {result['message']}")
    
    # 打坐/修炼/冥想指令
    @filter.command("打坐", alias={"修炼", "冥想"})
    async def meditate(self, event: AstrMessageEvent):
        """基础修炼获得修为"""
        sender_id = event.get_sender_id()
        player_id = await self.get_player_id(sender_id)
        
        if not player_id:
            yield event.plain_result("❌ 你还没有创建角色，请先使用 /创建角色 [名称] 开始修仙")
            return
        
        result = await self.call_api("打坐", player_id)
        
        if result["status"] == "success":
            data = result["data"]
            response_text = f"🧘‍♂️ {result['message']}\n\n"
            response_text += f"✨ 当前修为: {data['cultivation_points']}\n"
            response_text += f"📈 本次获得: {data['gained_points']}点\n"
            
            if "cooldown_end" in data:
                import time
                cooldown_time = data['cooldown_end'] - int(time.time())
                minutes, seconds = divmod(cooldown_time, 60)
                response_text += f"⏱️ 冷却时间: {minutes}分{seconds}秒\n"
            
            yield event.plain_result(response_text)
        else:
            yield event.plain_result(f"❌ 打坐失败: {result['message']}")
    
    # 突破/升级/进阶指令
    @filter.command("突破", alias={"升级", "进阶"})
    async def breakthrough(self, event: AstrMessageEvent):
        """消耗修为突破到更高境界"""
        sender_id = event.get_sender_id()
        player_id = await self.get_player_id(sender_id)
        
        if not player_id:
            yield event.plain_result("❌ 你还没有创建角色，请先使用 /创建角色 [名称] 开始修仙")
            return
        
        result = await self.call_api("突破", player_id)
        
        if result["status"] == "success":
            data = result["data"]
            response_text = f"🎉 {result['message']}\n\n"
            response_text += f"🌟 新境界: {data['cultivation_stage']}\n"
            response_text += f"💎 剩余修为: {data['remaining_points']}\n"
            response_text += f"✨ 恭喜你更上一层楼！\n"
            
            yield event.plain_result(response_text)
        else:
            yield event.plain_result(f"❌ 突破失败: {result['message']}")
    
    # 调息/恢复/休息指令
    @filter.command("调息", alias={"恢复", "休息"})
    async def recover(self, event: AstrMessageEvent):
        """恢复生命和灵力"""
        sender_id = event.get_sender_id()
        player_id = await self.get_player_id(sender_id)
        
        if not player_id:
            yield event.plain_result("❌ 你还没有创建角色，请先使用 /创建角色 [名称] 开始修仙")
            return
        
        result = await self.call_api("调息", player_id)
        
        if result["status"] == "success":
            data = result["data"]
            response_text = f"💨 {result['message']}\n\n"
            response_text += f"❤️ 生命值: {data['health']}\n"
            response_text += f"💙 灵力值: {data['mana']}\n"
            
            if "cooldown_end" in data:
                import time
                cooldown_time = data['cooldown_end'] - int(time.time())
                minutes, seconds = divmod(cooldown_time, 60)
                response_text += f"⏱️ 冷却时间: {minutes}分{seconds}秒\n"
            
            yield event.plain_result(response_text)
        else:
            yield event.plain_result(f"❌ 调息失败: {result['message']}")
    
    # 闭关/深度修炼指令
    @filter.command("闭关", alias={"深度修炼"})
    async def seclusion(self, event: AstrMessageEvent):
        """长时间修炼获得大量修为"""
        sender_id = event.get_sender_id()
        player_id = await self.get_player_id(sender_id)
        
        if not player_id:
            yield event.plain_result("❌ 你还没有创建角色，请先使用 /创建角色 [名称] 开始修仙")
            return
        
        result = await self.call_api("闭关", player_id)
        
        if result["status"] == "success":
            data = result["data"]
            response_text = f"🏯 {result['message']}\n\n"
            response_text += f"✨ 当前修为: {data['cultivation_points']}\n"
            response_text += f"📈 本次获得: {data['gained_points']}点\n"
            
            if "cooldown_end" in data:
                import time
                cooldown_time = data['cooldown_end'] - int(time.time())
                hours, remainder = divmod(cooldown_time, 3600)
                minutes, seconds = divmod(remainder, 60)
                response_text += f"⏱️ 冷却时间: {hours}时{minutes}分{seconds}秒\n"
            
            yield event.plain_result(response_text)
        else:
            yield event.plain_result(f"❌ 闭关失败: {result['message']}")
    
    async def terminate(self):
        """插件被卸载/停用时调用"""
        logger.info("修仙插件已卸载")
