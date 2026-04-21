"""
TimerPro SaaS - 后端主入口 (全路径映射版)
"""
import os
import sys
from pathlib import Path

# ==========================================
# 兼容宝塔直接运行 main_saas.py 的相对导入问题
# 强制将 web_app 的上级目录加入环境变量，并且将顶层包强制设为 web_app
# ==========================================
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
__package__ = "web_app"
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import traceback
from dotenv import load_dotenv

# 加载 .env 环境变量（如果存在）
load_dotenv()

# 导入
try:
    from .database import engine, Base
    from .routers import merchants as merchants_mod
    from .routers.orders import router as orders_router, tables_router, config_router
    from .routers.history import history_router
except ImportError:
    from database import engine, Base
    from routers import merchants as merchants_mod
    from routers.orders import router as orders_router, tables_router, config_router
    from routers.history import history_router

# 自动创建所有表（如果不存在）
Base.metadata.create_all(bind=engine)

app = FastAPI(title="TimerPro SaaS")

# 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. 先挂载所有 API 路由 (保证 API 优先级最高)
app.include_router(merchants_mod.router)
app.include_router(orders_router)
app.include_router(tables_router)
app.include_router(config_router)
app.include_router(history_router)


# 2. 静态资源路径
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# 根路径重定向
@app.get("/")
@app.get("/{file_path:path}")
async def serve_static(file_path: str):
    if not file_path or file_path == "/":
        file_path = "index.html"
    
    full_path = STATIC_DIR / file_path
    if full_path.is_file():
        # 强制不缓存，确保每次刷新都是最新的
        return FileResponse(full_path, headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        })
    return JSONResponse(status_code=404, content={"detail": f"File {file_path} not found"})

# 异常捕获
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    err = traceback.format_exc()
    print(f"Server Error: {err}")
    return JSONResponse(status_code=500, content={"success": False, "detail": str(exc)})

if __name__ == "__main__":
    import uvicorn
    # 为了兼容宝塔不同运行目录，直接传 app 实例，且生产环境关闭 reload
    uvicorn.run(app, host="0.0.0.0", port=8000)
