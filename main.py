from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import sqlite3
from pathlib import Path
from .utils import NATION_HELP

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
        
        # 创建职位表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nation_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(nation_id, name),
            FOREIGN KEY (nation_id) REFERENCES nations (id)
        )
        ''')
        
        # 创建用户职位关系表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_positions (
            user_id TEXT NOT NULL,
            position_id INTEGER NOT NULL,
            assign_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(user_id, position_id),
            FOREIGN KEY (user_id) REFERENCES user_nations (user_id),
            FOREIGN KEY (position_id) REFERENCES positions (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    @filter.command("创建国家")
    async def create_nation(self, event: AstrMessageEvent):
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
    async def join_nation(self, event: AstrMessageEvent):
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
    async def list_nations(self, event: AstrMessageEvent):
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
    async def check_nation_status(self, event: AstrMessageEvent):
        """查看自己所在国家的状态"""
        user_id = event.get_sender_id()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查用户是否加入了国家
            cursor.execute(
                "SELECT n.id, n.name, n.member_count, n.creator_name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ?",
                (user_id,)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("你还没有加入任何国家")
                return
            
            nation_id, name, member_count, creator_name = nation_info
            
            # 获取国家成员列表及职位信息
            cursor.execute(
                "SELECT un.user_name, GROUP_CONCAT(p.name, ', ') as positions FROM user_nations un LEFT JOIN user_positions up ON un.user_id = up.user_id LEFT JOIN positions p ON up.position_id = p.id AND p.nation_id = ? WHERE un.nation_id = ? GROUP BY un.user_id, un.user_name",
                (nation_id, nation_id)
            )
            members = cursor.fetchall()
            
            result = f"=== {name} 国家状态 ===\n"
            result += f"创建者: {creator_name}\n"
            result += f"成员数: {member_count}\n"
            result += "成员列表及职位:\n"
            
            for member_name, positions in members:
                if positions:
                    result += f"  - {member_name} ({positions})\n"
                else:
                    result += f"  - {member_name}\n"
            
            yield event.plain_result(result.strip())
        except Exception as e:
            logger.error(f"查看国家状态失败: {e}")
            yield event.plain_result("查看国家状态失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("退出国家")
    async def leave_nation(self, event: AstrMessageEvent):
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
    async def dissolve_nation(self, event: AstrMessageEvent):
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
            
            # 删除所有用户职位关系
            cursor.execute("DELETE FROM user_positions WHERE position_id IN (SELECT id FROM positions WHERE nation_id = ?)", (nation_id,))
            
            # 删除所有职位
            cursor.execute("DELETE FROM positions WHERE nation_id = ?", (nation_id,))
            
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
    
    @filter.command("晋升")
    async def promote_member(self, event: AstrMessageEvent):
        """晋升国家成员到指定职位"""
        user_id = event.get_sender_id()
        message_str = event.message_str.strip()
        
        # 解析参数
        if len(message_str) < 3:  # "/晋升 " 是3个字符
            yield event.plain_result("请输入正确格式：/晋升 <成员名或@用户> <职位>")
            return
        
        params = message_str[3:].strip().split(" ", 1)
        if len(params) < 2:
            yield event.plain_result("请输入正确格式：/晋升 <成员名或@用户> <职位>")
            return
        
        target_member, position_name = params[0].strip(), params[1].strip()
        if not target_member or not position_name:
            yield event.plain_result("成员名和职位不能为空")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 检查当前用户是否是国家创建者
            cursor.execute(
                "SELECT n.id, n.name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ? AND n.creator_id = ?",
                (user_id, user_id)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("只有国家创建者才能使用晋升命令")
                return
            
            nation_id, nation_name = nation_info
            
            # 2. 查找目标成员的user_id
            # 先尝试通过用户名查找
            cursor.execute(
                "SELECT user_id FROM user_nations WHERE nation_id = ? AND user_name = ?",
                (nation_id, target_member)
            )
            target_user = cursor.fetchone()
            
            # 如果没有找到，尝试解析@用户（这里简化处理，实际可能需要更复杂的解析）
            if not target_user:
                # 简单处理：如果target_member是@开头，去掉@符号后尝试作为用户名查找
                if target_member.startswith("@"):
                    cursor.execute(
                        "SELECT user_id FROM user_nations WHERE nation_id = ? AND user_name = ?",
                        (nation_id, target_member[1:])
                    )
                    target_user = cursor.fetchone()
            
            if not target_user:
                yield event.plain_result(f"{target_member} 不是本国家成员，无法晋升")
                return
            
            target_user_id = target_user[0]
            
            # 3. 检查职位是否存在，不存在则创建
            cursor.execute(
                "SELECT id FROM positions WHERE nation_id = ? AND name = ?",
                (nation_id, position_name)
            )
            position = cursor.fetchone()
            
            if not position:
                # 创建新职位
                cursor.execute(
                    "INSERT INTO positions (nation_id, name) VALUES (?, ?)",
                    (nation_id, position_name)
                )
                position_id = cursor.lastrowid
            else:
                position_id = position[0]
            
            # 4. 给目标成员分配职位
            cursor.execute(
                "INSERT OR REPLACE INTO user_positions (user_id, position_id) VALUES (?, ?)",
                (target_user_id, position_id)
            )
            
            conn.commit()
            yield event.plain_result(f"已成功晋升 {target_member} 为 {position_name}")
        except Exception as e:
            logger.error(f"晋升失败: {e}")
            yield event.plain_result("晋升失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("撤职")
    async def demote_member(self, event: AstrMessageEvent):
        """撤销国家成员的职位"""
        user_id = event.get_sender_id()
        message_str = event.message_str.strip()
        
        # 解析参数
        if len(message_str) < 3:  # "/撤职 " 是3个字符
            yield event.plain_result("请输入正确格式：/撤职 <成员名或@用户>")
            return
        
        target_member = message_str[3:].strip()
        if not target_member:
            yield event.plain_result("成员名不能为空")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 检查当前用户是否是国家创建者
            cursor.execute(
                "SELECT n.id, n.name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ? AND n.creator_id = ?",
                (user_id, user_id)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("只有国家创建者才能使用撤职命令")
                return
            
            nation_id, nation_name = nation_info
            
            # 2. 查找目标成员的user_id
            # 先尝试通过用户名查找
            cursor.execute(
                "SELECT user_id FROM user_nations WHERE nation_id = ? AND user_name = ?",
                (nation_id, target_member)
            )
            target_user = cursor.fetchone()
            
            # 如果没有找到，尝试解析@用户
            if not target_user:
                if target_member.startswith("@"):
                    cursor.execute(
                        "SELECT user_id FROM user_nations WHERE nation_id = ? AND user_name = ?",
                        (nation_id, target_member[1:])
                    )
                    target_user = cursor.fetchone()
            
            if not target_user:
                yield event.plain_result(f"{target_member} 不是本国家成员")
                return
            
            target_user_id = target_user[0]
            
            # 3. 撤销目标成员的所有职位
            cursor.execute(
                "DELETE FROM user_positions WHERE user_id = ? AND position_id IN (SELECT id FROM positions WHERE nation_id = ?)",
                (target_user_id, nation_id)
            )
            
            conn.commit()
            yield event.plain_result(f"已成功撤销 {target_member} 的所有职位")
        except Exception as e:
            logger.error(f"撤职失败: {e}")
            yield event.plain_result("撤职失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("查看国家所有成员")
    async def view_all_members(self, event: AstrMessageEvent):
        """查看国家的所有成员及其职位"""
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
            
            # 获取国家成员列表及职位信息
            cursor.execute(
                "SELECT un.user_name, GROUP_CONCAT(p.name, ', ') as positions, n.creator_id = un.user_id as is_creator FROM user_nations un LEFT JOIN user_positions up ON un.user_id = up.user_id LEFT JOIN positions p ON up.position_id = p.id AND p.nation_id = ? JOIN nations n ON un.nation_id = n.id WHERE un.nation_id = ? GROUP BY un.user_id, un.user_name, n.creator_id",
                (nation_id, nation_id)
            )
            members = cursor.fetchall()
            
            total_count = len(members)
            result = f"国家共[{total_count}]人\n"
            
            for i, (member_name, positions, is_creator) in enumerate(members, 1):
                if is_creator:
                    result += f"{i}.{member_name} 领导人\n"
                elif positions:
                    result += f"{i}.{member_name} {positions}\n"
                else:
                    result += f"{i}.{member_name} 成员\n"
            
            yield event.plain_result(result.strip())
        except Exception as e:
            logger.error(f"查看国家所有成员失败: {e}")
            yield event.plain_result("查看国家所有成员失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("国战帮助")
    async def nation_help(self, event: AstrMessageEvent):
        """查看国战插件的帮助信息"""
        url = await self.text_to_image(NATION_HELP)
        yield event.image_result(url)
    
    async def terminate(self):
        """插件被卸载/停用时调用"""
        logger.info("虚拟国政插件已关闭")
