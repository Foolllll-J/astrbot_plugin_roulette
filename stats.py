import json
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import threading


class StatsManager:
    """战绩管理器"""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.data_file = os.path.join(data_dir, "roulette_stats.json")
        self._lock = threading.Lock()
        self.stats: Dict = {
            "users": {},  # user_id -> {total, wins, losses, win_streak, max_win_streak, current_streak}
            "pvp": {},    # f"{user1_id}_{user2_id}" -> {total, user1_wins, user2_wins}
            "groups": {}, # group_id -> {users: {}, pvp: {}}
        }
        self._load_data()
    
    def _load_data(self):
        """加载数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
                # 兼容旧数据
                if "users" not in self.stats:
                    self.stats["users"] = {}
                if "pvp" not in self.stats:
                    self.stats["pvp"] = {}
                if "groups" not in self.stats:
                    self.stats["groups"] = {}
            except Exception as e:
                print(f"[Roulette] 加载战绩数据失败: {e}")
    
    def _save_data(self):
        """保存数据"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Roulette] 保存战绩数据失败: {e}")
    
    def record_game_result(self, loser_id: str, winner_ids: List[str], is_pvp: bool = False, group_id: str = None):
        """
        记录游戏结果
        :param loser_id: 失败者ID
        :param winner_ids: 胜利者ID列表
        :param is_pvp: 是否为双人对战
        :param group_id: 群组ID
        """
        with self._lock:
            targets = [self.stats]
            if group_id:
                if group_id not in self.stats["groups"]:
                    self.stats["groups"][group_id] = {"users": {}, "pvp": {}}
                targets.append(self.stats["groups"][group_id])

            for target in targets:
                # 记录失败者
                if loser_id not in target["users"]:
                    target["users"][loser_id] = {
                        "total": 0,
                        "wins": 0,
                        "losses": 0,
                        "win_streak": 0,
                        "max_win_streak": 0,
                        "current_streak": 0
                    }
                
                user_stats = target["users"][loser_id]
                user_stats["total"] += 1
                user_stats["losses"] += 1
                user_stats["current_streak"] = 0  # 输了重置连胜
                
                # 记录胜利者
                for winner_id in winner_ids:
                    if winner_id not in target["users"]:
                        target["users"][winner_id] = {
                            "total": 0,
                            "wins": 0,
                            "losses": 0,
                            "win_streak": 0,
                            "max_win_streak": 0,
                            "current_streak": 0
                        }
                    
                    winner_stats = target["users"][winner_id]
                    winner_stats["total"] += 1
                    winner_stats["wins"] += 1
                    winner_stats["current_streak"] += 1
                    
                    # 更新最高连胜
                    if winner_stats["current_streak"] > winner_stats["max_win_streak"]:
                        winner_stats["max_win_streak"] = winner_stats["current_streak"]
                
                # 如果是双人对战，记录PVP战绩
                if is_pvp and len(winner_ids) == 1:
                    winner_id = winner_ids[0]
                    # 确保顺序一致，小ID在前
                    user1_id, user2_id = sorted([loser_id, winner_id])
                    pvp_key = f"{user1_id}_{user2_id}"
                    
                    if pvp_key not in target["pvp"]:
                        target["pvp"][pvp_key] = {
                            "total": 0,
                            f"{user1_id}_wins": 0,
                            f"{user2_id}_wins": 0
                        }
                    
                    pvp_stats = target["pvp"][pvp_key]
                    pvp_stats["total"] += 1
                    pvp_stats[f"{winner_id}_wins"] += 1
            
            self._save_data()
    
    def get_user_stats(self, user_id: str, group_id: str = None) -> Optional[Dict]:
        """获取用户战绩"""
        with self._lock:
            if group_id and group_id in self.stats["groups"]:
                return self.stats["groups"][group_id]["users"].get(user_id)
            return self.stats["users"].get(user_id)
    
    def get_pvp_stats(self, user1_id: str, user2_id: str, group_id: str = None) -> Optional[Dict]:
        """获取两个用户之间的对战记录"""
        with self._lock:
            user1_id, user2_id = sorted([user1_id, user2_id])
            pvp_key = f"{user1_id}_{user2_id}"

            pvp_stats = None
            if group_id and group_id in self.stats["groups"]:
                pvp_stats = self.stats["groups"][group_id]["pvp"].get(pvp_key)

            if not pvp_stats and not group_id:
                pvp_stats = self.stats["pvp"].get(pvp_key)

            if not pvp_stats:
                return None

            user1_wins = pvp_stats.get(f"{user1_id}_wins", 0)
            user2_wins = pvp_stats.get(f"{user2_id}_wins", 0)
            total = pvp_stats["total"]

            # 计算胜率
            user1_win_rate = (user1_wins / total * 100) if total > 0 else 0
            user2_win_rate = (user2_wins / total * 100) if total > 0 else 0

            # 重新排列，让查询者的信息在前
            return {
                "total": total,
                f"{user1_id}_wins": user1_wins,
                f"{user2_id}_wins": user2_wins,
                f"{user1_id}_win_rate": user1_win_rate,
                f"{user2_id}_win_rate": user2_win_rate
            }
    
    def get_top_players(self, group_id: str = None, min_games: int = 5, limit: int = 5) -> List[Tuple[str, float, Dict]]:
        """
        获取胜率排行榜
        :param group_id: 群组ID
        :param min_games: 最少参与局数
        :param limit: 返回前N名
        :return: [(user_id, win_rate, stats), ...]
        """
        with self._lock:
            qualified_users = []
            
            source = self.stats["users"]
            if group_id and group_id in self.stats["groups"]:
                source = self.stats["groups"][group_id]["users"]
            
            for user_id, stats in source.items():
                if stats["total"] >= min_games:
                    win_rate = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
                    qualified_users.append((user_id, win_rate, stats))
            
            # 按胜率降序排序
            qualified_users.sort(key=lambda x: x[1], reverse=True)
            
            return qualified_users[:limit]
