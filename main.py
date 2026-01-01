from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import sqlite3
from pathlib import Path

@register("virtual_nation", "author", "虚拟国政QQ群插件", "1.0.0", "repo url")
class VirtualNationPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.plugin_name = "virtual_nation"
        self.db_path = Path(f"data/plugin_data/{self.plugin_name}/nation.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建国家表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS nations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            creator_id TEXT NOT NULL,
            creator_name TEXT NOT NULL,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            member_count INTEGER DEFAULT 1
        )
        ''')
        
        # 创建用户国家关系表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_nations (
            user_id TEXT PRIMARY KEY,
            user_name TEXT NOT NULL,
            nation_id INTEGER NOT NULL,
            join_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (nation_id) REFERENCES nations (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    @filter.command("创建国家")
    async def create_nation(self, event: AstrMessageEvent, *args, **kwargs):
        """创建一个新的国家"""
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        message_str = event.message_str.strip()
        
        # 解析国家名称
        if len(message_str) < 5:  # "/创建国家 " 是5个字符
            yield event.plain_result("请输入国家名称，格式：/创建国家 <国家名>")
            return
        
        nation_name = message_str[5:].strip()
        if not nation_name:
            yield event.plain_result("国家名称不能为空")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查用户是否已加入国家
            cursor.execute("SELECT nation_id FROM user_nations WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                yield event.plain_result("你已经加入了一个国家，无法创建新国家")
                return
            
            # 检查国家名称是否已存在
            cursor.execute("SELECT id FROM nations WHERE name = ?", (nation_name,))
            if cursor.fetchone():
                yield event.plain_result(f"国家 {nation_name} 已存在")
                return
            
            # 创建国家
            cursor.execute(
                "INSERT INTO nations (name, creator_id, creator_name) VALUES (?, ?, ?)",
                (nation_name, user_id, user_name)
            )
            nation_id = cursor.lastrowid
            
            # 将创建者加入国家
            cursor.execute(
                "INSERT INTO user_nations (user_id, user_name, nation_id) VALUES (?, ?, ?)",
                (user_id, user_name, nation_id)
            )
            
            conn.commit()
            yield event.plain_result(f"国家 {nation_name} 创建成功！你已成为该国成员")
        except Exception as e:
            logger.error(f"创建国家失败: {e}")
            yield event.plain_result("创建国家失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("加入国家")
    async def join_nation(self, event: AstrMessageEvent, *args, **kwargs):
        """加入一个已存在的国家"""
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        message_str = event.message_str.strip()
        
        # 解析国家名称
        if len(message_str) < 5:  # "/加入国家 " 是5个字符
            yield event.plain_result("请输入国家名称，格式：/加入国家 <国家名>")
            return
        
        nation_name = message_str[5:].strip()
        if not nation_name:
            yield event.plain_result("国家名称不能为空")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查用户是否已加入国家
            cursor.execute("SELECT nation_id FROM user_nations WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                yield event.plain_result("你已经加入了一个国家，无法再加入其他国家")
                return
            
            # 检查国家是否存在
            cursor.execute("SELECT id FROM nations WHERE name = ?", (nation_name,))
            nation = cursor.fetchone()
            if not nation:
                yield event.plain_result(f"国家 {nation_name} 不存在")
                return
            
            nation_id = nation[0]
            
            # 将用户加入国家
            cursor.execute(
                "INSERT INTO user_nations (user_id, user_name, nation_id) VALUES (?, ?, ?)",
                (user_id, user_name, nation_id)
            )
            
            # 更新国家成员数量
            cursor.execute(
                "UPDATE nations SET member_count = member_count + 1 WHERE id = ?",
                (nation_id,)
            )
            
            conn.commit()
            yield event.plain_result(f"成功加入国家 {nation_name}！")
        except Exception as e:
            logger.error(f"加入国家失败: {e}")
            yield event.plain_result("加入国家失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("查看所有国家")
    async def list_nations(self, event: AstrMessageEvent, *args, **kwargs):
        """查看所有已创建的国家"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT name, member_count, creator_name FROM nations ORDER BY member_count DESC")
            nations = cursor.fetchall()
            
            if not nations:
                yield event.plain_result("暂无创建的国家")
                return
            
            result = "所有国家列表：\n"
            for i, (name, member_count, creator_name) in enumerate(nations, 1):
                result += f"{i}. {name} - 成员数: {member_count} - 创建者: {creator_name}\n"
            
            yield event.plain_result(result.strip())
        except Exception as e:
            logger.error(f"查看国家列表失败: {e}")
            yield event.plain_result("查看国家列表失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("查看国家状态")
    async def check_nation_status(self, event: AstrMessageEvent, *args, **kwargs):
        """查看自己所在国家的状态"""
        user_id = event.get_sender_id()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查用户是否加入了国家
            cursor.execute(
                "SELECT n.name, n.member_count, n.creator_name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ?",
                (user_id,)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("你还没有加入任何国家")
                return
            
            name, member_count, creator_name = nation_info
            
            # 获取国家成员列表
            cursor.execute(
                "SELECT user_name FROM user_nations WHERE nation_id = (SELECT id FROM nations WHERE name = ?)",
                (name,)
            )
            members = cursor.fetchall()
            member_names = [member[0] for member in members]
            
            result = f"=== {name} 国家状态 ===\n"
            result += f"创建者: {creator_name}\n"
            result += f"成员数: {member_count}\n"
            result += f"成员列表: {', '.join(member_names)}\n"
            
            # 使用文转图功能
            url = await self.text_to_image(result.strip())
            yield event.image_result(url)
        except Exception as e:
            logger.error(f"查看国家状态失败: {e}")
            yield event.plain_result("查看国家状态失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("退出国家")
    async def leave_nation(self, event: AstrMessageEvent, *args, **kwargs):
        """退出当前所在的国家"""
        user_id = event.get_sender_id()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查用户是否加入了国家
            cursor.execute(
                "SELECT n.id, n.name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ?",
                (user_id,)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("你还没有加入任何国家")
                return
            
            nation_id, nation_name = nation_info
            
            # 删除用户国家关系
            cursor.execute("DELETE FROM user_nations WHERE user_id = ?", (user_id,))
            
            # 更新国家成员数量
            cursor.execute(
                "UPDATE nations SET member_count = member_count - 1 WHERE id = ?",
                (nation_id,)
            )
            
            # 检查国家成员数量，如果为0则解散国家
            cursor.execute("SELECT member_count FROM nations WHERE id = ?", (nation_id,))
            member_count = cursor.fetchone()[0]
            if member_count <= 0:
                # 删除国家
                cursor.execute("DELETE FROM nations WHERE id = ?", (nation_id,))
                conn.commit()
                yield event.plain_result(f"你已成功退出国家 {nation_name}，该国家因无成员已自动解散")
            else:
                conn.commit()
                yield event.plain_result(f"你已成功退出国家 {nation_name}")
        except Exception as e:
            logger.error(f"退出国家失败: {e}")
            yield event.plain_result("退出国家失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("解散国家")
    async def dissolve_nation(self, event: AstrMessageEvent, *args, **kwargs):
        """解散自己创建的国家"""
        user_id = event.get_sender_id()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查用户是否加入了国家，且是国家创建者
            cursor.execute(
                "SELECT n.id, n.name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ? AND n.creator_id = ?",
                (user_id, user_id)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("你不是任何国家的创建者，无法解散国家")
                return
            
            nation_id, nation_name = nation_info
            
            # 删除所有用户国家关系
            cursor.execute("DELETE FROM user_nations WHERE nation_id = ?", (nation_id,))
            
            # 删除国家
            cursor.execute("DELETE FROM nations WHERE id = ?", (nation_id,))
            
            conn.commit()
            yield event.plain_result(f"国家 {nation_name} 已成功解散")
        except Exception as e:
            logger.error(f"解散国家失败: {e}")
            yield event.plain_result("解散国家失败，请稍后重试")
        finally:
            conn.close()
    
    async def terminate(self):
        """插件被卸载/停用时调用"""
        logger.info("虚拟国政插件已关闭")
