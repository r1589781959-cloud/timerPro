# TimerPro Web App - Phase 1: FastAPI Backend Skeleton

## 启动服务器

在 `web_app` 目录下执行以下命令启动服务器：

```bash
# 开发模式（支持热重载）
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 访问接口

启动后可通过以下方式访问：

- **Swagger UI (API 文档)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **根路径**: http://localhost:8000/
- **局域网访问**: http://<本机IP>:8000/docs

## API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/auth/status` | 获取授权状态 |
| POST | `/api/auth/activate` | 激活授权 |
| POST | `/api/auth/guest` | 添加游客计数 |
| GET | `/api/config/shop` | 读取商店配置 |
| GET | `/api/data/active` | 读取活跃数据 |
| POST | `/api/data/active` | 更新活跃数据 |

## 依赖安装

```bash
pip install fastapi uvicorn[standard] pydantic
```

## Phase 1 完成内容

- FastAPI 应用框架
- CORS 支持（局域网访问）
- AuthManager 机器码授权系统
- shop_config.json 读取接口
- active_data.json 读写接口
- 测试 API 端点
