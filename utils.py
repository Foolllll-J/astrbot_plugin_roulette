
from astrbot.core.message.components import At
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

async def get_name(event: AstrMessageEvent, user_id: str|int, group_id: str|int = None) -> str:
    """
    获取指定群友的昵称
    :param event: 消息事件
    :param user_id: 用户ID
    :param group_id: 指定群组ID，如果不传则从 event 获取
    :return: 昵称，如果用户不在群内且无法获取陌生人信息则返回 None
    """
    if event.get_platform_name() == "aiocqhttp" and str(user_id).isdigit():
        assert isinstance(event, AiocqhttpMessageEvent)
        gid = group_id or event.get_group_id()
        try:
            if gid:
                member_info = await event.bot.get_group_member_info(
                    group_id=int(gid), user_id=int(user_id)
                )
                nickname = member_info.get("card") or member_info.get("nickname")
                return (nickname or str(user_id)).strip() or str(user_id)
            else:
                stranger_info = await event.bot.get_stranger_info(user_id=int(user_id))
                return (stranger_info.get("nickname") or str(user_id)).strip()
        except Exception as e:
            # 如果是群成员不存在 (retcode 1200)，在要求严格检查群成员时返回 None
            if "1200" in str(e) or "不存在" in str(e):
                return None
            
            # 其他异常尝试获取陌生人信息
            try:
                stranger_info = await event.bot.get_stranger_info(user_id=int(user_id))
                return (stranger_info.get("nickname") or str(user_id)).strip()
            except Exception:
                return str(user_id)
    else:
        return str(user_id)

def get_at_id(event: AstrMessageEvent) -> str:
    """获取@的 QQ 号"""
    return next(
        (
            str(seg.qq)
            for seg in event.get_messages()
            if (isinstance(seg, At)) and str(seg.qq) != event.get_self_id()
        ),
        "",
    )


async def ban(event: AstrMessageEvent, duration: int):
    if event.get_platform_name() == "aiocqhttp":
        assert isinstance(event, AiocqhttpMessageEvent)
        try:
            await event.bot.set_group_ban(
                group_id=int(event.get_group_id()),
                user_id=int(event.get_sender_id()),
                duration=duration,
            )
        except Exception:
            pass
