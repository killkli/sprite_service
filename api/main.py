from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from celery import Celery
import shutil
import os
import uuid

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
