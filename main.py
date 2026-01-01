from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
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
            member_count INTEGER DEFAULT 1,
            last_declare_war_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        
        # 创建国库表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS nation_treasury (
            nation_id INTEGER PRIMARY KEY,
            silver INTEGER DEFAULT 1000,
            gold INTEGER DEFAULT 10,
            gift INTEGER DEFAULT 0,
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (nation_id) REFERENCES nations (id) ON DELETE CASCADE
        )
        ''')
        
        # 创建个人仓库表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_inventory (
            user_id TEXT PRIMARY KEY,
            silver INTEGER DEFAULT 100,
            gold INTEGER DEFAULT 0,
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user_nations (user_id) ON DELETE CASCADE
        )
        ''')
        
        # 创建战争表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS wars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_id INTEGER NOT NULL,
            defender_id INTEGER NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            UNIQUE(attacker_id, defender_id),
            FOREIGN KEY (attacker_id) REFERENCES nations (id) ON DELETE CASCADE,
            FOREIGN KEY (defender_id) REFERENCES nations (id) ON DELETE CASCADE
        )
        ''')
        
        # 创建外交请求表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS diplomacy_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_nation_id INTEGER NOT NULL,
            to_nation_id INTEGER NOT NULL,
            request_type TEXT DEFAULT '建交',
            gift_type TEXT,
            gift_amount INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_nation_id) REFERENCES nations (id) ON DELETE CASCADE,
            FOREIGN KEY (to_nation_id) REFERENCES nations (id) ON DELETE CASCADE
        )
        ''')
        
        # 创建外交关系表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS diplomacy_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nation1_id INTEGER NOT NULL,
            nation2_id INTEGER NOT NULL,
            relation_type TEXT DEFAULT '友好',
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(nation1_id, nation2_id),
            UNIQUE(nation2_id, nation1_id),
            FOREIGN KEY (nation1_id) REFERENCES nations (id) ON DELETE CASCADE,
            FOREIGN KEY (nation2_id) REFERENCES nations (id) ON DELETE CASCADE
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
                yield event.plain_result("您的国家与其他国家重名，请重新输入")
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
            
            # 初始化国库资源
            cursor.execute(
                "INSERT INTO nation_treasury (nation_id) VALUES (?)",
                (nation_id,)
            )
            
            # 初始化创建者个人仓库
            cursor.execute(
                "INSERT INTO user_inventory (user_id) VALUES (?)",
                (user_id,)
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
            
            # 初始化用户个人仓库
            cursor.execute(
                "INSERT INTO user_inventory (user_id) VALUES (?)",
                (user_id,)
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
            
            # 删除用户职位记录
            cursor.execute("DELETE FROM user_positions WHERE user_id = ?", (user_id,))
            
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
                # 删除所有相关外交请求
                cursor.execute("DELETE FROM diplomacy_requests WHERE from_nation_id = ? OR to_nation_id = ?", (nation_id, nation_id))
                
                # 删除所有相关外交关系
                cursor.execute("DELETE FROM diplomacy_relations WHERE nation1_id = ? OR nation2_id = ?", (nation_id, nation_id))
                
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
            
            # 删除所有相关外交请求
            cursor.execute("DELETE FROM diplomacy_requests WHERE from_nation_id = ? OR to_nation_id = ?", (nation_id, nation_id))
            
            # 删除所有相关外交关系
            cursor.execute("DELETE FROM diplomacy_relations WHERE nation1_id = ? OR nation2_id = ?", (nation_id, nation_id))
            
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
    
    @filter.command("查看国库")
    async def view_treasury(self, event: AstrMessageEvent):
        """查看国家的国库资源（仅领导人可查看）"""
        user_id = event.get_sender_id()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查用户是否是国家创建者
            cursor.execute(
                "SELECT n.id, n.name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ? AND n.creator_id = ?",
                (user_id, user_id)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("只有国家创建者才能查看国库")
                return
            
            nation_id, nation_name = nation_info
            
            # 查询国库资源
            cursor.execute(
                "SELECT silver, gold, gift FROM nation_treasury WHERE nation_id = ?",
                (nation_id,)
            )
            treasury = cursor.fetchone()
            
            if not treasury:
                yield event.plain_result("国库资源未初始化")
                return
            
            silver, gold, gift = treasury
            
            result = f"=== {nation_name} 国库 ===\n"
            result += f"【货币】白银：{silver}\n"
            result += f"【货币】金币：{gold}\n"
            result += f"【物品】国礼：{gift}\n"
            
            yield event.plain_result(result.strip())
        except Exception as e:
            logger.error(f"查看国库失败: {e}")
            yield event.plain_result("查看国库失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("个人仓库")
    async def view_inventory(self, event: AstrMessageEvent):
        """查看个人的仓库资源"""
        user_id = event.get_sender_id()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查用户是否已加入国家
            cursor.execute(
                "SELECT nation_id FROM user_nations WHERE user_id = ?",
                (user_id,)
            )
            user_nation = cursor.fetchone()
            
            if not user_nation:
                yield event.plain_result("你还没有加入任何国家")
                return
            
            # 查询个人仓库资源
            cursor.execute(
                "SELECT silver, gold FROM user_inventory WHERE user_id = ?",
                (user_id,)
            )
            inventory = cursor.fetchone()
            
            if not inventory:
                yield event.plain_result("个人仓库未初始化")
                return
            
            silver, gold = inventory
            
            result = "=== 个人仓库 ===\n"
            result += f"【货币】白银：{silver}\n"
            result += f"【货币】金币：{gold}\n"
            
            yield event.plain_result(result.strip())
        except Exception as e:
            logger.error(f"查看个人仓库失败: {e}")
            yield event.plain_result("查看个人仓库失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("宣战")
    async def declare_war(self, event: AstrMessageEvent):
        """向指定国家宣战（仅领导人可使用）"""
        user_id = event.get_sender_id()
        message_str = event.message_str.strip()
        
        # 解析参数
        if len(message_str) < 3:  # "/宣战 " 是3个字符
            yield event.plain_result("请输入正确格式：/宣战 <国家名>")
            return
        
        target_nation_name = message_str[3:].strip()
        if not target_nation_name:
            yield event.plain_result("国家名称不能为空")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 检查用户是否是国家创建者
            cursor.execute(
                "SELECT n.id, n.name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ? AND n.creator_id = ?",
                (user_id, user_id)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("只有国家创建者才能宣战")
                return
            
            attacker_id, attacker_name = nation_info
            
            # 2. 查找目标国家
            cursor.execute(
                "SELECT id FROM nations WHERE name = ?",
                (target_nation_name,)
            )
            target_nation = cursor.fetchone()
            
            if not target_nation:
                yield event.plain_result(f"国家 {target_nation_name} 不存在")
                return
            
            defender_id = target_nation[0]
            
            # 3. 检查是否对自己的国家宣战
            if attacker_id == defender_id:
                yield event.plain_result("不能对自己的国家宣战")
                return
            
            # 4. 检查是否已经处于战争状态
            cursor.execute(
                "SELECT id FROM wars WHERE (attacker_id = ? AND defender_id = ?) OR (attacker_id = ? AND defender_id = ?) AND status = 'active'",
                (attacker_id, defender_id, defender_id, attacker_id)
            )
            existing_war = cursor.fetchone()
            
            if existing_war:
                yield event.plain_result(f"已经与国家 {target_nation_name} 处于战争状态")
                return
            
            # 5. 检查宣战冷却时间（30分钟）
            cursor.execute(
                "SELECT last_declare_war_time FROM nations WHERE id = ?",
                (attacker_id,)
            )
            last_war_time = cursor.fetchone()[0]
            
            # 计算时间差
            last_war_datetime = datetime.strptime(last_war_time, "%Y-%m-%d %H:%M:%S")
            current_time = datetime.now()
            time_diff = current_time - last_war_datetime
            
            if time_diff < timedelta(minutes=30):
                # 计算剩余冷却时间
                remaining_time = timedelta(minutes=30) - time_diff
                minutes, seconds = divmod(remaining_time.total_seconds(), 60)
                yield event.plain_result(f"宣战冷却中，剩余 {int(minutes)} 分钟 {int(seconds)} 秒")
                return
            
            # 6. 创建战争记录
            cursor.execute(
                "INSERT INTO wars (attacker_id, defender_id) VALUES (?, ?)",
                (attacker_id, defender_id)
            )
            
            # 7. 更新上次宣战时间
            cursor.execute(
                "UPDATE nations SET last_declare_war_time = CURRENT_TIMESTAMP WHERE id = ?",
                (attacker_id,)
            )
            
            conn.commit()
            yield event.plain_result(f"已向国家 {target_nation_name} 宣战")
        except Exception as e:
            logger.error(f"宣战失败: {e}")
            yield event.plain_result("宣战失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("终止战争")
    async def end_war(self, event: AstrMessageEvent):
        """终止与指定国家的战争（仅领导人可使用，只能终止自己宣战的战争）"""
        user_id = event.get_sender_id()
        message_str = event.message_str.strip()
        
        # 解析参数
        if len(message_str) < 5:  # "/终止战争 " 是5个字符
            yield event.plain_result("请输入正确格式：/终止战争 <国家名>")
            return
        
        target_nation_name = message_str[5:].strip()
        if not target_nation_name:
            yield event.plain_result("国家名称不能为空")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 检查用户是否是国家创建者
            cursor.execute(
                "SELECT n.id, n.name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ? AND n.creator_id = ?",
                (user_id, user_id)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("只有国家创建者才能终止战争")
                return
            
            attacker_id, attacker_name = nation_info
            
            # 2. 查找目标国家
            cursor.execute(
                "SELECT id FROM nations WHERE name = ?",
                (target_nation_name,)
            )
            target_nation = cursor.fetchone()
            
            if not target_nation:
                yield event.plain_result(f"国家 {target_nation_name} 不存在")
                return
            
            defender_id = target_nation[0]
            
            # 3. 检查是否存在自己发起的战争
            cursor.execute(
                "SELECT id FROM wars WHERE attacker_id = ? AND defender_id = ? AND status = 'active'",
                (attacker_id, defender_id)
            )
            war_record = cursor.fetchone()
            
            if not war_record:
                yield event.plain_result(f"没有发起对 {target_nation_name} 的战争，无法终止")
                return
            
            # 4. 终止战争
            cursor.execute(
                "UPDATE wars SET status = 'ended' WHERE id = ?",
                (war_record[0],)
            )
            
            conn.commit()
            yield event.plain_result(f"已终止与国家 {target_nation_name} 的战争")
        except Exception as e:
            logger.error(f"终止战争失败: {e}")
            yield event.plain_result("终止战争失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("查看当前战争")
    async def view_current_wars(self, event: AstrMessageEvent):
        """查看当前国家的战争状态"""
        user_id = event.get_sender_id()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 检查用户是否加入了国家
            cursor.execute(
                "SELECT un.nation_id, n.name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ?",
                (user_id,)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("你还没有加入任何国家")
                return
            
            nation_id, nation_name = nation_info
            
            # 2. 查询当前国家的战争记录
            cursor.execute(
                "SELECT a.name as attacker_name, d.name as defender_name, w.status FROM wars w JOIN nations a ON w.attacker_id = a.id JOIN nations d ON w.defender_id = d.id WHERE (w.attacker_id = ? OR w.defender_id = ?) AND w.status = 'active'",
                (nation_id, nation_id)
            )
            wars = cursor.fetchall()
            
            if not wars:
                yield event.plain_result("1.\n无战争")
                return
            
            result = ""
            for i, (attacker_name, defender_name, status) in enumerate(wars, 1):
                result += f"{i}.\n"
                if attacker_name == nation_name:
                    result += f"我方进攻《{defender_name}》（这是我们宣战目标）\n"
                else:
                    result += f"《{attacker_name}》攻击我国（这是被宣战）\n"
            
            yield event.plain_result(result.strip())
        except Exception as e:
            logger.error(f"查看当前战争失败: {e}")
            yield event.plain_result("查看当前战争失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("战争记录")
    async def view_war_history(self, event: AstrMessageEvent):
        """查看历史战争记录，最多显示10条"""
        user_id = event.get_sender_id()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 检查用户是否加入了国家
            cursor.execute(
                "SELECT un.nation_id, n.name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ?",
                (user_id,)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("你还没有加入任何国家")
                return
            
            nation_id, nation_name = nation_info
            
            # 2. 查询历史战争记录，最多10条，按时间倒序
            cursor.execute(
                "SELECT a.name as attacker_name, d.name as defender_name, w.status, w.start_time FROM wars w JOIN nations a ON w.attacker_id = a.id JOIN nations d ON w.defender_id = d.id WHERE w.attacker_id = ? OR w.defender_id = ? ORDER BY w.start_time DESC LIMIT 10",
                (nation_id, nation_id)
            )
            wars = cursor.fetchall()
            
            if not wars:
                yield event.plain_result("战争记录：\n无历史战争记录")
                return
            
            result = "战争记录：\n"
            for i, (attacker_name, defender_name, status, start_time) in enumerate(wars, 1):
                if attacker_name == nation_name:
                    result += f"{i}.我方进攻《{defender_name}》（这是我们宣战目标）\n"
                else:
                    result += f"{i}.《{attacker_name}》攻击我国（这是被宣战）\n"
            
            yield event.plain_result(result.strip())
        except Exception as e:
            logger.error(f"查看战争记录失败: {e}")
            yield event.plain_result("查看战争记录失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("建交")
    async def send_diplomacy_request(self, event: AstrMessageEvent):
        """向指定国家发送建交请求（可选择赠送国礼）"""
        user_id = event.get_sender_id()
        message_str = event.message_str.strip()
        
        # 解析参数
        if len(message_str) < 3:  # "/建交 " 是3个字符
            yield event.plain_result("请输入正确格式：/建交 <目标国家> <赠礼物品> <赠礼数量>（赠礼可选，目前只能赠国礼）")
            return
        
        params = message_str[3:].strip().split(" ")
        if len(params) < 1:
            yield event.plain_result("请输入正确格式：/建交 <目标国家> <赠礼物品> <赠礼数量>（赠礼可选，目前只能赠国礼）")
            return
        
        target_nation_name = params[0].strip()
        gift_type = None
        gift_amount = 0
        
        # 解析赠礼参数
        if len(params) >= 3 and params[1].strip() == "国礼":
            try:
                gift_type = "国礼"
                gift_amount = int(params[2].strip())
            except ValueError:
                yield event.plain_result("赠礼数量必须是数字")
                return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 检查用户是否是国家创建者
            cursor.execute(
                "SELECT n.id, n.name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ? AND n.creator_id = ?",
                (user_id, user_id)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("只有国家创建者才能发送建交请求")
                return
            
            from_nation_id, from_nation_name = nation_info
            
            # 2. 查找目标国家
            cursor.execute(
                "SELECT id FROM nations WHERE name = ?",
                (target_nation_name,)
            )
            target_nation = cursor.fetchone()
            
            if not target_nation:
                yield event.plain_result(f"国家 {target_nation_name} 不存在")
                return
            
            to_nation_id = target_nation[0]
            
            # 3. 检查是否是自己国家
            if from_nation_id == to_nation_id:
                yield event.plain_result("不能向自己的国家发送建交请求")
                return
            
            # 4. 检查是否已经有未处理的建交请求
            cursor.execute(
                "SELECT id FROM diplomacy_requests WHERE from_nation_id = ? AND to_nation_id = ? AND status = 'pending'",
                (from_nation_id, to_nation_id)
            )
            existing_request = cursor.fetchone()
            
            if existing_request:
                yield event.plain_result(f"已经向 {target_nation_name} 发送过建交请求，对方尚未回复")
                return
            
            # 5. 检查国库是否有足够的国礼
            if gift_type == "国礼" and gift_amount > 0:
                cursor.execute(
                    "SELECT gift FROM nation_treasury WHERE nation_id = ?",
                    (from_nation_id,)
                )
                treasury = cursor.fetchone()
                if not treasury or treasury[0] < gift_amount:
                    yield event.plain_result(f"国库国礼不足，当前只有 {treasury[0] if treasury else 0} 个国礼")
                    return
                
                # 6. 扣除国库国礼
                cursor.execute(
                    "UPDATE nation_treasury SET gift = gift - ? WHERE nation_id = ?",
                    (gift_amount, from_nation_id)
                )
            
            # 7. 创建外交请求
            cursor.execute(
                "INSERT INTO diplomacy_requests (from_nation_id, to_nation_id, request_type, gift_type, gift_amount) VALUES (?, ?, ?, ?, ?)",
                (from_nation_id, to_nation_id, "建交", gift_type, gift_amount)
            )
            
            conn.commit()
            if gift_type and gift_amount > 0:
                yield event.plain_result(f"已向国家 {target_nation_name} 发送建交请求，并赠送国礼 {gift_amount}")
            else:
                yield event.plain_result(f"已向国家 {target_nation_name} 发送建交请求")
        except Exception as e:
            logger.error(f"发送建交请求失败: {e}")
            yield event.plain_result("发送建交请求失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("查看外交")
    async def view_diplomacy(self, event: AstrMessageEvent):
        """查看收到的外交请求"""
        user_id = event.get_sender_id()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 检查用户是否是国家创建者
            cursor.execute(
                "SELECT n.id, n.name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ? AND n.creator_id = ?",
                (user_id, user_id)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("只有国家创建者才能查看外交请求")
                return
            
            nation_id, nation_name = nation_info
            
            # 2. 查询外交请求
            cursor.execute(
                "SELECT fn.name as from_nation_name, dr.gift_type, dr.gift_amount, dr.status FROM diplomacy_requests dr JOIN nations fn ON dr.from_nation_id = fn.id WHERE dr.to_nation_id = ?",
                (nation_id,)
            )
            requests = cursor.fetchall()
            
            if not requests:
                yield event.plain_result("1.\n无外交事件")
                return
            
            result = ""
            for i, (from_nation_name, gift_type, gift_amount, status) in enumerate(requests, 1):
                result += f"{i}.\n"
                if gift_type and gift_amount > 0:
                    result += f"【{from_nation_name}】要与我国建交，赠送国礼{gift_amount}。[{status}]（有赠礼）\n"
                else:
                    result += f"【{from_nation_name}】要与我国建交，未赠国礼。[{status}]（无赠礼）\n"
            
            yield event.plain_result(result.strip())
        except Exception as e:
            logger.error(f"查看外交请求失败: {e}")
            yield event.plain_result("查看外交请求失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("回应外交")
    async def respond_diplomacy(self, event: AstrMessageEvent):
        """回应外交请求"""
        user_id = event.get_sender_id()
        message_str = event.message_str.strip()
        
        # 解析参数
        if len(message_str) < 6:  # "/回应外交 " 是6个字符
            yield event.plain_result("请输入正确格式：/回应外交 <建交> <拒绝/同意> <目标国家>")
            return
        
        params = message_str[6:].strip().split(" ", 2)
        if len(params) < 3:
            yield event.plain_result("请输入正确格式：/回应外交 <建交> <拒绝/同意> <目标国家>")
            return
        
        request_type, response, target_nation_name = params[0].strip(), params[1].strip(), params[2].strip()
        
        if request_type != "建交":
            yield event.plain_result("目前只支持回应建交请求")
            return
        
        if response not in ["同意", "拒绝"]:
            yield event.plain_result("回应必须是'同意'或'拒绝'")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 检查用户是否是国家创建者
            cursor.execute(
                "SELECT n.id, n.name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ? AND n.creator_id = ?",
                (user_id, user_id)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("只有国家创建者才能回应外交请求")
                return
            
            to_nation_id, to_nation_name = nation_info
            
            # 2. 查找目标国家
            cursor.execute(
                "SELECT id FROM nations WHERE name = ?",
                (target_nation_name,)
            )
            target_nation = cursor.fetchone()
            
            if not target_nation:
                yield event.plain_result(f"国家 {target_nation_name} 不存在")
                return
            
            from_nation_id = target_nation[0]
            
            # 3. 查询外交请求
            cursor.execute(
                "SELECT id, gift_type, gift_amount FROM diplomacy_requests WHERE from_nation_id = ? AND to_nation_id = ? AND status = 'pending'",
                (from_nation_id, to_nation_id)
            )
            request = cursor.fetchone()
            
            if not request:
                yield event.plain_result(f"没有来自 {target_nation_name} 的未处理建交请求")
                return
            
            request_id, gift_type, gift_amount = request
            
            if response == "同意":
                # 4. 处理国礼（如果有）
                if gift_type and gift_amount > 0:
                    cursor.execute(
                        "UPDATE nation_treasury SET gift = gift + ? WHERE nation_id = ?",
                        (gift_amount, to_nation_id)
                    )
                
                # 5. 创建外交关系
                try:
                    cursor.execute(
                        "INSERT INTO diplomacy_relations (nation1_id, nation2_id) VALUES (?, ?)",
                        (from_nation_id, to_nation_id)
                    )
                except sqlite3.IntegrityError:
                    # 外交关系已存在
                    pass
                
                # 6. 更新请求状态
                cursor.execute(
                    "UPDATE diplomacy_requests SET status = '已答应' WHERE id = ?",
                    (request_id,)
                )
                
                yield event.plain_result(f"已同意 {target_nation_name} 的建交请求")
            else:
                # 7. 拒绝请求
                cursor.execute(
                    "UPDATE diplomacy_requests SET status = '已拒绝' WHERE id = ?",
                    (request_id,)
                )
                
                # 8. 返还国礼（如果有）
                if gift_type and gift_amount > 0:
                    cursor.execute(
                        "UPDATE nation_treasury SET gift = gift + ? WHERE nation_id = ?",
                        (gift_amount, from_nation_id)
                    )
                
                yield event.plain_result(f"已拒绝 {target_nation_name} 的建交请求")
            
            conn.commit()
        except Exception as e:
            logger.error(f"回应外交请求失败: {e}")
            yield event.plain_result("回应外交请求失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("查看外交关系")
    async def view_diplomacy_relations(self, event: AstrMessageEvent):
        """查看当前国家的外交关系"""
        user_id = event.get_sender_id()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 检查用户是否加入了国家
            cursor.execute(
                "SELECT un.nation_id, n.name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ?",
                (user_id,)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("你还没有加入任何国家")
                return
            
            nation_id, nation_name = nation_info
            
            # 2. 查询外交关系
            cursor.execute("SELECT CASE WHEN nation1_id = ? THEN n2.name ELSE n1.name END as other_nation_name, relation_type FROM diplomacy_relations dr JOIN nations n1 ON dr.nation1_id = n1.id JOIN nations n2 ON dr.nation2_id = n2.id WHERE nation1_id = ? OR nation2_id = ?", (nation_id, nation_id, nation_id))
            relations = cursor.fetchall()
            
            if not relations:
                yield event.plain_result("1.\n无外交关系")
                return
            
            result = ""
            for i, (other_nation_name, relation_type) in enumerate(relations, 1):
                result += f"{i}.【{relation_type}】{other_nation_name}\n"
            
            yield event.plain_result(result.strip())
        except Exception as e:
            logger.error(f"查看外交关系失败: {e}")
            yield event.plain_result("查看外交关系失败，请稍后重试")
        finally:
            conn.close()
    
    @filter.command("解除外交")
    async def break_diplomacy(self, event: AstrMessageEvent):
        """解除与指定国家的外交关系"""
        user_id = event.get_sender_id()
        message_str = event.message_str.strip()
        
        # 解析参数
        if len(message_str) < 5:  # "/解除外交 " 是5个字符
            yield event.plain_result("请输入正确格式：/解除外交 <目标国家>")
            return
        
        target_nation_name = message_str[5:].strip()
        if not target_nation_name:
            yield event.plain_result("国家名称不能为空")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 检查用户是否是国家创建者
            cursor.execute(
                "SELECT n.id, n.name FROM user_nations un JOIN nations n ON un.nation_id = n.id WHERE un.user_id = ? AND n.creator_id = ?",
                (user_id, user_id)
            )
            nation_info = cursor.fetchone()
            
            if not nation_info:
                yield event.plain_result("只有国家创建者才能解除外交关系")
                return
            
            from_nation_id, from_nation_name = nation_info
            
            # 2. 查找目标国家
            cursor.execute(
                "SELECT id, name FROM nations WHERE name = ?",
                (target_nation_name,)
            )
            target_nation = cursor.fetchone()
            
            if not target_nation:
                yield event.plain_result(f"国家 {target_nation_name} 不存在")
                return
            
            to_nation_id, to_nation_name = target_nation
            
            # 3. 检查是否存在外交关系
            cursor.execute(
                "SELECT id FROM diplomacy_relations WHERE (nation1_id = ? AND nation2_id = ?) OR (nation1_id = ? AND nation2_id = ?)",
                (from_nation_id, to_nation_id, to_nation_id, from_nation_id)
            )
            relation = cursor.fetchone()
            
            if not relation:
                yield event.plain_result(f"与国家 {target_nation_name} 没有外交关系")
                return
            
            # 4. 删除外交关系
            cursor.execute(
                "DELETE FROM diplomacy_relations WHERE (nation1_id = ? AND nation2_id = ?) OR (nation1_id = ? AND nation2_id = ?)",
                (from_nation_id, to_nation_id, to_nation_id, from_nation_id)
            )
            
            conn.commit()
            yield event.plain_result(f"已解除与国家 {target_nation_name} 的外交关系")
        except Exception as e:
            logger.error(f"解除外交关系失败: {e}")
            yield event.plain_result("解除外交关系失败，请稍后重试")
        finally:
            conn.close()
    
    async def terminate(self):
        """插件被卸载/停用时调用"""
        logger.info("虚拟国政插件已关闭")
