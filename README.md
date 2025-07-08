<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="/img/obot_logo_inv.png">
    <source media="(prefers-color-scheme: light)" srcset="/img/obot_logo.png">
    <img alt="OBot's ACM" width="40%" src="/img/obot_logo.png">
  </picture>
</h1>
<div align="center">
  <strong>A.k.a. O宝的AC梦 · 基于PBG等项目的QQ机器人</strong><br>
</div><br>

<div align="center">
  <a href="https://github.com/qwedc001/Peeper-Board-Generator/blob/master/requirements.txt"><img alt="Supported Python Version" src="https://img.shields.io/badge/Python-3.10+-teal?style=flat-square"></a>
  <a href="https://github.com/Floating-Ocean/OBot-ACM/actions/workflows/codeql.yml"><img alt="CodeQL Scan" src="https://img.shields.io/github/actions/workflow/status/Floating-Ocean/OBot-ACM/codeql.yml?style=flat-square&label=codeql+scan"></a>
  <a href="https://github.com/Floating-Ocean/OBot-ACM/releases/latest"><img alt="GitHub Release" src="https://img.shields.io/github/v/release/Floating-Ocean/OBot-ACM?style=flat-square&label=OBot's+ACM"></a>
  <a href="https://github.com/Floating-Ocean/OBot-ACM/graphs/contributors"><img alt="GitHub contributors" src="https://img.shields.io/github/contributors/Floating-Ocean/OBot-ACM?style=flat-square"></a>
</div>
<div align="center">
  <a href="https://github.com/Floating-Ocean/OBot-ACM/commits"><img alt="GitHub Last Commit" src="https://img.shields.io/github/last-commit/Floating-Ocean/OBot-ACM?style=flat-square"></a>
  <a href="https://github.com/Floating-Ocean/OBot-ACM/commits"><img alt="GitHub commit activity" src="https://img.shields.io/github/commit-activity/y/Floating-Ocean/OBot-ACM?style=flat-square"></a>
</div>

## 开始之前

本仓库包含主项目和一个分支，主项目是一个经过配置后可以独立运行的 **官方 QQ 机器人**，而分支则是一个 **Nonebot 机器人**。

请在运行机器人前，将 [`config_example.json`](https://github.com/Floating-Ocean/OBot-ACM/blob/main/config_example.json) 重命名为 [`config.json`](https://github.com/Floating-Ocean/OBot-ACM/blob/main/config_example.json)，并根据文件内提示填写相关字段。

机器人依赖一些项目，需要自行建立 `lib` 文件夹并进行相关配置。

[>> 前往 **Nonebot** 侧开发分支](https://github.com/Floating-Ocean/OBot-ACM/tree/dev-nonebot)

## Bot 能做什么

### 算法竞赛

- 训练榜单图片，基于 [`Peeper-Board-Generator`](https://github.com/qwedc001/Peeper-Board-Generator) 项目；

- 实用功能，基于算法竞赛平台 API 实现：
  
  | 可用功能       | 近日比赛         | 用户信息    | 随机选题    | 玩家对战    | 最近提交记录  | 比赛表现实时预估     |
  |------------|--------------|---------|---------|---------|---------|--------------|
  | Codeforces | &#9745;      | &#9745; | &#9745; | &#9745; | &#9745; | &#9745; $^2$ |
  | AtCoder    | &#9745; $^1$ | &#9745; | &#9745; |         |         |              |
  | NowCoder   | &#9745;      | &#9745; |         |         |         |              |
  
  $^1$ AtCoder 平台的随机选题基于 Clist API；
  
  $^2$ Codeforces 平台的比赛表现实时预估（ELO）基于 [`Carrot`](https://github.com/meooow25/carrot) 浏览器插件项目；

- 近日比赛清单整合图（可手动导入 XCPC 比赛）；

- 平台可用性查询，基于 [`Uptime Robot`](https://uptimerobot.com/)；

### 实用功能

- 表情包的分类管理、添加、审核、随机，自动识别图片中的文字并打上标签；

- 菜谱查询、随机，基于 [`HowToCook`](https://github.com/Anduin2017/HowToCook)；

- 一言获取，基于 [`Hitokoto`](https://hitokoto.cn/)；

- 颜色卡片，在中国传统颜色中随机选择；

- 真随机数、随机序列，基于 [`Random.org`](https://www.random.org/)；

- 二维码图片生成；

### 交互式小游戏

- 下落式俄罗斯方块；

- 区间猜数字；

- 1A2B猜数字；

<details open>
<summary><h3>可用指令</h3></summary>
  <img src="/img/command_instructions.jpg" alt="可用指令"/>
</details>

### PRs Welcome

项目不定期更新中，欢迎向项目提 PR ~
