# TimerPro 多版本项目

## 项目结构

```
├── README.md                  # 项目说明
├── timerProV15.py            # 主程序（桌面版，V15 终极版）
├── shop_config.json          # 店铺配置文件（桌面版）
├── active_data.json          # 活跃数据文件（桌面版）
├── history_data.json         # 历史数据文件（桌面版）
├── history_log.csv           # 历史日志文件（桌面版）
├── TimerProWeb.spec         # PyInstaller 打包配置
├── Dockerfile               # Docker 配置
├── docker-compose.yml       # Docker Compose 配置
├── __pycache__/             # Python 缓存目录
├── .git/                    # Git 版本控制
├── .claude/                 # Claude Code 配置
├── .vscode/                 # VS Code 配置
├── build/                   # 构建临时目录
├── dist/                    # 打包输出目录
├── archive/                 # 归档目录（旧版本文件）
├── tests/                   # 测试脚本目录
├── documents/               # 文档目录
├── web_app/                 # Web 版本（FastAPI）
│   ├── main.py             # 单商家版本（旧版）
│   ├── main_saas.py        # 多商家 SaaS 版本（推荐）
│   ├── database.py         # 数据库模型
│   ├── init_db.py          # 数据库初始化脚本
│   ├── auth.py             # 认证和 JWT 服务
│   ├── routers/            # API 路由模块
│   │   ├── merchants.py   # 商家管理 API
│   │   ├── orders.py      # 订单管理 API
│   │   ├── history.py     # 历史流水 API
│   │   └── customer.py    # 顾客端二维码/号牌 API
│   ├── static/             # 静态文件
│   │   ├── index.html     # 主界面
│   │   ├── login.html     # 登录页面
│   │   └── register.html  # 注册页面
│   ├── test_saas.py       # SaaS 测试脚本
│   ├── .env               # 环境变量配置 (SMTP邮件等)
│   ├── requirements.txt   # 依赖清单
│   ├── timerpro_saas.db   # SaaS专属 SQLite 数据库
│   └── README_SAAS.md    # SaaS 文档
└── xcx_client/              # 微信小程序（保持不变）
    ├── cloudfunctions/     # 云函数
    └── miniprogram/        # 小程序前端
```

## 版本说明

### 1. 桌面版（V15 终极版）
- **文件**: `timerProV15.py`
- **功能**: 完整的计时收款系统，支持暂停、结账、团购等
- **运行**: `python timerProV15.py`

### 2. Web 版本

#### 2.1 SaaS 多商家版本（推荐）
- **文件**: `web_app/main_saas.py`
- **技术**: FastAPI + SQLite + JWT + Vue 3
- **功能**: 多商家收银系统，支持商家注册、登录、独立数据管理
- **启动**:
  ```bash
  cd web_app
  # 创建 .env 环境变量文件并配置发件邮箱 (可参考 README_SAAS.md)
  python init_db.py  # 首次运行需要初始化数据库
  python main_saas.py
  ```
- **访问**: http://localhost:5050
- **文档**: 查看 `web_app/README_SAAS.md`

#### 2.2 单商家版本（旧版）
- **文件**: `web_app/main.py`
- **技术**: FastAPI + 前端
- **功能**: 单商家收银系统
- **启动**:
  ```bash
  cd web_app
  python main.py
  ```

### 3. 微信小程序
- **目录**: `xcx_client/`
- **技术**: 微信小程序原生开发
- **注意**: 开发中，保持原样

## 数据存储说明

不同版本使用不同的数据存储方式：
- **桌面版（V15）/ 旧版 Web单商家** 使用本地 JSON 文件存储数据：
  - `shop_config.json` - 店铺配置
  - `active_data.json` - 活跃数据（桌号、包厢状态等）
  - `history_data.json` - 历史数据
  - `history_log.csv` - 操作日志
- **SaaS 多商家版本** 完全独立，使用真正的关系型数据库引擎：
  - `web_app/timerpro_saas.db` - 隔离了多租户数据的 SQLite 数据库

## 整理说明

- **tests/** - 所有测试脚本已整理到此处
- **documents/** - 所有测试报告和文档已整理到此处
- **archive/** - 旧版本文件已归档
- **xcx_client/** - 微信小程序目录保持不变，未做任何修改