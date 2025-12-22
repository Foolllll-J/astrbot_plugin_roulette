import random
import threading
from typing import Dict, List, Optional


class Room:
    """内部房间类，不对外暴露 room_id"""

    def __init__(self, players: List[str], ban_time:int):
        self.players = players
        self.ban_time = ban_time
        self.bullet = random.randint(1, 6)
        self.round = 0
        # 双人模式：发起者（players[0]）先手
        self.next_idx: Optional[int] = 0 if players else None
        self.participated: set = set()  # 记录多人模式下已参与的玩家

    @property
    def over(self) -> bool:
        return self.round >= self.bullet


    def can_shoot(self, shooter: str):
        if self.players and isinstance(self.next_idx, int):
            return shooter == self.players[self.next_idx]
        # 多人模式：检查是否已经参与过
        if not self.players:
            return shooter not in self.participated
        return True

    def shoot(self, shooter: str) -> bool:
        if self.over:
            return False

        # 多人模式
        if not self.players:
            # 检查是否已参与
            if shooter in self.participated:
                return False
            self.participated.add(shooter)
            self.round += 1
            return self.round == self.bullet

        # 双人模式：固定玩家列表
        if shooter not in self.players:
            return False

        # 判断本轮枪手
        if not self.can_shoot(shooter):
            return False

        self.round += 1
        # 切换枪手
        self.next_idx = 1 - self.next_idx

        return self.round == self.bullet
    
    def get_all_participants(self) -> List[str]:
        """获取所有参与者（包括固定玩家和多人模式下的参与者）"""
        if self.players:
            return self.players
        return list(self.participated)


class GameManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.room: Dict[str, Room] = {}  # player_id -> room 实例


    def create_room(
        self, kids: list[str], ban_time: int = 0
    ) -> Room | None:
        """创建房间"""
        sender_id, target_id, group_id = kids[0], kids[1], kids[2]
        with self._lock:
            # 双人模式：检查双方是否在游戏中
            if sender_id and target_id:
                k1 = f"{group_id}:{sender_id}"
                k2 = f"{group_id}:{target_id}"
                if k1 in self.room or k2 in self.room:
                    return None
                room = Room(players=[sender_id, target_id], ban_time=ban_time)
                self.room[k1] = room
                self.room[k2] = room
                return room
            # 多人模式：只检查群是否已有多人游戏
            elif group_id:
                k_group = f"{group_id}:group"
                if k_group in self.room:
                    return None
                room = Room(players=[], ban_time=ban_time)
                self.room[k_group] = room
                return room


    def get_room(self, kids: list[str]) -> Room | None:
        """获取房间"""
        sender_id, target_id, group_id = kids[0], kids[1], kids[2]
        with self._lock:
            if sender_id:
                if room := self.room.get(f"{group_id}:{sender_id}"): return room
            if target_id:
                if room := self.room.get(f"{group_id}:{target_id}"): return room
            if group_id:
                if room := self.room.get(f"{group_id}:group"): return room
            return None


    def has_room(self, kid: str, group_id: str) -> bool:
        """玩家是否已在房间"""
        with self._lock:
            return f"{group_id}:{kid}" in self.room

    def del_room(self, group_id: str, players: list[str] = None):
        """即销毁房间"""
        with self._lock:
            if players:
                for p in players:
                    k = f"{group_id}:{p}"
                    if k in self.room:
                        self.room.pop(k)
            
            k_group = f"{group_id}:group"
            if k_group in self.room:
                self.room.pop(k_group)






