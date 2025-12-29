from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional
from celery import Celery
import shutil
import os
import uuid
import base64


class ProcessingParams(BaseModel):
    """
    Sprite 處理參數
    Sprite processing parameters
    """
    distance_threshold: int = Field(
        default=80,
        ge=10, le=500,
        description="合併距離閾值 / Merge distance threshold (pixels)"
    )
    size_ratio_threshold: float = Field(
        default=0.4,
        ge=0.1, le=1.0,
        description="大小區分閾值 / Size ratio threshold"
    )
    alpha_threshold: int = Field(
        default=50,
        ge=1, le=254,
        description="Alpha 通道閾值 / Alpha channel threshold"
    )
    min_area_ratio: float = Field(
        default=0.0005,
        ge=0.0001, le=0.1,
        description="最小面積比例 / Minimum area ratio"
    )
    max_area_ratio: float = Field(
        default=0.25,
        ge=0.05, le=0.9,
        description="最大面積比例 / Maximum area ratio"
    )


class GenerateRequest(BaseModel):
    """
    文字生圖請求模型
    Text-to-image generation request model
    """
    prompt: str
    model: str = "nano-banana"  # "nano-banana" or "nano-banana-pro"
    auto_process: bool = True   # 是否自動進入 Sprite 處理流程
    temperature: float = Field(
        default=1.0,
        ge=0.0, le=2.0,
        description="生成溫度 / Generation temperature (0=deterministic, 2=creative)"
    )
    # Sprite 處理參數 / Sprite processing parameters
    distance_threshold: int = Field(default=80, ge=10, le=500)
    size_ratio_threshold: float = Field(default=0.4, ge=0.1, le=1.0)
    alpha_threshold: int = Field(default=50, ge=1, le=254)
    min_area_ratio: float = Field(default=0.0005, ge=0.0001, le=0.1)
    max_area_ratio: float = Field(default=0.25, ge=0.05, le=0.9)

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
async def create_process_task(
    file: UploadFile = File(...),
    distance_threshold: int = Form(80),
    size_ratio_threshold: float = Form(0.4),
    alpha_threshold: int = Form(50),
    min_area_ratio: float = Form(0.0005),
    max_area_ratio: float = Form(0.25)
):
    """
    上傳圖片並建立處理任務
    Upload image and create processing task

    Processing Parameters:
    - **distance_threshold**: 合併距離閾值 (10-500) / Merge distance threshold
    - **size_ratio_threshold**: 大小區分閾值 (0.1-1.0) / Size ratio threshold
    - **alpha_threshold**: Alpha 通道閾值 (1-254) / Alpha channel threshold
    - **min_area_ratio**: 最小面積比例 (0.0001-0.1) / Min area ratio
    - **max_area_ratio**: 最大面積比例 (0.05-0.9) / Max area ratio
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

    # 處理參數
    processing_params = {
        "distance_threshold": distance_threshold,
        "size_ratio_threshold": size_ratio_threshold,
        "alpha_threshold": alpha_threshold,
        "min_area_ratio": min_area_ratio,
        "max_area_ratio": max_area_ratio
    }

    # 發送任務給 Worker
    task = celery_client.send_task(
        "tasks.process_sprite",
        args=[file_path, task_id],
        kwargs={"processing_params": processing_params}
    )

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
    - **temperature**: 生成溫度 (0.0-2.0) / Generation temperature
    - Processing parameters for sprite detection/merging
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

    # 處理參數
    processing_params = {
        "distance_threshold": request.distance_threshold,
        "size_ratio_threshold": request.size_ratio_threshold,
        "alpha_threshold": request.alpha_threshold,
        "min_area_ratio": request.min_area_ratio,
        "max_area_ratio": request.max_area_ratio
    }

    # 選擇任務類型
    if request.auto_process:
        task_name = "tasks.generate_and_process"
    else:
        task_name = "tasks.generate_image"

    # 發送任務給 Worker
    task = celery_client.send_task(
        task_name,
        args=[request.prompt, request.model],
        kwargs={
            "temperature": request.temperature,
            "processing_params": processing_params
        }
    )

    return {
        "task_id": task.id,
        "status": "queued",
        "auto_process": request.auto_process,
        "message": "Generation task submitted. Check status with /status/{task_id}"
    }


@app.post("/generate/with-reference")
async def create_generate_with_reference_task(
    prompt: str = Form(...),
    model: str = Form("nano-banana"),
    auto_process: bool = Form(True),
    reference_image: UploadFile = File(...),
    temperature: float = Form(1.0),
    distance_threshold: int = Form(80),
    size_ratio_threshold: float = Form(0.4),
    alpha_threshold: int = Form(50),
    min_area_ratio: float = Form(0.0005),
    max_area_ratio: float = Form(0.25)
):
    """
    使用參考圖片進行 Image-to-Image 生成
    Generate sprite using reference image (Image-to-Image)

    - **prompt**: 編輯指令 / Edit instruction (e.g., "make it a zombie version")
    - **model**: 模型選擇 / Model selection ("nano-banana" or "nano-banana-pro")
    - **auto_process**: 是否自動進入 Sprite 處理 / Auto process into sprites
    - **reference_image**: 參考圖片檔案 / Reference image file
    - **temperature**: 生成溫度 (0.0-2.0) / Generation temperature
    - Processing parameters for sprite detection/merging
    """
    # 驗證 prompt 不為空
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # 驗證模型選擇
    valid_models = ["nano-banana", "nano-banana-pro"]
    if model not in valid_models:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model. Choose from: {valid_models}"
        )

    # 產生唯一 ID 並儲存參考圖片
    task_id = str(uuid.uuid4())
    ref_filename = f"ref_{task_id}.png"
    ref_file_path = os.path.join(UPLOAD_DIR, ref_filename)

    try:
        with open(ref_file_path, "wb") as buffer:
            shutil.copyfileobj(reference_image.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reference image save error: {str(e)}")

    # 處理參數
    processing_params = {
        "distance_threshold": distance_threshold,
        "size_ratio_threshold": size_ratio_threshold,
        "alpha_threshold": alpha_threshold,
        "min_area_ratio": min_area_ratio,
        "max_area_ratio": max_area_ratio
    }

    # 選擇任務類型
    if auto_process:
        task_name = "tasks.generate_with_reference_and_process"
    else:
        task_name = "tasks.generate_with_reference"

    # 發送任務給 Worker
    task = celery_client.send_task(
        task_name,
        args=[ref_file_path, prompt, model],
        kwargs={
            "temperature": temperature,
            "processing_params": processing_params
        }
    )

    return {
        "task_id": task.id,
        "status": "queued",
        "auto_process": auto_process,
        "message": "Reference image generation task submitted. Check status with /status/{task_id}"
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
