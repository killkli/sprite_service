from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
from celery import Celery
import shutil
import os
import uuid


class GenerateRequest(BaseModel):
    """
    文字生圖請求模型
    Text-to-image generation request model
    """
    prompt: str
    model: str = "nano-banana"  # "nano-banana" or "nano-banana-pro"
    auto_process: bool = True   # 是否自動進入 Sprite 處理流程

# 初始化 FastAPI
app = FastAPI(title="Sprite Processing Service")

# 初始化 Celery 客戶端 (用來發送任務)
celery_client = Celery(
    "tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

# 共享目錄路徑
SHARED_DIR = "/app/data"
UPLOAD_DIR = os.path.join(SHARED_DIR, "uploads")
RESULT_DIR = os.path.join(SHARED_DIR, "results")

# 確保目錄存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

@app.post("/process")
async def create_process_task(file: UploadFile = File(...)):
    """
    上傳圖片並建立處理任務
    """
    # 產生唯一 ID
    task_id = str(uuid.uuid4())
    filename = f"{task_id}.png"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # 儲存上傳的檔案到共享 Volume
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save error: {str(e)}")
        
    # 發送任務給 Worker (只傳遞檔案路徑與 ID)
    # task_name 必須與 worker 中的定義一致
    task = celery_client.send_task("tasks.process_sprite", args=[file_path, task_id])
    
    return {
        "task_id": task.id,
        "status": "queued",
        "message": "Task submitted successfully. Check status with /status/{task_id}"
    }


@app.post("/generate")
async def create_generate_task(request: GenerateRequest):
    """
    從文字描述生成 Sprite
    Generate sprite from text description

    - **prompt**: 圖片描述 / Image description
    - **model**: 模型選擇 / Model selection ("nano-banana" or "nano-banana-pro")
    - **auto_process**: 是否自動進入 Sprite 處理 / Auto process into sprites
    """
    # 驗證 prompt 不為空
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # 驗證模型選擇
    valid_models = ["nano-banana", "nano-banana-pro"]
    if request.model not in valid_models:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model. Choose from: {valid_models}"
        )

    # 選擇任務類型
    if request.auto_process:
        task_name = "tasks.generate_and_process"
    else:
        task_name = "tasks.generate_image"

    # 發送任務給 Worker
    task = celery_client.send_task(
        task_name,
        args=[request.prompt, request.model]
    )

    return {
        "task_id": task.id,
        "status": "queued",
        "auto_process": request.auto_process,
        "message": "Generation task submitted. Check status with /status/{task_id}"
    }


@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    查詢任務狀態
    """
    task_result = celery_client.AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
    }
    
    if task_result.status == 'SUCCESS':
        response["download_url"] = f"/download/{task_id}"
        response["result"] = task_result.result
    elif task_result.status == 'FAILURE':
        response["error"] = str(task_result.result)
        
    return response

@app.get("/download/{task_id}")
async def download_result(task_id: str):
    """
    下載處理完成的 Zip 檔
    """
    # 檢查 Redis 中的任務狀態
    task_result = celery_client.AsyncResult(task_id)
    if task_result.status != 'SUCCESS':
        raise HTTPException(status_code=400, detail="Task not finished or failed")
    
    # 取得 Zip 檔案路徑
    zip_path = task_result.result.get("zip_path")
    
    if not zip_path or not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Result file not found")
        
    return FileResponse(
        zip_path, 
        media_type='application/zip', 
        filename=f"sprites_{task_id}.zip"
    )
