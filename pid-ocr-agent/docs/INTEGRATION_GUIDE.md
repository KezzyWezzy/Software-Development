# P&ID OCR Agent - Integration Guide

## Overview

This guide explains how to integrate the P&ID OCR Agent into your existing React + FastAPI + PostgreSQL application for autonomous 24/7 operation.

---

## Architecture Overview

The P&ID OCR Agent is designed as a microservice that can run independently or be integrated into existing systems. It provides:

1. **OCR Engine** - Extracts text and tags from P&ID documents
2. **Symbol Recognition** - Identifies instruments, equipment, and process lines
3. **HAZOP Generator** - Automatically creates comprehensive HAZOP studies
4. **Instrument Index** - Generates detailed instrument catalogs
5. **Autonomous Processing** - Runs 24/7 without human intervention using Celery workers

---

## Integration Methods

### Method 1: Standalone Microservice (Recommended)

Run as a separate service that communicates with your main application via REST API.

**Advantages:**
- Independent scaling
- Isolated processing resources
- Easy to maintain and update
- No impact on main application performance

**Setup:**
```bash
# Start the microservice
cd pid-ocr-agent
docker-compose up -d

# Access API at http://localhost:8000
# Monitor workers at http://localhost:5555 (Flower)
```

**Integration with Your React Frontend:**
```typescript
// services/pidOcrApi.ts
const API_BASE_URL = 'http://localhost:8000/api/v1';

export const uploadPID = async (file: File, projectName: string) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('project_name', projectName);
  formData.append('auto_process', 'true');

  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: 'POST',
    body: formData
  });

  return response.json();
};

export const getTaskStatus = async (taskId: string) => {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`);
  return response.json();
};
```

### Method 2: Direct Integration

Integrate the modules directly into your existing FastAPI backend.

**Steps:**

1. **Copy modules to your backend:**
```bash
cp -r pid-ocr-agent/backend/app/modules/* your-app/backend/app/modules/
```

2. **Update your requirements.txt:**
```bash
cat pid-ocr-agent/backend/requirements.txt >> your-app/backend/requirements.txt
pip install -r your-app/backend/requirements.txt
```

3. **Add Celery configuration:**
```python
# your-app/backend/app/core/celery_app.py
from celery import Celery
from app.config.settings import settings

celery_app = Celery(
    "your_app",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.core.tasks"]
)
```

4. **Import tasks in your routes:**
```python
# your-app/backend/app/routes/pid.py
from fastapi import APIRouter, UploadFile, File
from app.core.tasks import process_complete_workflow

router = APIRouter()

@router.post("/pid/upload")
async def upload_pid(file: UploadFile = File(...)):
    # Save file
    file_path = save_uploaded_file(file)

    # Start autonomous processing
    task = process_complete_workflow.delay(
        file_path,
        document_id,
        project_name,
        pid_reference
    )

    return {"task_id": task.id}
```

---

## Autonomous 24/7 Operation Setup

### 1. Start Celery Workers

The Celery workers process documents continuously without human intervention.

**Docker (Recommended):**
```bash
docker-compose up -d celery_worker celery_beat
```

**Manual:**
```bash
# Terminal 1: Start worker
celery -A app.core.celery_app worker --loglevel=info --concurrency=4

# Terminal 2: Start beat scheduler
celery -A app.core.celery_app beat --loglevel=info

# Terminal 3: Start Flower monitoring
celery -A app.core.celery_app flower --port=5555
```

### 2. Configure Auto-Processing

**Enable automatic processing on upload:**
```python
# In your upload endpoint
@app.post("/api/v1/documents/upload")
async def upload_document(
    file: UploadFile,
    project_name: str,
    auto_process: bool = True  # Enable by default
):
    if auto_process:
        task = process_complete_workflow.delay(
            document_path,
            document_id,
            project_name,
            pid_reference
        )
```

### 3. Batch Processing

For processing multiple documents continuously:

```python
# Process entire directory
document_paths = [
    "/path/to/pid1.pdf",
    "/path/to/pid2.pdf",
    "/path/to/pid3.pdf"
]

task = batch_process_documents.delay(document_paths, "Project Name")
```

### 4. Monitor Processing

**Web Interface (Flower):**
Visit http://localhost:5555 to monitor:
- Active tasks
- Completed tasks
- Failed tasks
- Worker status
- Task statistics

**API:**
```bash
# Check task status
curl http://localhost:8000/api/v1/tasks/{task_id}
```

---

## Database Integration

### Option 1: Use Separate Database

Keep P&ID OCR data in its own database (recommended for microservice approach).

```python
# pid-ocr-agent/backend/app/config/settings.py
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/pidocr"
```

### Option 2: Use Existing Database

Share your main application's database.

```python
# Update DATABASE_URL to point to your existing database
DATABASE_URL = "postgresql://user:pass@host:5432/your_db"
```

**Create tables:**
```bash
cd pid-ocr-agent/backend
alembic upgrade head
```

---

## React Frontend Integration

### 1. Create API Service

```typescript
// src/services/pidOcrService.ts
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_PID_OCR_API_URL || 'http://localhost:8000/api/v1';

export interface PIDUploadResponse {
  document_id: string;
  task_id: string;
  status: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: 'PENDING' | 'PROCESSING' | 'SUCCESS' | 'FAILURE';
  result?: any;
  error?: string;
}

export const pidOcrService = {
  uploadDocument: async (
    file: File,
    projectName: string,
    pidReference: string
  ): Promise<PIDUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_name', projectName);
    formData.append('pid_reference', pidReference);
    formData.append('auto_process', 'true');

    const response = await axios.post(
      `${API_BASE_URL}/documents/upload`,
      formData
    );
    return response.data;
  },

  batchUpload: async (
    files: File[],
    projectName: string
  ): Promise<any> => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('project_name', projectName);

    const response = await axios.post(
      `${API_BASE_URL}/documents/batch-upload`,
      formData
    );
    return response.data;
  },

  getTaskStatus: async (taskId: string): Promise<TaskStatusResponse> => {
    const response = await axios.get(`${API_BASE_URL}/tasks/${taskId}`);
    return response.data;
  },

  downloadHAZOP: async (documentId: string, format: 'pdf' | 'excel' | 'word') => {
    const response = await axios.get(
      `${API_BASE_URL}/export/hazop/${documentId}`,
      {
        params: { format },
        responseType: 'blob'
      }
    );
    return response.data;
  },

  downloadInstrumentIndex: async (documentId: string, format: 'excel' | 'csv') => {
    const response = await axios.get(
      `${API_BASE_URL}/export/instruments/${documentId}`,
      {
        params: { format },
        responseType: 'blob'
      }
    );
    return response.data;
  }
};
```

### 2. Create Upload Component

```typescript
// src/components/PIDUpload.tsx
import React, { useState } from 'react';
import { pidOcrService } from '../services/pidOcrService';

export const PIDUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    try {
      const result = await pidOcrService.uploadDocument(
        file,
        'My Project',
        'P&ID-001'
      );

      setTaskId(result.task_id);
      alert('Processing started! Task ID: ' + result.task_id);
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <h2>Upload P&ID Document</h2>
      <input
        type="file"
        accept=".pdf,.png,.jpg,.jpeg,.tiff"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button onClick={handleUpload} disabled={!file || uploading}>
        {uploading ? 'Uploading...' : 'Upload & Process'}
      </button>
      {taskId && <p>Task ID: {taskId}</p>}
    </div>
  );
};
```

### 3. Create Status Monitor Component

```typescript
// src/components/TaskMonitor.tsx
import React, { useEffect, useState } from 'react';
import { pidOcrService, TaskStatusResponse } from '../services/pidOcrService';

interface Props {
  taskId: string;
}

export const TaskMonitor: React.FC<Props> = ({ taskId }) => {
  const [status, setStatus] = useState<TaskStatusResponse | null>(null);

  useEffect(() => {
    const pollInterval = setInterval(async () => {
      try {
        const result = await pidOcrService.getTaskStatus(taskId);
        setStatus(result);

        if (result.status === 'SUCCESS' || result.status === 'FAILURE') {
          clearInterval(pollInterval);
        }
      } catch (error) {
        console.error('Failed to get status:', error);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [taskId]);

  if (!status) return <div>Loading...</div>;

  return (
    <div>
      <h3>Task Status: {status.status}</h3>
      {status.status === 'SUCCESS' && status.result && (
        <div>
          <p>Processing complete!</p>
          <pre>{JSON.stringify(status.result, null, 2)}</pre>
        </div>
      )}
      {status.status === 'FAILURE' && (
        <div>
          <p>Error: {status.error}</p>
        </div>
      )}
    </div>
  );
};
```

---

## Environment Variables

Add these to your `.env` file:

```bash
# P&ID OCR Service
PIDOCR_API_URL=http://localhost:8000/api/v1

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# OCR Settings
TESSERACT_PATH=/usr/bin/tesseract
OCR_LANGUAGE=eng
OCR_DPI=300

# Processing
MAX_CONCURRENT_JOBS=5
PROCESSING_TIMEOUT=600
```

---

## Production Deployment

### 1. Docker Swarm / Kubernetes

Scale workers based on load:

```yaml
# docker-compose.prod.yml
services:
  celery_worker:
    deploy:
      replicas: 4  # Run 4 workers
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
```

### 2. Monitoring & Alerts

Set up monitoring for:
- Worker health
- Task queue length
- Processing failures
- System resources

### 3. Auto-Scaling

Configure auto-scaling based on:
- Queue length
- Worker utilization
- Processing time

---

## Troubleshooting

### Workers Not Processing

**Check worker status:**
```bash
celery -A app.core.celery_app inspect active
```

**Check Redis connection:**
```bash
redis-cli ping
```

### OCR Failures

**Check Tesseract installation:**
```bash
tesseract --version
```

**Verify file permissions:**
```bash
ls -la /tmp/pid-uploads
```

### Database Connection Issues

**Test connection:**
```bash
psql -h localhost -U postgres -d pidocr
```

---

## API Reference

### Upload Document
```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data

file: <file>
project_name: string
pid_reference: string
auto_process: boolean
```

### Get Task Status
```http
GET /api/v1/tasks/{task_id}

Response:
{
  "task_id": "uuid",
  "status": "SUCCESS",
  "result": { ... }
}
```

### Complete Workflow
```http
POST /api/v1/workflow/complete

{
  "document_path": "string",
  "document_id": "string",
  "project_name": "string",
  "pid_reference": "string"
}
```

---

## Support

For issues or questions:
- GitHub Issues: [repository-url]/issues
- Documentation: [repository-url]/docs
- Email: support@kjvsolutions.com

---

**Built by KJV Solutions™ for 24/7 Autonomous Operation**
