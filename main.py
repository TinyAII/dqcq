#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟国战游戏主程序
"""

import os
import sqlite3
import datetime
import logging
from typing import Dict, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VirtualWarGame:
    """
    虚拟国战游戏主类
    """
    
    def __init__(self, db_path: str = "virtual_war.db"):
        """
        初始化游戏
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.db = DatabaseManager(db_path)
        
    def handle_command(self, qq_id: str, qq_name: str, command: str) -> str:
        """
        处理玩家指令
        
        Args:
            qq_id: 玩家QQ号
            qq_name: 玩家QQ名
            command: 指令内容
            
        Returns:
            指令执行结果
        """
        command = command.strip()
        
        if command == "/注册":
            return self.register_player(qq_id, qq_name)
        elif command == "/我的信息":
            return self.show_player_info(qq_id)
        elif command == "/每日签到":
            return self.daily_checkin(qq_id)
        elif command == "/帮助":
            return self.show_help()
        else:
            return "未知指令，请输入/帮助查看可用指令"
    
    def register_player(self, qq_id: str, qq_name: str) -> str:
        """
        注册玩家
        
        Args:
            qq_id: 玩家QQ号
            qq_name: 玩家QQ名
            
        Returns:
            注册结果
        """
        return self.db.register_player(qq_id, qq_name)
    
    def show_player_info(self, qq_id: str) -> str:
        """
        查看玩家信息
        
        Args:
            qq_id: 玩家QQ号
            
        Returns:
            玩家信息
        """
        return self.db.get_player_info(qq_id)
    
    def daily_checkin(self, qq_id: str) -> str:
        """
        每日签到
        
        Args:
            qq_id: 玩家QQ号
            
        Returns:
            签到结果
        """
        return self.db.daily_checkin(qq_id)
    
    def show_help(self) -> str:
        """
        显示帮助信息
        
        Returns:
            帮助信息
        """
        help_text = """虚拟国战游戏指令帮助：
/注册 - 注册成为玩家
/我的信息 - 查看个人信息
/每日签到 - 领取每日奖励
/帮助 - 查看帮助文档
"""
        return help_text



class DatabaseManager:
    """
    数据库管理类
    """
    
    def __init__(self, db_path: str):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._create_tables()
    
    def _create_tables(self):
        """
        创建数据库表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建玩家表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            qq_id TEXT PRIMARY KEY,
            qq_name TEXT NOT NULL,
            register_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_checkin_date DATE,
            checkin_count INTEGER DEFAULT 0,
            gold INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            experience INTEGER DEFAULT 0
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_player(self, qq_id: str, qq_name: str) -> str:
        """
        注册玩家
        
        Args:
            qq_id: 玩家QQ号
            qq_name: 玩家QQ名
            
        Returns:
            注册结果
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查玩家是否已注册
            cursor.execute("SELECT qq_id FROM players WHERE qq_id = ?", (qq_id,))
            if cursor.fetchone():
                return "您已注册过，无需重复注册"
            
            # 注册新玩家
            cursor.execute(
                "INSERT INTO players (qq_id, qq_name) VALUES (?, ?)",
                (qq_id, qq_name)
            )
            conn.commit()
            return f"注册成功！玩家{qq_name}"
        except Exception as e:
            logger.error(f"注册玩家失败: {e}")
            return "注册失败，请稍后重试"
        finally:
            conn.close()
    
    def get_player_info(self, qq_id: str) -> str:
        """
        获取玩家信息
        
        Args:
            qq_id: 玩家QQ号
            
        Returns:
            玩家信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT qq_name, register_time, last_checkin_date, checkin_count, gold, level, experience FROM players WHERE qq_id = ?",
                (qq_id,)
            )
            player = cursor.fetchone()
            
            if not player:
                return "您还未注册，请先输入/注册"
            
            qq_name, register_time, last_checkin_date, checkin_count, gold, level, experience = player
            
            info = f"""玩家信息：
昵称：{qq_name}
注册时间：{register_time}
签到次数：{checkin_count}
金币：{gold}
等级：{level}
经验：{experience}
"""
            
            if last_checkin_date:
                info += f"上次签到：{last_checkin_date}"
            else:
                info += "还未签到过"
            
            return info
        except Exception as e:
            logger.error(f"获取玩家信息失败: {e}")
            return "获取信息失败，请稍后重试"
        finally:
            conn.close()
    
    def daily_checkin(self, qq_id: str) -> str:
        """
        每日签到
        
        Args:
            qq_id: 玩家QQ号
            
        Returns:
            签到结果
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查玩家是否已注册
            cursor.execute("SELECT qq_name, last_checkin_date FROM players WHERE qq_id = ?", (qq_id,))
            player = cursor.fetchone()
            
            if not player:
                return "您还未注册，请先输入/注册"
            
            qq_name, last_checkin_date = player
            today = datetime.date.today()
            
            # 检查是否已签到
            if last_checkin_date == today.isoformat():
                return "您今天已签到，明日再来"
            
            # 执行签到
            cursor.execute(
                "UPDATE players SET last_checkin_date = ?, checkin_count = checkin_count + 1, gold = gold + 100, experience = experience + 50 WHERE qq_id = ?",
                (today.isoformat(), qq_id)
            )
            conn.commit()
            
            return f"{qq_name}，签到成功！获得100金币和50经验"
        except Exception as e:
            logger.error(f"每日签到失败: {e}")
            return "签到失败，请稍后重试"
        finally:
            conn.close()

# 测试代码
if __name__ == "__main__":
    game = VirtualWarGame()
    
    # 测试指令处理
    print("=== 虚拟国战游戏测试 ===")
    print(game.handle_command("123456", "测试玩家", "/注册"))
    print(game.handle_command("123456", "测试玩家", "/我的信息"))
    print(game.handle_command("123456", "测试玩家", "/每日签到"))
    print(game.handle_command("123456", "测试玩家", "/每日签到"))  # 重复签到
    print(game.handle_command("123456", "测试玩家", "/我的信息"))
    print(game.handle_command("123456", "测试玩家", "/帮助"))
    print(game.handle_command("654321", "未注册玩家", "/我的信息"))