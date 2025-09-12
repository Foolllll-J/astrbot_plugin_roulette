import random
import asyncio  # 导入 asyncio 库
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot import logger
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from .utils import ban, get_at_id, get_name
from .model import GameManager


@register(
    "astrbot_plugin_roulette",
    "Zhalslar",
    "俄罗斯转盘赌，中枪者禁言",
    "1.0.2"  # 版本号更新
)
class RoulettePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.gm = GameManager()
        self.ban_duration: list[int] = [
            int(x) for x in config.get("ban_duration_str", "30-300").split("-")
        ]
        self.PERSUASION_QUOTES: list = [
            # ... (语录列表保持不变)
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
    
    # start_wheel 函數保持不變...
    @filter.command("转盘", alias={"轮盘", "开启转盘"})
    async def start_wheel(self, event: AstrMessageEvent):
        """转盘@某人 不@表示进入多人模式"""
        args = event.message_str.split()
        duration = (
            int(args[-1]) if args[-1].isdigit() else random.randint(*self.ban_duration)
        )

        target_id = get_at_id(event)
        sender_id = event.get_sender_id()
        group_id = event.get_group_id()

        if sender_id == target_id:
            yield event.plain_result("不能和自己玩哦！")
            return

        kids = [sender_id, target_id, group_id]
        room = self.gm.create_room(kids=kids, ban_time=duration)
        if not room:
            reply = ""
            if self.gm.has_room(sender_id):
                reply = "你在游戏中..."
            if self.gm.has_room(target_id):
                reply = "对方游戏中..."
            if self.gm.has_room(group_id):
                reply = "本群游戏中..."
            yield event.plain_result(reply)
            return

        # 开盘提示
        if room.players:
            user_name = await get_name(event, sender_id)
            target_name = await get_name(event, target_id) if target_id else ""
            yield event.plain_result(f"{user_name} VS {target_name}, 请开枪")
        else:
            yield event.plain_result("本群转盘开始，请开枪！")
        logger.info(
            f"转盘游戏创建成功：子弹在第{room.bullet}轮，禁言时长为{room.ban_time}秒"
        )
        return

    # --- shoot_wheel 函數重大修改 ---
    @filter.command("开枪")
    async def shoot_wheel(self, event: AstrMessageEvent):
        sender_id = event.get_sender_id()
        group_id = event.get_group_id()
        kids = [sender_id, "", group_id]

        room = self.gm.get_room(kids)
        if not room:
            yield event.plain_result("请先开启转盘")
            return
        
        if not room.can_shoot(sender_id):
            yield event.plain_result("本轮不是你的回合")
            return

        # --- 核心修改：玩家行动时，取消可能存在的超时任务 ---
        if group_id in self.timeout_tasks:
            self.timeout_tasks[group_id].cancel()
            del self.timeout_tasks[group_id]

        user_name = await get_name(event, sender_id)

        if room.shoot(sender_id):
            await ban(event, room.ban_time)
            reply = f"Bang！{user_name}被禁言{room.ban_time}秒！{random.choice(self.PERSUASION_QUOTES)}"
            self.gm.del_room(kids)
        else:
            reply = f"【{user_name}】开了一枪没响，还剩【{6 - room.round}】发"
            next_player_id = room.players[room.next_idx] if room.next_idx is not None else None

            if next_player_id:
                player_name = await get_name(event, user_id=next_player_id)
                reply += f", {player_name}，该你了！"

                # --- 核心修改：检查是否触发了超时条件 ---
                is_last_round = (6 - room.round) == 1
                if is_last_round:
                    reply += "\n\n⚠️ 你只剩下最后一发子弹，命运掌握在自己手中！\n请在3分钟内【开枪】或【认输】，否则将自动判负。"
                    
                    # 定义一个协程，用于执行超时逻辑
                    async def auto_surrender_coro():
                        try:
                            await asyncio.sleep(180) # 等待3分钟
                            logger.info(f"玩家 {player_name}({next_player_id}) 在群 {group_id} 的游戏超时。")
                            # 超时后执行的逻辑
                            timeout_event = event.fork(user_id=next_player_id)
                            await ban(timeout_event, room.ban_time)
                            timeout_reply = (
                                f"玩家 {player_name} 在命运抉择面前犹豫了超过3分钟，已自动判负！\n"
                                f"被禁言 {room.ban_time} 秒！{random.choice(self.PERSUASION_QUOTES)}"
                            )
                            # 使用 event.yield_result 而不是 yield event.plain_result
                            await event.yield_result(event.plain(timeout_reply))
                            self.gm.del_room(kids=[next_player_id, "", group_id])
                            if group_id in self.timeout_tasks:
                                del self.timeout_tasks[group_id]
                        except asyncio.CancelledError:
                            logger.info(f"群 {group_id} 的超时任务被取消。")
                    
                    # 创建并存储这个超时任务
                    self.timeout_tasks[group_id] = asyncio.create_task(auto_surrender_coro())

        yield event.plain_result(reply)
    
    # --- surrender_game 和 exit_game 函數需要添加任务取消逻辑 ---
    @filter.command("认输", alias={"玩不起"})
    async def surrender_game(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        kids = [user_id, "", group_id]
        room = self.gm.get_room(kids)

        if not room:
            yield event.plain_result("你没有正在进行的转盘游戏")
            return

        if not room.can_shoot(user_id):
            yield event.plain_result("还没轮到你，不能认输哦！")
            return

        # --- 核心修改：玩家行动时，取消可能存在的超时任务 ---
        if group_id in self.timeout_tasks:
            self.timeout_tasks[group_id].cancel()
            del self.timeout_tasks[group_id]
        
        user_name = await get_name(event, user_id)
        await ban(event, room.ban_time)
        reply = (
            f"{user_name} 选择了认输，直面惩罚！"
            f"被禁言 {room.ban_time} 秒！{random.choice(self.PERSUASION_QUOTES)}"
        )
        self.gm.del_room(kids)
        yield event.plain_result(reply)

    @filter.command("退出", alias={"结束游戏"})
    async def exit_game(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        kids = [user_id, "", group_id]
        room = self.gm.get_room(kids)

        if not room:
            yield event.plain_result("你没有正在进行的转盘游戏")
            return

        is_last_round = (6 - room.round) == 1
        if is_last_round and room.can_shoot(user_id):
            yield event.plain_result("只剩最后一发，命运已定，无法退出！请选择【开枪】或【认输】。")
            return

        # --- 核心修改：游戏结束时，取消可能存在的超时任务 ---
        if group_id in self.timeout_tasks:
            self.timeout_tasks[group_id].cancel()
            del self.timeout_tasks[group_id]

        self.gm.del_room(kids)
        yield event.plain_result("游戏已由玩家主动退出，无人受罚。")
