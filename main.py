import random
import asyncio
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api.message_components import Plain as Comp_Plain, At as Comp_At
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot import logger
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from .utils import ban, get_at_id, get_name
from .model import GameManager
from .stats import StatsManager


@register(
    "astrbot_plugin_roulette",
    "Zhalslar",
    "俄罗斯转盘赌，中枪者禁言",
    "1.1.0"
)
class RoulettePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.gm = GameManager()
        data_dir = StarTools.get_data_dir("astrbot_plugin_roulette")
        self.stats = StatsManager(data_dir)
        self.ban_duration: list[int] = [
            int(x) for x in config.get("ban_duration_str", "30-300").split("-")
        ]
        self.game_timeout: int = config.get("game_timeout", 3600)  # 游戏超时时长（秒）
        self.MAX_BAN_DURATION: int = 86400  # 24小时
        self.PERSUASION_QUOTES: list = [
            "赌博一时爽，一直赌博一直爽，但最后爽的只有赌场老板！",
            "别再赌了，回头是岸！",
            "赌博是无底洞，早回头早安心。",
            "赌一时，悔一世！",
            "别让赌博毁了你的未来！",
            "赌博是毒药，沾染不得！",
            "别再赌了，你的家人需要你！",
            "别让赌博成为你人生的绊脚石！",
            "小赌怡情，大赌伤身，强赌灰飞烟灭",
            "赌狗赌到最后一无所有，你确定要继续吗？",
            "十赌九输，清醒点",
            "'赌'字上'贝'下'者'，'贝者'即背着债务的人",
            "常在河边走，哪有不湿鞋?",
            "赌博之害，你岂能不知",
            "一次戒赌，终生受益",
            "手握一手好牌，切莫做那糊涂的赌徒",
            "听我一言，捷径虽诱人，赌路却凶险，慎行",
            "放手一搏,不如稳健前行",
        ]
        # 用于存储超时任务，键为 group_id，值为 asyncio.Task 对象
        self.timeout_tasks: dict[str, asyncio.Task] = {}
        # 用于存储游戏超时任务
        self.game_timeout_tasks: dict[str, asyncio.Task] = {}
    
    def _set_game_timeout(self, event: AstrMessageEvent, group_id: str, room):
        """设置游戏超时任务"""
        if self.game_timeout <= 0:
            return
        
        # 取消已有的超时任务
        if group_id in self.game_timeout_tasks:
            self.game_timeout_tasks[group_id].cancel()
        
        async def game_timeout_coro():
            try:
                await asyncio.sleep(self.game_timeout)
                logger.info(f"群 {group_id} 的游戏超时，自动结束")
                
                # 清理房间
                if room.players:
                    self.gm.del_room(group_id=group_id, players=room.players)
                else:
                    self.gm.del_room(group_id=group_id)
                
                # 发送超时提示
                timeout_msg = f"⏱️ 转盘游戏超时（{self.game_timeout}秒无人开枪），已自动结束，无人受罚。"
                await event.yield_result(event.plain(timeout_msg))
                
                if group_id in self.game_timeout_tasks:
                    del self.game_timeout_tasks[group_id]
            except asyncio.CancelledError:
                logger.info(f"群 {group_id} 的游戏超时任务被取消")
        
        self.game_timeout_tasks[group_id] = asyncio.create_task(game_timeout_coro())
    
    @filter.command("转盘", alias={"轮盘", "开启转盘"})
    async def start_wheel(self, event: AstrMessageEvent):
        """转盘@某人 [秒数] 不@表示进入多人模式"""
        args = event.message_str.split()
        
        target_id = get_at_id(event)
        sender_id = event.get_sender_id()
        group_id = event.get_group_id()
        
        # 解析禁言时长参数
        duration = None
        custom_duration = False  # 标记是否为自定义时长
        if len(args) >= 2 and args[-1].isdigit():
            # 多人模式不允许自定义时长
            if not target_id:
                # 使用随机时长
                duration = random.randint(*self.ban_duration)
                custom_duration = False
            else:
                # 双人模式允许自定义时长
                duration = int(args[-1])
                custom_duration = True
                if duration > self.MAX_BAN_DURATION:
                    duration = self.MAX_BAN_DURATION
                    yield event.plain_result(f"⚠️ 禁言时长不能超过24小时，已设置为最大值 {self.MAX_BAN_DURATION} 秒")
        
        if duration is None:
            # 使用随机时长
            duration = random.randint(*self.ban_duration)

        if sender_id == target_id:
            yield event.plain_result("不能和自己玩哦！")
            return

        kids = [sender_id, target_id, group_id]
        room = self.gm.create_room(kids=kids, ban_time=duration)
        if not room:
            reply = ""
            if self.gm.has_room(sender_id, group_id): reply = "你在游戏中..."
            if target_id and self.gm.has_room(target_id, group_id): reply = "对方游戏中..."
            # 双人转盘和多人转盘可以并存，不检查群游戏
            if not target_id and self.gm.get_room(["", "", group_id]): 
                reply = "本群游戏中..."
            yield event.plain_result(reply)
            return

        if room.players:
            user_name = await get_name(event, sender_id)
            target_name = await get_name(event, target_id) if target_id else ""
            # 使用chain格式，@发起者并说明规则
            chain = []
            if custom_duration:
                text = f"🎲 {user_name} VS {target_name}\n双人转盘对决开始！惩罚时长：{duration}秒\n发起者先手，"
            else:
                text = f"🎲 {user_name} VS {target_name}\n双人转盘对决开始！\n发起者先手，"
            chain.append(Comp_Plain(text))
            chain.append(Comp_At(qq=sender_id))
            chain.append(Comp_Plain(" 请先开枪！"))
            yield event.chain_result(chain)
        else:
            if custom_duration:
                yield event.plain_result(f"本群转盘开始，惩罚时长：{duration}秒，请开枪！")
            else:
                yield event.plain_result("本群转盘开始，请开枪！")
        
        # 设置游戏超时
        self._set_game_timeout(event, group_id, room)
        
        logger.info(
            f"转盘游戏创建成功：子弹在第{room.bullet}轮，禁言时长为{room.ban_time}秒"
        )
        return

    @filter.command("开枪")
    async def shoot_wheel(self, event: AstrMessageEvent):
        sender_id = event.get_sender_id()
        group_id = event.get_group_id()
        
        # 优先查找双人转盘（通过sender_id）
        room = self.gm.get_room(kids=[sender_id, "", ""])
        
        # 如果没有双人转盘，查找多人转盘（通过group_id）
        if not room:
            room = self.gm.get_room(kids=["", "", group_id])

        if not room:
            yield event.plain_result("请先开启转盘")
            return
        
        if not room.can_shoot(sender_id):
            # 多人模式下已参与过
            if not room.players and sender_id in room.participated:
                yield event.plain_result("你已经参与过本局游戏了！")
            else:
                yield event.plain_result("本轮不是你的回合")
            return

        # 取消最后一发超时任务
        if group_id in self.timeout_tasks:
            self.timeout_tasks[group_id].cancel()
            del self.timeout_tasks[group_id]
        
        # 取消游戏超时任务
        if group_id in self.game_timeout_tasks:
            self.game_timeout_tasks[group_id].cancel()
            del self.game_timeout_tasks[group_id]

        user_name = await get_name(event, sender_id)

        if room.shoot(sender_id):
            # 记录战绩
            all_participants = room.get_all_participants()
            winner_ids = [p for p in all_participants if p != sender_id]
            is_pvp = len(room.players) == 2
            
            # 多人模式只记录败者，不记录胜者
            if not is_pvp:
                winner_ids = []
                
            self.stats.record_game_result(sender_id, winner_ids, is_pvp, group_id)
            
            await ban(event, room.ban_time)
            reply = f"Bang！{user_name}被禁言{room.ban_time}秒！{random.choice(self.PERSUASION_QUOTES)}"
            yield event.plain_result(reply)
            # 使用包含所有参与者的列表来清理房间
            self.gm.del_room(group_id=group_id, players=room.players)
        else:
            # 没中枪
            reply = f"【{user_name}】开了一枪没响，还剩【{6 - room.round}】发"
            next_player_id = room.players[room.next_idx] if room.next_idx is not None else None
            
            if next_player_id:
                # 双人模式，@下一个玩家
                is_last_round = (6 - room.round) == 1
                if is_last_round:
                    # 最后一发，@玩家并给出警告
                    chain = []
                    chain.append(Comp_Plain(reply + "，"))
                    chain.append(Comp_At(qq=next_player_id))
                    chain.append(Comp_Plain(" ⚠️ 你只剩下最后一发子弹，命运掌握在自己手中！\n请在3分钟内【开枪】或【认输】，否则将自动判负。"))
                    yield event.chain_result(chain)
                else:
                    # 普通回合，@下一个玩家
                    chain = []
                    chain.append(Comp_Plain(reply + "，"))
                    chain.append(Comp_At(qq=next_player_id))
                    chain.append(Comp_Plain(" 该你了！"))
                    yield event.chain_result(chain)
                
                if is_last_round:
                    async def auto_surrender_coro():
                        try:
                            await asyncio.sleep(180) # 等待3分钟
                            logger.info(f"玩家 {player_name}({next_player_id}) 在群 {group_id} 的游戏超时。")
                            
                            # 记录战绩
                            all_participants = room.get_all_participants()
                            winner_ids = [p for p in all_participants if p != next_player_id]
                            is_pvp = len(room.players) == 2
                            
                            # 多人模式只记录败者，不记录胜者
                            if not is_pvp:
                                winner_ids = []
                                
                            self.stats.record_game_result(next_player_id, winner_ids, is_pvp, group_id)
                            
                            timeout_event = event.fork(user_id=next_player_id)
                            await ban(timeout_event, room.ban_time)
                            timeout_reply = (
                                f"玩家 {player_name} 在命运抉择面前犹豫了超过3分钟，已自动判负！\n"
                                f"被禁言 {room.ban_time} 秒！{random.choice(self.PERSUASION_QUOTES)}"
                            )
                            await event.yield_result(event.plain(timeout_reply))
                            # 使用包含所有参与者的列表来清理房间
                            self.gm.del_room(group_id=group_id, players=room.players)
                            if group_id in self.timeout_tasks:
                                del self.timeout_tasks[group_id]
                        except asyncio.CancelledError:
                            logger.info(f"群 {group_id} 的超时任务被取消。")
                    
                    self.timeout_tasks[group_id] = asyncio.create_task(auto_surrender_coro())
            else:
                # 多人模式，没有指定下一个玩家
                yield event.plain_result(reply)
            
            # 重新设置游戏超时（没中枪，游戏继续）
            self._set_game_timeout(event, group_id, room)
    
    @filter.command("认输", alias={"玩不起"})
    async def surrender_game(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        
        # 优先查找双人转盘
        room = self.gm.get_room(kids=[user_id, "", ""])
        
        # 如果没有双人转盘，查找多人转盘
        if not room:
            room = self.gm.get_room(kids=["", "", group_id])

        if not room:
            yield event.plain_result("你没有正在进行的转盘游戏")
            return

        if not room.can_shoot(user_id):
            yield event.plain_result("还没轮到你，不能认输哦！")
            return

        if group_id in self.timeout_tasks:
            self.timeout_tasks[group_id].cancel()
            del self.timeout_tasks[group_id]
        
        if group_id in self.game_timeout_tasks:
            self.game_timeout_tasks[group_id].cancel()
            del self.game_timeout_tasks[group_id]
        
        user_name = await get_name(event, user_id)
        
        # 记录战绩
        all_participants = room.get_all_participants()
        winner_ids = [p for p in all_participants if p != user_id]
        is_pvp = len(room.players) == 2
        
        # 多人模式只记录败者，不记录胜者
        if not is_pvp:
            winner_ids = []
            
        self.stats.record_game_result(user_id, winner_ids, is_pvp, group_id)
        
        await ban(event, room.ban_time)
        reply = (
            f"{user_name} 选择了认输，直面惩罚！"
            f"被禁言 {room.ban_time} 秒！{random.choice(self.PERSUASION_QUOTES)}"
        )
        # 使用包含所有参与者的列表来清理房间
        self.gm.del_room(group_id=group_id, players=room.players)
        yield event.plain_result(reply)

    @filter.command("退出", alias={"结束游戏"})
    async def exit_game(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        
        # 优先查找双人转盘
        room = self.gm.get_room(kids=[user_id, "", ""])
        
        # 如果没有双人转盘，查找多人转盘
        if not room:
            room = self.gm.get_room(kids=["", "", group_id])

        if not room:
            yield event.plain_result("你没有正在进行的转盘游戏")
            return

        is_last_round = (6 - room.round) == 1
        if is_last_round and room.can_shoot(user_id):
            yield event.plain_result("只剩最后一发，命运已定，无法退出！请选择【开枪】或【认输】。")
            return

        if group_id in self.timeout_tasks:
            self.timeout_tasks[group_id].cancel()
            del self.timeout_tasks[group_id]
        
        if group_id in self.game_timeout_tasks:
            self.game_timeout_tasks[group_id].cancel()
            del self.game_timeout_tasks[group_id]

        # 使用包含所有参与者的列表来清理房间
        self.gm.del_room(group_id=group_id, players=room.players)
        yield event.plain_result("游戏已由玩家主动退出，无人受罚。")
    
    @filter.command("结束转盘")
    async def admin_end_game(self, event: AstrMessageEvent):
        """管理员强制结束当前群的多人转盘游戏（不影响双人对决）"""
        if not event.is_admin():
            yield event.plain_result("此指令仅限管理员使用")
            return
        
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("请在群聊中使用此指令")
            return
        
        room = self.gm.get_room(kids=["", "", group_id])
        if not room:
            yield event.plain_result("当前群没有进行中的转盘游戏")
            return
        
        # 检查是否为双人模式
        if room.players:
            yield event.plain_result("当前是双人对决模式，无法强制结束。请让玩家自行【退出】或【认输】。")
            return
        
        if group_id in self.timeout_tasks:
            self.timeout_tasks[group_id].cancel()
            del self.timeout_tasks[group_id]
        
        if group_id in self.game_timeout_tasks:
            self.game_timeout_tasks[group_id].cancel()
            del self.game_timeout_tasks[group_id]
        
        # 清理多人模式房间
        self.gm.del_room(group_id=group_id)
        yield event.plain_result("管理员已强制结束当前群的多人转盘游戏，无人受罚。")
    
    @filter.command("我的战绩", alias={"转盘战绩", "查看战绩"})
    async def my_stats(self, event: AstrMessageEvent):
        """查看个人转盘战绩"""
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        stats = self.stats.get_user_stats(user_id, group_id)
        
        if not stats:
            yield event.plain_result("你还没有参与过转盘游戏哦！")
            return
        
        user_name = await get_name(event, user_id)
        total = stats["total"]
        wins = stats["wins"]
        losses = stats["losses"]
        win_rate = (wins / total * 100) if total > 0 else 0
        max_streak = stats["max_win_streak"]
        current_streak = stats["current_streak"]
        
        reply = f"🎰 {user_name} 的转盘战绩\n\n"
        reply += f"参与局数: {total}\n"
        reply += f"获胜次数: {wins} (未中枪)\n"
        reply += f"失败次数: {losses} (中枪)\n"
        reply += f"胜率: {win_rate:.1f}%\n"
        reply += f"最高连胜: {max_streak} 连胜\n"
        reply += f"当前连胜: {current_streak} 连胜" if current_streak > 0 else f"当前连胜: 0"
        
        yield event.plain_result(reply)
    
    @filter.command("对战记录")
    async def pvp_stats(self, event: AstrMessageEvent):
        """查看与某人的对战记录，需要@对方"""
        sender_id = event.get_sender_id()
        target_id = get_at_id(event)
        
        if not target_id:
            yield event.plain_result("请@你想查看对战记录的人")
            return
        
        if sender_id == target_id:
            yield event.plain_result("不能查看与自己的对战记录哦！")
            return
        
        group_id = event.get_group_id()
        pvp_stats = self.stats.get_pvp_stats(sender_id, target_id, group_id)
        
        if not pvp_stats:
            sender_name = await get_name(event, sender_id)
            target_name = await get_name(event, target_id)
            yield event.plain_result(f"{sender_name} 和 {target_name} 还没有对战记录")
            return
        
        sender_name = await get_name(event, sender_id)
        target_name = await get_name(event, target_id)
        
        total = pvp_stats["total"]
        sender_wins = pvp_stats.get(f"{sender_id}_wins", 0)
        target_wins = pvp_stats.get(f"{target_id}_wins", 0)
        
        reply = f"⚔️ 对战记录\n\n"
        reply += f"{sender_name} VS {target_name}\n\n"
        reply += f"总对战: {total} 局\n"
        reply += f"{sender_name} 获胜: {sender_wins} 局\n"
        reply += f"{target_name} 获胜: {target_wins} 局\n"
        
        if sender_wins > target_wins:
            reply += f"\n{sender_name} 暂时领先！"
        elif target_wins > sender_wins:
            reply += f"\n{target_name} 暂时领先！"
        else:
            reply += f"\n双方势均力敌！"
        
        yield event.plain_result(reply)
    
    @filter.command("赌圣榜", alias={"赌圣排行榜", "胜率排行"})
    async def top_players(self, event: AstrMessageEvent):
        """查看胜率排行榜（至少参与5局）"""
        group_id = event.get_group_id()
        top_list = self.stats.get_top_players(group_id=group_id, min_games=5, limit=5)
        
        if not top_list:
            yield event.plain_result("暂时还没有符合条件的赌圣（至少参与5局）")
            return
        
        reply = "🏆 赌圣排行榜 TOP5\n"
        reply += "（至少参与5局）\n\n"
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        
        for idx, (user_id, win_rate, stats) in enumerate(top_list):
            user_name = await get_name(event, user_id)
            total = stats["total"]
            wins = stats["wins"]
            max_streak = stats["max_win_streak"]
            
            reply += f"{medals[idx]} {user_name}\n"
            reply += f"   胜率: {win_rate*100:.1f}% ({wins}/{total})\n"
            reply += f"   最高连胜: {max_streak}\n\n"
        
        yield event.plain_result(reply)
    
    @filter.command("转盘帮助", alias={"轮盘帮助"})
    async def roulette_help(self, event: AstrMessageEvent):
        """显示转盘游戏帮助"""
        help_text = """🎰 俄罗斯转盘游戏帮助

📌 基础玩法
• /转盘@群友 [秒数] - 双人对决，发起者先手
• /转盘 [秒数] - 多人模式，每人只能开一枪
• /开枪 - 向自己开一枪
• /认输 或 /玩不起 - 主动认输接受惩罚
• /退出 或 /结束游戏 - 退出当前游戏

📊 战绩查询
• /我的战绩 - 查看个人战绩统计
• /对战记录@群友 - 查看与某人的对战记录
• /赌圣榜 - 查看胜率排行榜TOP5

🛡️ 管理员指令
• /结束转盘 - 强制结束多人游戏（不影响双人对决）

💡 游戏规则
• 转盘有6发子弹位，随机一发是实弹
• 双人模式发起者先手，轮流开枪
• 多人模式每人限开一枪
• 可在@后加秒数自定义禁言时长（最高24小时）
• 中枪者会被禁言，时长可自定义或随机
• 胜利者不受惩罚，战绩会被记录
• 最后一发时必须开枪或认输，不能退出
• 游戏超时无人开枪将自动结束

📈 战绩说明
• 胜利：未中枪即为胜利
• 失败：中枪、认输、超时均为失败
• 胜率：胜利次数/总参与次数
• 赌圣榜：至少参与5局才能上榜

⚠️ 小赌怡情，大赌伤身！"""
        
        yield event.plain_result(help_text)
