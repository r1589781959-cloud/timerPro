"""
TimerPro SaaS - 后端主入口 (全路径映射版)
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import traceback

# 导入
try:
    from .database import engine, Base
    from .routers import merchants as merchants_mod
    from .routers.orders import router as orders_router, tables_router, config_router
except ImportError:
    from database import engine, Base
    from routers import merchants as merchants_mod
    from routers.orders import router as orders_router, tables_router, config_router

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

@app.get("/api/system/auth-status")
async def get_auth_status():
    return {"activated": True, "machine_code": "SAAS-PRO-001", "guests": 888}

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
    uvicorn.run("web_app.main_saas:app", host="0.0.0.0", port=8000, reload=True)
