<h1 align="center">FJNU_OJ_Peeper_Bot (Nonebot Branch)</h1>
<div align="center">
  <strong>基于 PBG 项目和官方接口的 QQ 机器人</strong><br>
  <em>一个专注于算法竞赛辅助的 NoneBot 机器人</em>
</div>

<br>

<div align="center">
  <a href="https://github.com/Floating-Ocean/FJNU_OJ_Peeper_Bot/actions/workflows/codeql.yml"><img alt="CodeQL Scan" src="https://img.shields.io/github/actions/workflow/status/Floating-Ocean/FJNU_OJ_Peeper_Bot/codeql.yml?style=flat-square"></a>
  <a href="https://github.com/Floating-Ocean/FJNU_OJ_Peeper_Bot/commits"><img alt="GitHub Last Commit" src="https://img.shields.io/github/last-commit/Floating-Ocean/FJNU_OJ_Peeper_Bot?style=flat-square"></a>
  <a href="https://github.com/Floating-Ocean/FJNU_OJ_Peeper_Bot/graphs/contributors"><img alt="GitHub contributors" src="https://img.shields.io/github/contributors/Floating-Ocean/FJNU_OJ_Peeper_Bot?style=flat-square"></a>
  <a href="https://github.com/Floating-Ocean/FJNU_OJ_Peeper_Bot/commits"><img alt="GitHub commit activity" src="https://img.shields.io/github/commit-activity/y/Floating-Ocean/FJNU_OJ_Peeper_Bot?style=flat-square"></a>
</div>

---

## ⚠️ 重要提示

**本分支正在积极开发中，以跟上 main branch 的功能。**

本分支由 [qwedc001](https://github.com/qwedc001) 维护。请注意，此分支与主项目完全不同：

- **主项目**：经过配置后可以独立运行的官方 QQ 机器人
- **本分支**：基于 NoneBot 框架的机器人插件

本分支的代码需要在 **NoneBot** 环境下运行。如果你不了解 **NoneBot**，请先阅读 [Nonebot 文档](https://nonebot.dev/)。

> **注意**：本分支下的具体代码实现可能会与主项目产生差异，但整体功能追求与主分支保持一致。当前分支支持的内容可能略少于主分支，仍处于适配阶段。

---

## 🚀 技术架构

- **框架**：NoneBot 2.x
- **协议**：OneBot V11
- **通信方式**：FastAPI 反向 WebSocket（与 Napcat 通信）
- **配置位置**：`config.json`
- **插件目录**：`src/plugins/`

---


## 🎯 功能支持

### 全局功能

#### 简单响应模块

- **`/help`** 或 **`/帮助`**：显示所有模块的帮助信息
- **`/活着吗`** / **`/死了吗`** / **`/似了吗`** / **`/ping`**：检查机器人是否在线

对于各个模块的具体使用方法，使用 **`/模块名 help`** 来显示对应模块的帮助信息。

#### ⭐ Cron / 定时模块 (`cron.py`)

**本分支独占功能**

- **心跳检测**：每天 0:00、6:00、12:00、18:00 向 Bot 主人发送心跳信息，证明机器人存活
- **比赛提醒**：
  - **`/schedule add [platform] [contestId]`**：订阅指定比赛的通知
    - `platform`：平台名称（codeforces / atcoder / nowcoder）
    - `contestId`：比赛 ID（Codeforces 为 URL 后的数字，AtCoder 为赛事简写如 abc123）
  - 自动在比赛开始前 1 天、2 小时、5 分钟发送提醒
  - 管理员可使用 **`/schedule addto [platform] [contestId] [groupId]`** 向指定群推送订阅通知
  - 管理员可使用 **`/schedule all`** 查看所有定时任务
  - 管理员可使用 **`/schedule removeall`** 删除所有定时提醒任务

---

### 算法竞赛功能

#### Codeforces (`/codeforces` / `/cf`)

支持功能：
- 展示指定用户基本信息和近期提交记录
- 列出近期比赛
- 列出网站上所有赛题标签（tag）
- 根据标签和难度随机挑选题目用于训练

#### AtCoder (`/atcoder` / `/atc`)

支持功能：
- 展示指定用户基本信息
- 列出近期比赛
- 根据赛题所在比赛类型和难度随机挑选题目用于训练

#### Nowcoder (`/nowcoder` / `/nc` / `/nk`)

支持功能：
- 展示指定用户基本信息
- 列出近期比赛

---

### 娱乐功能

#### 随机色卡 (`/color` / `/颜色` / `/色` / `/来个颜色` / `/来个色卡` / `/色卡`)

随机从色卡 JSON 中选取一个颜色，生成精美的色卡图片，包含：
- 颜色的中文名称和拼音
- HEX、RGB、HSV 颜色值
- 二维码链接到颜色详情页面

![色卡示例](image/README/1737780160490.png)

---

### 管理功能

#### 插件权限管理

- 插件权限检查
- 插件权限设置

---

## ⚙️ 配置说明

### 环境变量

在项目根目录创建 `.env` 文件，或设置以下环境变量：

```env
# Bot 配置
BOT_OWNER=123456789              # Bot 主人 QQ 号
SUPERUSERS=123456789,987654321   # 超级用户列表（逗号分隔）

# API 密钥（可选）
CLIST_APIKEY=your_clist_apikey   # Clist API 密钥
UPTIME_APIKEY=your_uptime_apikey # UptimeRobot API 密钥
UPTIME_PAGE_ID=your_page_id      # UptimeRobot 页面 ID
```

### 配置文件

参考 `config_example.json` 创建 `config.json`：

```json
{
  "role": {
    "admin_id": ["<Admin-ID-1>", "<Admin-ID-2>"],
    "mod_id": ["<Mod-ID-1>", "<Mod-ID-2>"]
  },
  "modules": {
    "general": {
      "http_proxy": "",
      "https_proxy": ""
    },
    "clist": {
      "apikey": "<Full-Clist-Api-Key>"
    },
    "uptime": {
      "page_id": "<UptimeRobot-Status-Page-ID>"
    },
    "game": {
      "exclude": {}
    },
    "peeper": {
      "exclude_id": [],
      "configs": []
    }
  }
}
```

---

## 📥 安装与运行

### 前置要求

- Python 3.9 - 3.11
- NoneBot 2.x 环境
- Napcat（用于 QQ 协议连接）

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone <repository-url>
   cd QBot
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境**
   - 复制 `config_example.json` 为 `config.json` 并填写配置
   - 创建 `.env` 文件并设置环境变量

4. **运行机器人**
   ```bash
   python bot.py
   ```

---

## 🔧 开发说明

### 插件开发

插件应放置在 `src/plugins/` 目录下，使用 NoneBot 2.x 的插件系统。

### 帮助系统

使用 `@with_help` 装饰器注册帮助信息：

```python
from src.core.help_registry import with_help

@with_help("模块名称")
async def handle_command(event: MessageEvent):
    """
    指令说明
    指令: /command1, /command2
    """
    pass
```

---


## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

详见 [LICENSE](LICENSE) 文件。

---

## 🔗 相关链接

- [NoneBot 文档](https://nonebot.dev/)
- [OneBot 标准](https://onebot.dev/)
- [主项目仓库](https://github.com/Floating-Ocean/FJNU_OJ_Peeper_Bot)

---

<div align="center">
  <strong>⭐ 如果这个项目对你有帮助，请给个 Star ⭐</strong>
</div>
