<div align="center">

![:name](https://count.getloli.com/@astrbot_plugin_roulette?name=astrbot_plugin_roulette&theme=minecraft&padding=6&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)

# astrbot_plugin_roulette

_✨ [astrbot](https://github.com/AstrBotDevs/AstrBot) 俄罗斯转盘赌 ✨_

[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![AstrBot](https://img.shields.io/badge/AstrBot-3.4%2B-orange.svg)](https://github.com/Soulter/AstrBot)
[![GitHub](https://img.shields.io/badge/作者-Zhalslar-blue)](https://github.com/Zhalslar)

</div>

## 🤝 介绍

本插件模拟了俄罗斯转盘赌的玩法，中枪者会被禁言，支持双人对决和多人模式，带有完整的战绩记录系统。

## 📦 安装

- 可以直接在astrbot的插件市场搜索astrbot_plugin_roulette，点击安装，耐心等待安装完成即可
- 若是安装失败，可以尝试直接克隆源码：

```bash
# 克隆仓库到插件目录
cd /AstrBot/data/plugins
git clone https://github.com/Zhalslar/astrbot_plugin_roulette

# 控制台重启AstrBot
```

## ⌨️ 使用说明

### 游戏指令


|        命令        |                    说明                    |
| :----------------: | :----------------------------------------: |
| /转盘@群友 [秒数] |   双人对决，发起者先手，可自定义禁言时长   |
|    /转盘 [秒数]    | 多人模式，每人只能开一枪，可自定义禁言时长 |
|       /开枪       |                向自己开一枪                |
|  /认输 或 /玩不起  |             主动认输，接受惩罚             |
| /退出 或 /结束游戏 |     主动退出游戏（最后一发时不可退出）     |

### 战绩查询


|                命令                |              说明              |
| :---------------------------------: | :----------------------------: |
| /我的战绩 或 /转盘战绩 或 /查看战绩 | 查看个人战绩，包括胜率、连胜等 |
|           /对战记录@群友           |    查看与某人的1v1对战记录    |
|        /赌圣榜 或 /胜率排行        | 胜率最高排行榜TOP5（至少5局） |
|               /散财榜               | 胜率最低排行榜TOP5（至少5局） |
|               /赌狗榜               |       参与局数排行榜TOP5       |

### 管理员指令


|          命令          |           说明           |
| :--------------------: | :----------------------: |
|       /结束转盘       | 强制结束当前群的转盘游戏 |
| /转盘帮助 或 /轮盘帮助 |     查看完整帮助信息     |

### 游戏规则

- 🎲 转盘有6发子弹位，随机一发是实弹
- 👥 双人模式：发起者先手，轮流开枪
- 🎮 多人模式：每人限开一枪
- ⏱️ 可在指令后加秒数自定义禁言时长（最高24小时）
- 🔇 中枪者禁言，时长可自定义或随机
- 📊 自动记录战绩，可查看个人数据和排行榜
- ⚠️ 最后一发时必须开枪或认输，不能退出
- ⏰ 游戏超时无人开枪将自动结束（默认1小时，每次开枪后重置计时）

## 👥 贡献指南

- 🌟 Star 这个项目！（点右上角的星星，感谢支持！）
- 🐛 提交 Issue 报告问题
- 💡 提出新功能建议
- 🔧 提交 Pull Request 改进代码

## 📌 注意事项

- 想第一时间得到反馈的可以来作者的插件反馈群（QQ群）：460973561（不点star不给进）
