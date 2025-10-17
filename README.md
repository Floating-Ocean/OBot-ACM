<br>
<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="/img/obot_logo_inv.png">
    <source media="(prefers-color-scheme: light)" srcset="/img/obot_logo.png">
    <img alt="OBot's ACM" width="40%" src="/img/obot_logo.png">
  </picture>
</h1>
<div align="center">
  <strong>A.k.a. O宝的AC梦 · 算竞平台实时做题记录查询和更多功能</strong><br>
</div><br>

<div align="center">
  <a href="https://github.com/qwedc001/Peeper-Board-Generator/blob/master/requirements.txt"><img alt="Supported Python Version" src="https://img.shields.io/badge/Python-3.10+-teal?style=flat-square"></a>
  <a href="https://github.com/Floating-Ocean/OBot-ACM/releases"><img alt="GitHub Release" src="https://img.shields.io/github/v/release/Floating-Ocean/OBot-ACM?include_prereleases&style=flat-square&label=OBot's+ACM"></a>
  <a href="https://github.com/Floating-Ocean/OBot-ACM/blob/main/LICENSE"><img alt="GitHub Licence" src="https://img.shields.io/github/license/Floating-Ocean/OBot-ACM?style=flat-square&color=yellow"></a>
  <a href="https://github.com/Floating-Ocean/OBot-ACM/actions/workflows/codeql.yml"><img alt="CodeQL Scan" src="https://img.shields.io/github/actions/workflow/status/Floating-Ocean/OBot-ACM/codeql.yml?style=flat-square&label=codeql+scan"></a>
</div>
<div align="center">
  <a href="https://github.com/Floating-Ocean/OBot-ACM/commits"><img alt="GitHub Last Commit" src="https://img.shields.io/github/last-commit/Floating-Ocean/OBot-ACM?style=flat-square"></a>
  <a href="https://github.com/Floating-Ocean/OBot-ACM/commits"><img alt="GitHub commit activity" src="https://img.shields.io/github/commit-activity/y/Floating-Ocean/OBot-ACM?style=flat-square"></a>
  <a href="https://github.com/Floating-Ocean/OBot-ACM/graphs/contributors"><img alt="GitHub contributors" src="https://img.shields.io/github/contributors/Floating-Ocean/OBot-ACM?style=flat-square"></a>
</div><br>

## 开始之前

在运行机器人前，请将 **[`config_example.json`](config_example.json)** 复制为 **`config.json`**，并根据文件内提示填写相关字段。

> [!CAUTION]
> 1. 项目依赖包含部分修改的 **[`botpy`](https://github.com/Floating-Ocean/botpy)**；
> 2. 项目依赖子模块，以 `git submodule` 的形式被引用在项目中，请在克隆时加上 `--recursive` 参数。

### 部署

可参考下面的脚本进行部署。

```bash
git clone https://github.com/Floating-Ocean/OBot-ACM.git --recursive
cd OBot-ACM
pip install -r requirements.txt
pip uninstall qq-botpy
pip install git+https://github.com/Floating-Ocean/botpy.git
```

### 运行

项目实现了一个简单的守护进程，可按需使用。

```bash
python main.py     # 带守护进程
python entry.py    # 直接运行
```

### 其他分支

本仓库包含主项目和一个分支，主项目是一个经过配置后可以独立运行的 **官方 QQ 机器人**，而分支则是一个 **Nonebot 机器人**。

主项目有放弃 `botpy` 并切换到 `Nonebot` 侧继续维护的计划，目前先等待 `Nonebot` 侧分支开发完成。

**[>> 前往 Nonebot 侧开发分支](https://github.com/Floating-Ocean/OBot-ACM/tree/refactor-nonebot)**

## Bot 能做什么

### 算法竞赛

- 训练榜单图片，基于 **[`Peeper-Board-Generator`](https://github.com/qwedc001/Peeper-Board-Generator)** 项目；

- 实用功能，基于算法竞赛平台 API 实现：

  | 可用功能       | 近日比赛         | 用户信息    | 随机选题    | 比赛榜单         | 玩家对战    | 最近提交记录  |
    |------------|--------------|---------|---------|--------------|---------|---------|
  | Codeforces | &#9745;      | &#9745; | &#9745; | &#9745; $^1$ | &#9745; | &#9745; |
  | AtCoder    | &#9745; $^2$ | &#9745; | &#9745; |              |         |         |
  | NowCoder   | &#9745;      | &#9745; |         | &#9745;      |         |         |

  $^1$ Codeforces 平台支持比赛表现实时预估（ELO），基于 **[`Carrot`](https://github.com/meooow25/carrot)** 浏览器插件项目；

  $^2$ AtCoder 平台的随机选题通过 **[`CList API`](https://clist.by/api/v4/doc/)** 获取数据源；

- 近日比赛清单整合图（可手动导入 XCPC 比赛）；

- 选手获奖信息查询，基于 **[`CPCFinder`](https://cpcfinder.com)** 和 **[`OIerDb`](https://oier.baoshuo.dev/)** 平台；

- 多平台可用性查询，基于 **[`Uptime Robot`](https://uptimerobot.com/)** 平台；

### 实用功能

- 表情包的分类管理、添加、审核、随机，自动识别图片中的文字并打上标签；

- 菜谱查询、随机，基于 **[`HowToCook`](https://github.com/Anduin2017/HowToCook)** 开源项目；

- 一言获取，基于 **[`Hitokoto`](https://hitokoto.cn/)** 平台；

- 颜色卡片，在中国传统颜色中随机选择；

- 真随机数、随机序列，基于 **[`Random.org`](https://www.random.org/)** 平台；

- 二维码图片生成；

- 电棍活字印刷（并非实用）；

### 交互式小游戏

- 下落式俄罗斯方块；

- 区间猜数字；

- 1A2B猜数字；

<details>
<summary><h3>可用指令（点击展开）</h3></summary>
  <img src="/img/command_instructions.png" alt="可用指令"/>
</details>

## 关于

本项目直接来源于训练榜单可视化项目 **[`Peeper-Board-Generator`](https://github.com/qwedc001/Peeper-Board-Generator)** 和 **[`Hydro_Peeper_Module`](https://github.com/Floating-Ocean/Hydro_Peeper_Module)**，旨在快速且便捷地查询当前榜单。

### 致谢

感谢以下贡献者，以及所有 OBot 的使用者。如果这个项目给你带来了帮助，可以考虑点个 Star 哦~

<a href="https://github.com/Floating-Ocean/OBot-ACM/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Floating-Ocean/OBot-ACM" alt="Contributors Graph"/>
</a>

### 许可

本项目使用 AGPL-3.0 开源协议进行授权，请遵守相关条款。

### 贡献

项目不定期更新中，欢迎向项目提 PR 呢~
