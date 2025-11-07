"""
P&ID OCR Agent - Main FastAPI Application
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import uvicorn
import logging
from pathlib import Path
import shutil
from datetime import datetime

from app.config.settings import settings
from app.core.tasks import (
    process_pid_document,
    analyze_pid_symbols,
    generate_hazop,
    generate_instrument_index,
    process_complete_workflow,
    batch_process_documents
)

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Automated P&ID OCR, HAZOP, and Instrument Index Generation System",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now().isoformat()
    }


# Document upload endpoint
@app.post("/api/v1/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    project_name: str = "Default Project",
    pid_reference: str = "P&ID-001",
    auto_process: bool = True
):
    """
    Upload a P&ID document for processing

    Args:
        file: P&ID document (PDF, PNG, JPG, TIFF)
        project_name: Project name
        pid_reference: P&ID reference number
        auto_process: Automatically start processing (default: True)

    Returns:
        Document upload confirmation and task ID
    """
    try:
        # Validate file type
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in settings.IMAGE_SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Supported: {settings.IMAGE_SUPPORTED_FORMATS}"
            )

        # Create upload directory
        upload_dir = Path(settings.TEMP_UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate document ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        document_id = f"{project_name}_{timestamp}"
        file_path = upload_dir / f"{document_id}{file_ext}"

        # Save file
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Document uploaded: {document_id}")

        response = {
            "status": "success",
            "document_id": document_id,
            "file_name": file.filename,
            "file_path": str(file_path),
            "project_name": project_name,
            "pid_reference": pid_reference,
            "upload_time": datetime.now().isoformat()
        }

        # Automatically start processing if enabled
        if auto_process:
            task = process_complete_workflow.delay(
                str(file_path),
                document_id,
                project_name,
                pid_reference
            )

            response["task_id"] = task.id
            response["processing_status"] = "started"
            logger.info(f"Started processing task: {task.id}")

        return response

    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Batch upload endpoint
@app.post("/api/v1/documents/batch-upload")
async def batch_upload_documents(
    files: List[UploadFile] = File(...),
    project_name: str = "Default Project"
):
    """
    Batch upload multiple P&ID documents
    Processes all documents autonomously

    Args:
        files: List of P&ID documents
        project_name: Project name

    Returns:
        Batch upload confirmation and task ID
    """
    try:
        upload_dir = Path(settings.TEMP_UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_paths = []

        for idx, file in enumerate(files):
            file_ext = Path(file.filename).suffix.lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            document_id = f"{project_name}_{timestamp}_{idx}"
            file_path = upload_dir / f"{document_id}{file_ext}"

            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            file_paths.append(str(file_path))

        logger.info(f"Batch uploaded {len(files)} documents")

        # Start batch processing
        task = batch_process_documents.delay(file_paths, project_name)

        return {
            "status": "success",
            "document_count": len(files),
            "project_name": project_name,
            "task_id": task.id,
            "processing_status": "started",
            "upload_time": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in batch upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Task status endpoint
@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Get status of a processing task

    Args:
        task_id: Task identifier

    Returns:
        Task status and results
    """
    from app.core.celery_app import celery_app

    try:
        task = celery_app.AsyncResult(task_id)

        response = {
            "task_id": task_id,
            "status": task.state,
            "timestamp": datetime.now().isoformat()
        }

        if task.state == "SUCCESS":
            response["result"] = task.result
        elif task.state == "FAILURE":
            response["error"] = str(task.info)
        elif task.state == "PROCESSING":
            response["meta"] = task.info

        return response

    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Start OCR processing
@app.post("/api/v1/ocr/process/{document_id}")
async def start_ocr_processing(document_id: str, document_path: str):
    """
    Start OCR processing for a document

    Args:
        document_id: Document identifier
        document_path: Path to document

    Returns:
        Task information
    """
    try:
        task = process_pid_document.delay(document_path, document_id)

        return {
            "status": "started",
            "task_id": task.id,
            "document_id": document_id,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error starting OCR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Generate HAZOP
@app.post("/api/v1/hazop/generate")
async def start_hazop_generation(
    document_id: str,
    project_name: str,
    pid_reference: str,
    nodes_data: List[dict]
):
    """
    Generate HAZOP study

    Args:
        document_id: Document identifier
        project_name: Project name
        pid_reference: P&ID reference
        nodes_data: List of node data

    Returns:
        Task information
    """
    try:
        task = generate_hazop.delay(
            document_id,
            project_name,
            pid_reference,
            nodes_data
        )

        return {
            "status": "started",
            "task_id": task.id,
            "document_id": document_id,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error starting HAZOP generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Generate Instrument Index
@app.post("/api/v1/instruments/generate-index")
async def start_instrument_index_generation(
    document_id: str,
    project_name: str,
    pid_reference: str,
    instrument_tags: List[str]
):
    """
    Generate Instrument Index

    Args:
        document_id: Document identifier
        project_name: Project name
        pid_reference: P&ID reference
        instrument_tags: List of instrument tags

    Returns:
        Task information
    """
    try:
        task = generate_instrument_index.delay(
            document_id,
            project_name,
            pid_reference,
            instrument_tags
        )

        return {
            "status": "started",
            "task_id": task.id,
            "document_id": document_id,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error starting instrument index generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Complete workflow
@app.post("/api/v1/workflow/complete")
async def start_complete_workflow(
    document_path: str,
    document_id: str,
    project_name: str,
    pid_reference: str
):
    """
    Start complete autonomous workflow
    Runs all steps: OCR → Symbol Analysis → HAZOP → Instrument Index

    Args:
        document_path: Path to document
        document_id: Document identifier
        project_name: Project name
        pid_reference: P&ID reference

    Returns:
        Task information
    """
    try:
        task = process_complete_workflow.delay(
            document_path,
            document_id,
            project_name,
            pid_reference
        )

        return {
            "status": "started",
            "task_id": task.id,
            "document_id": document_id,
            "workflow": "complete",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error starting complete workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD
    )
