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
        with self._lock:
            for kid in kids:
                if kid in self.room:
                    return None
            if kids[0] and kids[1]:  # 固定列表
                room = Room(players=kids[:2], ban_time=ban_time)
                self.room[kids[0]] = room
                self.room[kids[1]] = room
                return room
            elif kids[2]:
                # 多人模式
                room = Room(players=[], ban_time=ban_time)
                self.room[kids[2]] = room
                return room


    def get_room(self, kids: list[str]) -> Room | None:
        """获取房间"""
        with self._lock:
            for kid in kids:
                if room := self.room.get(kid):
                    return room
            return None


    def has_room(self, kid: str) -> bool:
        """玩家是否已在房间"""
        with self._lock:
            return kid in self.room

    def del_room(self, kids: list[str]):
        """即销毁房间"""
        with self._lock:
            for kid in kids:
                if kid in self.room:
                    self.room.pop(kid)






