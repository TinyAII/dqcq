from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
from astrbot.api.event import filter
from astrbot.api.star import Star, register
from astrbot.api import logger
import httpx

API_URL = "http://api.tinyaii.top/index.php"

# 菜单样式的HTML模板（参考工具箱插件样式）
MENU_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文字斗气菜单</title>
    <style>
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 20px;
            line-height: 2.0;
        }
        .container {
            max-width: 950px;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        }
        .menu-title {
            font-size: 32px;
            font-weight: bold;
            color: #28a745;
            text-align: center;
            margin-bottom: 40px;
            padding: 15px;
            background-color: #e8f5e8;
            border-radius: 8px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        .category-title {
            font-size: 24px;
            font-weight: bold;
            color: #17a2b8;
            margin: 30px 0 20px 0;
            padding: 10px 0;
            border-bottom: 3px solid #17a2b8;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .menu-item {
            font-size: 18px;
            line-height: 2.2;
            margin: 15px 0;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #ffc107;
        }
        .command-name {
            font-weight: bold;
            color: #dc3545;
            font-size: 24px;
        }
        .command-format {
            color: #dc3545;
            font-weight: bold;
            font-size: 20px;
        }
        .command-desc {
            color: #495057;
            font-weight: bold;
        }
        .example-section {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e9ecef;
        }
        .example-title {
            font-size: 22px;
            font-weight: bold;
            color: #6f42c1;
            margin-bottom: 20px;
        }
        .example-item {
            font-size: 16px;
            line-height: 1.8;
            margin: 10px 0;
            padding: 10px;
            background-color: #e7f5ff;
            border-radius: 6px;
            border-left: 4px solid #007bff;
        }
        .note-section {
            margin-top: 30px;
            padding: 15px;
            background-color: #fff3cd;
            border: 1px solid #ffeeba;
            border-radius: 6px;
            color: #856404;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="menu-title">📚 文字斗气指令列表 📚</h1>
        {{content}}
        <div class="note-section">
            💡 输入指令前不需要加斜杠，直接输入指令即可！
        </div>
    </div>
</body>
</html>
'''

# 个人信息样式的HTML模板
PERSONAL_INFO_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>斗气角色信息</title>
    <style>
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 30px;
            line-height: 1.6;
            color: #333;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.15);
        }
        .title {
            font-size: 36px;
            font-weight: bold;
            text-align: center;
            color: #2c3e50;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        .basic-info {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 10px;
        }
        .username {
            font-size: 28px;
            font-weight: bold;
            color: #e74c3c;
            margin-bottom: 10px;
        }
        .create-time {
            font-size: 16px;
            color: #7f8c8d;
        }
        .section {
            margin: 30px 0;
            padding: 25px;
            background-color: #f8f9fa;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .section-title {
            font-size: 22px;
            font-weight: bold;
            color: #3498db;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #3498db;
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .info-item {
            background-color: white;
            padding: 18px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .info-label {
            font-size: 14px;
            color: #7f8c8d;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .info-value {
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
        }
        .list-section {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .list-item {
            margin: 15px 0;
            padding: 12px;
            background-color: #f0f8ff;
            border-radius: 6px;
            border-left: 4px solid #3498db;
        }
        .list-empty {
            text-align: center;
            color: #95a5a6;
            font-style: italic;
            padding: 20px;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            color: #7f8c8d;
            font-size: 14px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="title">📋 斗气角色详细信息 📋</h1>
        
        <!-- 基本信息 -->
        <div class="basic-info">
            <div class="username">{{username}}</div>
            <div class="create-time">创建时间：{{create_time}}</div>
        </div>
        
        <!-- 斗气状态 -->
        <div class="section">
            <h2 class="section-title">💫 斗气状态</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">等级</div>
                    <div class="info-value">{{level}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">修为</div>
                    <div class="info-value">{{cultivation}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">境界</div>
                    <div class="info-value">{{realm}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">经验值</div>
                    <div class="info-value">{{experience}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">斗气值</div>
                    <div class="info-value">{{battle_qi}}</div>
                </div>
            </div>
        </div>
        
        <!-- 属性 -->
        <div class="section">
            <h2 class="section-title">⚡ 属性</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">生命值</div>
                    <div class="info-value">{{health}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">灵力值</div>
                    <div class="info-value">{{mana}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">体力值</div>
                    <div class="info-value">{{stamina}}</div>
                </div>
            </div>
        </div>
        
        <!-- 财富 -->
        <div class="section">
            <h2 class="section-title">💰 财富</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">金币</div>
                    <div class="info-value">{{gold}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">灵石</div>
                    <div class="info-value">{{spirit_stone}}</div>
                </div>
            </div>
        </div>
        
        <!-- 突破信息 -->
        <div class="section">
            <h2 class="section-title">🚀 突破信息</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">下一境界</div>
                    <div class="info-value">{{next_realm}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">所需斗气</div>
                    <div class="info-value">{{required_battle_qi}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">当前斗气</div>
                    <div class="info-value">{{current_battle_qi}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">突破成功率</div>
                    <div class="info-value">{{breakthrough_rate}}</div>
                </div>
                <div class="info-item" style="grid-column: 1 / -1;">
                    <div class="info-label">突破需求</div>
                    <div class="info-value">{{breakthrough_requirement}}</div>
                </div>
            </div>
        </div>
        
        <!-- 修炼冷却 -->
        <div class="section">
            <h2 class="section-title">⏰ 修炼冷却</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">打坐</div>
                    <div class="info-value">{{cd_meditate}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">突破</div>
                    <div class="info-value">{{cd_breakthrough}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">调息</div>
                    <div class="info-value">{{cd_recover}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">闭关</div>
                    <div class="info-value">{{cd_seclusion}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">切磋</div>
                    <div class="info-value">{{cd_duel}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">赠送</div>
                    <div class="info-value">{{cd_give}}</div>
                </div>
            </div>
        </div>
        
        <!-- 切磋战绩 -->
        <div class="section">
            <h2 class="section-title">⚔️ 切磋战绩</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">胜利</div>
                    <div class="info-value">{{battle_wins}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">失败</div>
                    <div class="info-value">{{battle_losses}}</div>
                </div>
            </div>
        </div>
        
        <!-- 道友列表 -->
        <div class="section">
            <h2 class="section-title">👥 道友列表</h2>
            <div class="list-section">
                {% if friends %}
                    {% for friend in friends %}
                        <div class="list-item">{{friend}}</div>
                    {% endfor %}
                {% else %}
                    <div class="list-empty">暂无道友</div>
                {% endif %}
            </div>
        </div>
        
        <!-- 技能 -->
        <div class="section">
            <h2 class="section-title">✨ 技能</h2>
            <div class="list-section">
                {% if skills %}
                    {% for skill in skills %}
                        <div class="list-item">{{skill}}</div>
                    {% endfor %}
                {% else %}
                    <div class="list-empty">暂无技能</div>
                {% endif %}
            </div>
        </div>
        
        <!-- 物品 -->
        <div class="section">
            <h2 class="section-title">🎒 物品</h2>
            <div class="list-section">
                {% if items %}
                    {% for item in items %}
                        <div class="list-item">{{item}}</div>
                    {% endfor %}
                {% else %}
                    <div class="list-empty">暂无物品</div>
                {% endif %}
            </div>
        </div>
        
        <div class="footer">
            查询时间：{{current_time}} | 文字斗气系统
        </div>
    </div>
</body>
</html>
'''

@register("literary_battle_qi", "author", "文字斗气机器人插件", "1.0.0")
class LiteraryBattleQiBot(Star):
    def __init__(self, context):
        super().__init__(context)
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def _call_api(self, action, params):
        """调用API的通用方法"""
        try:
            response = await self.client.get(API_URL, params={"action": action, **params})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"API请求失败: {e}")
            return {"code": 500, "message": "服务器连接失败，请稍后重试"}
        except Exception as e:
            logger.error(f"API处理失败: {e}")
            return {"code": 500, "message": "服务器内部错误，请稍后重试"}
    
    def _format_response(self, response):
        """格式化API响应"""
        code = response.get("code")
        message = response.get("message", "未知错误")
        data = response.get("data")
        
        if code != 200:
            return f"❌ {message}"
        
        return message
    
    async def text_to_image_menu_style(self, text, *args, **kwargs):
        """使用菜单样式的HTML模板生成图片"""
        try:
            # 将文本内容转换为结构化HTML
            lines = text.split('\n')
            html_parts = []
            
            # 添加分类标题
            html_parts.append('<div class="category-title">📚 斗气修炼指令</div>')
            
            # 处理指令列表
            for line in lines:
                line = line.strip()
                if not line or line.startswith('📚') or line.startswith('💡'):
                    continue
                
                # 解析指令行
                if ' - ' in line:
                    command_part, desc_part = line.split(' - ', 1)
                    # 提取指令名称（去除🔹 **和**）
                    command_name = command_part.replace('🔹 **', '').replace('**', '').strip()
                    command_desc = desc_part.strip()
                    
                    # 生成HTML
                    html_parts.append(f'<div class="menu-item">')
                    html_parts.append(f'<span class="command-format">{command_name}</span>')
                    html_parts.append(f'<span class="command-desc"> - {command_desc}</span>')
                    html_parts.append(f'</div>')
            
            # 组装最终HTML内容
            formatted_html = '\n'.join(html_parts)
            
            # 渲染HTML模板
            html_content = MENU_TEMPLATE.replace("{{content}}", formatted_html)
            
            # 使用html_render函数生成图片
            options = {
                "full_page": True,
                "type": "jpeg",
                "quality": 95,
            }
            
            # 调用AstrBot的html_render方法
            image_url = await self.html_render(
                html_content,  # 渲染后的HTML内容
                {},  # 空数据字典
                True,  # 返回URL
                options  # 图片生成选项
            )
            
            return image_url
        except Exception as e:
            logger.error(f"菜单样式图片生成失败：{e}")
            # 回退到默认的纯文本输出
            return None
    
    async def render_personal_info_image(self, data):
        """使用个人信息模板生成图片"""
        try:
            # 提取数据
            basic = data.get("基本信息", {})
            battle_qi = data.get("斗气状态", {})
            attributes = data.get("属性", {})
            wealth = data.get("财富", {})
            cooldowns = data.get("修炼冷却", {})
            breakthrough = data.get("突破信息", {})
            friends = data.get("道友列表", [])
            battle = data.get("切磋战绩", {})
            skills = data.get("技能", [])
            items = data.get("物品", [])
            
            # 格式化当前时间
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 替换模板变量
            html_content = PERSONAL_INFO_TEMPLATE
            html_content = html_content.replace("{{username}}", basic.get('用户名', ''))
            html_content = html_content.replace("{{create_time}}", basic.get('创建时间', ''))
            html_content = html_content.replace("{{level}}", str(battle_qi.get('等级', 0)))
            html_content = html_content.replace("{{cultivation}}", str(battle_qi.get('修为', 0)))
            html_content = html_content.replace("{{realm}}", battle_qi.get('境界', ''))
            html_content = html_content.replace("{{experience}}", str(battle_qi.get('经验值', 0)))
            html_content = html_content.replace("{{battle_qi}}", str(battle_qi.get('斗气值', 0)))
            html_content = html_content.replace("{{health}}", str(attributes.get('生命值', 0)))
            html_content = html_content.replace("{{mana}}", str(attributes.get('灵力值', 0)))
            html_content = html_content.replace("{{stamina}}", str(attributes.get('体力值', 0)))
            html_content = html_content.replace("{{gold}}", str(wealth.get('金币', 0)))
            html_content = html_content.replace("{{spirit_stone}}", str(wealth.get('灵石', 0)))
            html_content = html_content.replace("{{next_realm}}", breakthrough.get('下一境界', ''))
            html_content = html_content.replace("{{required_battle_qi}}", str(breakthrough.get('所需斗气', 0)))
            html_content = html_content.replace("{{current_battle_qi}}", str(breakthrough.get('当前斗气', 0)))
            html_content = html_content.replace("{{breakthrough_rate}}", str(breakthrough.get('突破成功率', 0)))
            html_content = html_content.replace("{{breakthrough_requirement}}", breakthrough.get('突破需求', ''))
            html_content = html_content.replace("{{cd_meditate}}", cooldowns.get('打坐', ''))
            html_content = html_content.replace("{{cd_breakthrough}}", cooldowns.get('突破', ''))
            html_content = html_content.replace("{{cd_recover}}", cooldowns.get('调息', ''))
            html_content = html_content.replace("{{cd_seclusion}}", cooldowns.get('闭关', ''))
            html_content = html_content.replace("{{cd_duel}}", cooldowns.get('切磋', ''))
            html_content = html_content.replace("{{cd_give}}", cooldowns.get('赠送', ''))
            html_content = html_content.replace("{{battle_wins}}", str(battle.get('胜利', 0)))
            html_content = html_content.replace("{{battle_losses}}", str(battle.get('失败', 0)))
            html_content = html_content.replace("{{current_time}}", current_time)
            
            # 处理列表数据
            friends_html = '\n'.join([f'<div class="list-item">{friend}</div>' for friend in friends]) if friends else '<div class="list-empty">暂无道友</div>'
            skills_html = '\n'.join([f'<div class="list-item">{skill}</div>' for skill in skills]) if skills else '<div class="list-empty">暂无技能</div>'
            items_html = '\n'.join([f'<div class="list-item">{item}</div>' for item in items]) if items else '<div class="list-empty">暂无物品</div>'
            
            # 替换列表变量
            html_content = html_content.replace("{% if friends %}\n                    {% for friend in friends %}\n                        <div class=\"list-item\">{{friend}}</div>\n                    {% endfor %}\n                {% else %}\n                    <div class=\"list-empty\">暂无道友</div>\n                {% endif %}", friends_html)
            html_content = html_content.replace("{% if skills %}\n                    {% for skill in skills %}\n                        <div class=\"list-item\">{{skill}}</div>\n                    {% endfor %}\n                {% else %}\n                    <div class=\"list-empty\">暂无技能</div>\n                {% endif %}", skills_html)
            html_content = html_content.replace("{% if items %}\n                    {% for item in items %}\n                        <div class=\"list-item\">{{item}}</div>\n                    {% endfor %}\n                {% else %}\n                    <div class=\"list-empty\">暂无物品</div>\n                {% endif %}", items_html)
            
            # 使用html_render函数生成图片
            options = {
                "full_page": True,
                "type": "jpeg",
                "quality": 95,
            }
            
            # 调用AstrBot的html_render方法
            image_url = await self.html_render(
                html_content,  # 渲染后的HTML内容
                {},  # 空数据字典
                True,  # 返回URL
                options  # 图片生成选项
            )
            
            return image_url
        except Exception as e:
            logger.error(f"个人信息图片生成失败：{e}")
            # 回退到默认的纯文本输出
            return None
    
    @filter.command("斗气帮助", alias={"帮助", "斗气指令"})
    async def help(self, event):
        """查看所有指令说明"""
        help_text = (
                     "🔹 **斗气帮助**   - 查看所有指令说明\n" +
                     "🔹 **创建角色**   - 创建斗气角色（自动使用你的QQ号，无需额外参数）\n" +
                     "🔹 **状态**       - 查看自己的斗气状态\n" +
                     "🔹 **个人信息**   - 查看详细角色信息\n" +
                     "🔹 **打坐**       - 基础修炼获得斗气（冷却10分钟）\n" +
                     "🔹 **突破**       - 消耗斗气突破境界\n" +
                     "🔹 **调息**       - 恢复生命和灵力（冷却30分钟）\n" +
                     "🔹 **闭关**       - 深度修炼获得更多斗气（格式：闭关 [时长]，冷却2小时）\n" +
                     "🔹 **排行榜**     - 查看斗气排行榜\n" +
                     "🔹 **道友**       - 查看好友/道友列表\n" +
                     "🔹 **切磋**       - 与道友切磋（格式：切磋 @目标QQ号）\n" +
                     "🔹 **赠送**       - 赠送物品给道友（格式：赠送 @目标QQ号 物品x数量）\n" +
                     ""
                     )
        
        # 尝试生成图片
        image_url = await self.text_to_image_menu_style(help_text)
        
        if image_url:
            # 如果生成图片成功，发送图片
            yield event.image_result(image_url).use_t2i(False)
        else:
            # 否则发送纯文本
            yield event.plain_result(help_text)
    
    @filter.command("创建角色", alias={"注册", "开始斗气"})
    async def create_character(self, event):
        """创建斗气角色"""
        # 自动获取用户的QQ号作为用户名
        username = str(event.message_obj.sender.user_id)
        
        response = await self._call_api("创建角色", {"username": username})
        yield event.plain_result(self._format_response(response))
    
    @filter.command("状态", alias={"我的状态", "查看状态"})
    async def status(self, event):
        """查看自己的斗气状态"""
        # 自动获取用户的QQ号作为用户名
        username = str(event.message_obj.sender.user_id)
        
        response = await self._call_api("状态", {"username": username})
        
        if response.get("code") != 200:
            yield event.plain_result(self._format_response(response))
            return
        
        data = response.get("data", {})
        status_text = f"""🌟 {data.get('用户名')} 的状态信息：

📊 等级：{data.get('等级')}
🛡️ 修为：{data.get('修为')}
✨ 境界：{data.get('境界')}
📈 经验：{data.get('经验')}
❤️ 生命值：{data.get('生命值')}
💧 灵力值：{data.get('灵力值')}
💫 斗气值：{data.get('斗气值')}
⚡ 体力值：{data.get('体力值')}
💰 金币：{data.get('金币')}
💎 灵石：{data.get('灵石')}
"""
        yield event.plain_result(status_text)
    
    @filter.command("个人信息", alias={"信息", "我的信息"})
    async def personal_info(self, event):
        """查看详细角色信息"""
        # 自动获取用户的QQ号作为用户名
        username = str(event.message_obj.sender.user_id)
        
        response = await self._call_api("个人信息", {"username": username})
        
        if response.get("code") != 200:
            yield event.plain_result(self._format_response(response))
            return
        
        data = response.get("data", {})
        
        # 尝试生成图片
        image_url = await self.render_personal_info_image(data)
        
        if image_url:
            # 如果生成图片成功，发送图片
            yield event.image_result(image_url).use_t2i(False)
        else:
            # 否则发送纯文本
            basic = data.get("基本信息", {})
            battle_qi = data.get("斗气状态", {})
            attributes = data.get("属性", {})
            wealth = data.get("财富", {})
            cooldowns = data.get("修炼冷却", {})
            breakthrough = data.get("突破信息", {})
            friends = data.get("道友列表", [])
            battle = data.get("切磋战绩", {})
            skills = data.get("技能", [])
            items = data.get("物品", [])
            
            info_text = f"""📋 {basic.get('用户名')} 的详细信息：

📅 创建时间：{basic.get('创建时间')}

=== 斗气状态 ===
等级：{battle_qi.get('等级')}
修为：{battle_qi.get('修为')}
境界：{battle_qi.get('境界')}
经验值：{battle_qi.get('经验值')}
斗气值：{battle_qi.get('斗气值')}

=== 属性 ===
生命值：{attributes.get('生命值')}
灵力值：{attributes.get('灵力值')}
体力值：{attributes.get('体力值')}

=== 财富 ===
金币：{wealth.get('金币')}
灵石：{wealth.get('灵石')}

=== 修炼冷却 ===
打坐：{cooldowns.get('打坐')}
突破：{cooldowns.get('突破')}
调息：{cooldowns.get('调息')}
闭关：{cooldowns.get('闭关')}
切磋：{cooldowns.get('切磋')}
赠送：{cooldowns.get('赠送')}

=== 突破信息 ===
下一境界：{breakthrough.get('下一境界')}
所需斗气：{breakthrough.get('所需斗气')}
当前斗气：{breakthrough.get('当前斗气')}
突破成功率：{breakthrough.get('突破成功率')}
突破需求：{breakthrough.get('突破需求')}

=== 道友列表 ===
{chr(10).join(f"- {friend}" for friend in friends) if friends else "暂无道友"}

=== 切磋战绩 ===
胜利：{battle.get('胜利')}
失败：{battle.get('失败')}

=== 技能 ===
{chr(10).join(f"- {skill}" for skill in skills) if skills else "暂无技能"}

=== 物品 ===
{chr(10).join(f"- {item}" for item in items) if items else "暂无物品"}
"""
            yield event.plain_result(info_text)
    
    @filter.command("打坐", alias={"修炼", "冥想"})
    async def meditate(self, event):
        """基础修炼获得斗气，每次获得20斗气"""
        # 自动获取用户的QQ号作为用户名
        username = str(event.message_obj.sender.user_id)
        
        response = await self._call_api("打坐", {"username": username})
        
        if response.get("code") != 200:
            yield event.plain_result(self._format_response(response))
            return
        
        data = response.get("data", {})
        meditate_text = f"""🧘‍♀️ 打坐修炼成功！

获得斗气：20点
当前斗气：{data.get('当前斗气')}
当前境界：{data.get('境界')}
剩余体力：{data.get('剩余体力')}

⏰ 冷却时间：10分钟"""
        yield event.plain_result(meditate_text)
    
    @filter.command("突破", alias={"升级", "进阶"})
    async def breakthrough(self, event):
        """消耗斗气突破境界，有成功率"""
        # 自动获取用户的QQ号作为用户名
        username = str(event.message_obj.sender.user_id)
        
        response = await self._call_api("突破", {"username": username})
        
        if response.get("code") != 200:
            yield event.plain_result(self._format_response(response))
            return
        
        data = response.get("data", {})
        breakthrough_text = f"""🚀 突破成功！

当前境界：{data.get('当前境界')}
剩余斗气：{data.get('剩余斗气')}
当前等级：{data.get('等级')}
突破成功率：{data.get('突破成功率')}
消耗体力：{data.get('消耗体力')}
剩余体力：{data.get('剩余体力')}
"""
        yield event.plain_result(breakthrough_text)
    
    @filter.command("调息", alias={"恢复", "休息"})
    async def recover(self, event):
        """恢复生命和灵力"""
        # 自动获取用户的QQ号作为用户名
        username = str(event.message_obj.sender.user_id)
        
        response = await self._call_api("调息", {"username": username})
        yield event.plain_result(self._format_response(response))
    
    @filter.command("闭关", alias={"深度修炼"})
    async def seclusion(self, event):
        """长时间修炼获得更多斗气，每分钟1斗气"""
        # 自动获取用户的QQ号作为用户名
        username = str(event.message_obj.sender.user_id)
        
        # 解析可选的时长参数
        msg = event.message_str.replace("闭关", "").replace("深度修炼", "").strip()
        duration = None
        if msg:
            # 只取第一个参数作为时长
            duration = msg.split()[0]
        
        params = {"username": username}
        if duration:
            params["duration"] = duration
        
        response = await self._call_api("闭关", params)
        
        if response.get("code") != 200:
            yield event.plain_result(self._format_response(response))
            return
        
        data = response.get("data", {})
        seclusion_text = f"""🏯 闭关修炼成功！

闭关时长：{data.get('闭关时长')}
获得斗气：{data.get('当前斗气', 0) - (data.get('当前斗气', 0) - int(data.get('闭关时长', '0分钟').split('分钟')[0]))}
当前斗气：{data.get('当前斗气')}
当前境界：{data.get('境界')}
消耗体力：{data.get('消耗体力')}
剩余体力：{data.get('剩余体力')}

⏰ 冷却时间：2小时"""
        yield event.plain_result(seclusion_text)
    
    @filter.command("排行榜", alias={"排名", "榜单"})
    async def ranking(self, event):
        """查看斗气排行榜"""
        response = await self._call_api("排行榜", {})
        
        if response.get("code") != 200:
            yield event.plain_result(self._format_response(response))
            return
        
        data = response.get("data", {})
        ranking_list = data.get("排行榜", [])
        update_time = data.get("更新时间")
        
        if not ranking_list:
            yield event.plain_result("📊 排行榜为空！")
            return
        
        ranking_text = "📊 斗气排行榜\n\n"
        for i, player in enumerate(ranking_list, 1):
            ranking_text += f"🏆 第{i}名：{player.get('用户名')}\n"
            ranking_text += f"   境界：{player.get('境界')}\n"
            ranking_text += f"   修为值：{player.get('修为值')}\n"
            ranking_text += f"   等级：{player.get('等级')}\n\n"
        
        ranking_text += f"⏰ 更新时间：{update_time}"
        yield event.plain_result(ranking_text)
    
    @filter.command("道友", alias={"好友", "道友列表"})
    async def friends(self, event):
        """查看好友/道友"""
        # 自动获取用户的QQ号作为用户名
        username = str(event.message_obj.sender.user_id)
        
        response = await self._call_api("道友", {"username": username})
        
        if response.get("code") != 200:
            yield event.plain_result(self._format_response(response))
            return
        
        data = response.get("data", {})
        friend_list = data.get("道友列表", [])
        friend_count = data.get("道友数量", 0)
        
        friends_text = f"👥 道友列表（共{friend_count}人）\n\n"
        for friend in friend_list:
            friends_text += f"- {friend.get('用户名')}\n"
            friends_text += f"  境界：{friend.get('境界')}\n"
            friends_text += f"  等级：{friend.get('等级')}\n"
            friends_text += f"  修为值：{friend.get('修为值')}\n\n"
        
        yield event.plain_result(friends_text)
    
    @filter.command("切磋", alias={"比试", "挑战"})
    async def duel(self, event):
        """与道友切磋"""
        # 自动获取用户的QQ号作为用户名
        username = str(event.message_obj.sender.user_id)
        
        msg = event.message_str.replace("切磋", "").replace("比试", "").replace("挑战", "").strip()
        parts = msg.split()
        if len(parts) < 1:
            yield event.plain_result("❌ 请输入完整参数！格式：切磋 @456789")
            return
        
        target = parts[0]
        
        # 检查target格式
        if not target.startswith("@"):
            yield event.plain_result("❌ 切磋对象格式错误！请使用 @用户名 格式，如 @456789")
            return
        
        response = await self._call_api("切磋", {"username": username, "target": target})
        
        if response.get("code") != 200:
            yield event.plain_result(self._format_response(response))
            return
        
        data = response.get("data", {})
        duel_text = f"""⚔️ 切磋结果

{response.get('message')}

=== 切磋双方 ===
挑战者：{data.get('切磋双方', {}).get('挑战者')}
应战者：{data.get('切磋双方', {}).get('应战者')}

=== 胜负结果 ===
{data.get('胜负结果')}

=== 战斗详情 ===
你的修为：{data.get('战斗详情', {}).get('你的修为')}
对手修为：{data.get('战斗详情', {}).get('对手修为')}

战斗值：
你的战斗值：{data.get('战斗详情', {}).get('战斗值', {}).get('你的战斗值')}
对手战斗值：{data.get('战斗详情', {}).get('战斗值', {}).get('对手战斗值')}

=== 当前战绩 ===
胜利：{data.get('当前战绩', {}).get('胜利')}
失败：{data.get('当前战绩', {}).get('失败')}

⏰ 冷却时间：5分钟"""
        yield event.plain_result(duel_text)
    
    @filter.command("赠送", alias={"送礼", "给予"})
    async def give(self, event):
        """赠送物品给道友"""
        # 自动获取用户的QQ号作为用户名
        username = str(event.message_obj.sender.user_id)
        
        msg = event.message_str.replace("赠送", "").replace("送礼", "").replace("给予", "").strip()
        parts = msg.split()
        if len(parts) < 2:
            yield event.plain_result("❌ 请输入完整参数！格式：赠送 @456789 灵石x10")
            return
        
        target = parts[0]
        item = " ".join(parts[1:])
        
        # 检查target格式
        if not target.startswith("@"):
            yield event.plain_result("❌ 赠送对象格式错误！请使用 @用户名 格式，如 @456789")
            return
        
        response = await self._call_api("赠送", {"username": username, "target": target, "item": item})
        
        if response.get("code") != 200:
            yield event.plain_result(self._format_response(response))
            return
        
        data = response.get("data", {})
        give_text = f"""🎁 赠送成功！

{response.get('message')}

赠送对象：{data.get('赠送对象')}
赠送物品：{data.get('赠送物品')}
赠送数量：{data.get('赠送数量')}
你的剩余：{data.get('你的剩余')}
对方获得：{data.get('对方获得')}

⏰ 冷却时间：10分钟"""
        yield event.plain_result(give_text)
    
    async def terminate(self):
        """插件被卸载/停用时调用"""
        await self.client.aclose()
        logger.info("文字斗气机器人插件已卸载")