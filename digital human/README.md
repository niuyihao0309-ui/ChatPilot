# 数字人（魔珐星云）改动打包

> 这是**给你审阅的改动集**，全部放在本文件夹里，**尚未写进工程**。
> 审阅 OK 后，按子文件夹说明合并到 `customer-service-backend/`。

---

## 这条路线定了什么

| 决策 | 选择 |
|---|---|
| 平台 | 魔珐星云（轻、快、便宜，demo 用；灵眸的 WebSocket+RTC 全链路以后要再加） |
| 数字人位置 | 聊天框**左侧独立竖列**（方案 A，9:16 竖屏） |
| 触发 | 连上数字人后，Bot 文字回复**自动朗读**；没连则保持你原有 TTS 🔈 按钮 |
| 凭证 | `.env` 留占位（填真实 AppId/AppSecret 后直接跑），**密钥只存后端**，前端源码不出现 |
| 现有业务 | `engine/service/task/knowledge/chitchat/plan` **一字不动**，数字人是外挂一条 |

## 文件夹结构

```
digital human/
├── README.md                  ← 本文件（先看这个）
├── 01-backend/                后端改动（4 文件 + 说明）
│   ├── conf_config.py         覆盖 conf/config.py（+3 字段）
│   ├── api_app.py             覆盖 api/app.py（+2 行路由装配）
│   ├── digital_human_router.py  新建 api/routers/digital_human_router.py
│   ├── env.snippet            .env 追加 3 行（占位）
│   ├── gitignore.snippet      新建 .gitignore（挡 .env）
│   └── 01-后端改动说明.md     逐文件精确改法 + 验证命令
└── 02-frontend/              前端改动（4 文件 + 说明）
    ├── index.html             覆盖（head 加魔珐 SDK）
    ├── App_vue_template.html  App.vue 模板插数字人列
    ├── App_vue_js.js          App.vue script 加方法 + 2 处小改
    ├── App_vue_css.css        App.vue style 加样式 + 1 处小改
    └── 02-前端改动说明.md     精确锚点行号 + 验证步骤
```

## 改动统计（一共）

| 层 | 覆盖 | 新建 | 小改 |
|---|---|---|---|
| 后端 | `conf/config.py`、`api/app.py` | `digital_human_router.py`、`.gitignore` | `.env` 追加 |
| 前端 | `index.html` | — | `App.vue` 模板/脚本/样式 4 处 |
| **合计** | 3 | 2 | 4 处小改 |

> 前端 `App.vue` 用「精确锚点补丁 + 片段」而不是全量重写，因为它 2140 行，全量版没法定位核对。
> 每处都标了**原行号 + 原样 + 改成 + 为什么**，照说明合就行。

## 合并顺序（建议）

1. 先 `01-backend`：按《01-后端改动说明.md》改 4 文件 → `uv run python main.py` 起后端 → 验证 `/api/digital-human/credentials` 返回（没填凭证应返回空串不报错）→ 原 `/api/chat` 照常。
2. 再填 `.env` 真实凭证。
3. 最后 `02-frontend`：按《02-前端改动说明.md》合 4 处 → `npm run dev` → 左侧出现数字人列 → 连上 → 发消息看它开口读。

## 魔珐星云账号（没的话先去弄）

1. https://xingyun3d.com/ 注册/登录
2. 应用中心 → 创建「具身驱动应用」→ 选形象/音色/表演
3. 拿到 **App ID** + **App Secret**（实名送 300 分钟免费）

---

_生成于 2026-10-07，供审阅。确认改动方式后我可直接把这些写进工程并跑一遍验证。_
