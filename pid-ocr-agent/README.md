# P&ID OCR Agent - HAZOP & Instrument Index Generator
## Version 1.0

**KJV Solutions™**
*Automated P&ID Analysis and Safety Documentation System*

---

## Overview

The P&ID OCR Agent is an advanced industrial document processing system designed to automatically scan, analyze, and extract critical information from Piping and Instrumentation Diagrams (P&IDs). The system leverages state-of-the-art OCR technology, computer vision, and AI to generate comprehensive HAZOP studies and detailed Instrument Indexes.

## Key Features

### 🔍 Advanced OCR & Document Processing
- Multi-page PDF processing with high-accuracy OCR
- Support for scanned and digital P&ID documents
- Automatic image enhancement and preprocessing
- Symbol recognition using computer vision
- Line detection and flow analysis

### 🛡️ HAZOP Generation
- Automated hazard identification from P&ID analysis
- Industry-standard HAZOP methodology (Guide Words)
- Risk assessment and consequence analysis
- Safeguard identification
- Recommendation generation
- Export to PDF, Excel, and Word formats

### 📋 Instrument Index Generation
- Comprehensive instrument catalog extraction
- Tag number identification and classification
- Instrument specifications and details
- Service description and location tracking
- Cross-referencing with P&ID sheets
- Export to multiple formats

### 🎯 Key Capabilities
- Batch processing of multiple P&IDs
- Intelligent symbol recognition library
- Line and connection tracing
- Equipment identification and tagging
- Process flow analysis
- Integration with existing plant databases
- Audit trail and version control

---

## Technology Stack

### Backend
- **Framework**: FastAPI 0.104.1 (Python 3.9+)
- **OCR Engine**: Tesseract 5.0+ with pytesseract
- **Computer Vision**: OpenCV 4.8+
- **PDF Processing**: PyMuPDF (fitz), pdf2image
- **AI/ML**: TensorFlow 2.x for symbol recognition
- **Database**: PostgreSQL 13+ with SQLAlchemy 2.0
- **Document Generation**: ReportLab, python-docx, openpyxl
- **Task Queue**: Celery with Redis

### Frontend
- **Framework**: React 18.2.0 with TypeScript
- **Build Tool**: Vite
- **UI Library**: Material-UI / Tailwind CSS
- **State Management**: React Context API / Redux
- **File Upload**: React Dropzone
- **PDF Viewer**: React-PDF
- **Charts**: Recharts for analytics

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Message Queue**: Redis 6+
- **Cache**: Redis
- **Storage**: MinIO for document storage
- **API Documentation**: Swagger/OpenAPI

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Frontend (React)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  Upload  │ │  HAZOP   │ │Instrument│ │ Reports  │       │
│  │  Module  │ │  Viewer  │ │  Index   │ │ Export   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │   OCR    │ │   P&ID   │ │  HAZOP   │ │Instrument│       │
│  │ Engine   │ │Processor │ │Generator │ │  Index   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│              Processing & Storage Layer                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │PostgreSQL│ │  Redis   │ │  MinIO   │ │ Celery   │       │
│  │   DB     │ │  Cache   │ │ Storage  │ │  Queue   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Document Output                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                     │
│  │   PDF    │ │  Excel   │ │   Word   │                     │
│  │  HAZOP   │ │  Index   │ │  Report  │                     │
│  └──────────┘ └──────────┘ └──────────┘                     │
└──────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.9+
- Node.js 18+
- Tesseract OCR 5.0+

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd pid-ocr-agent
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start with Docker Compose**
```bash
docker-compose up -d
```

4. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Manual Setup

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install Tesseract OCR
# Ubuntu/Debian: sudo apt-get install tesseract-ocr
# macOS: brew install tesseract
# Windows: Download from GitHub releases

# Run database migrations
alembic upgrade head

# Start the backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## Usage Guide

### 1. Upload P&ID Documents
- Support formats: PDF, PNG, JPG, TIFF
- Batch upload multiple documents
- Automatic page detection and splitting

### 2. OCR Processing
- Automatic text extraction
- Symbol recognition and classification
- Line and connection detection
- Equipment and instrument identification

### 3. HAZOP Generation
- Automatic node identification
- Guide word application (No/None, More, Less, Reverse, etc.)
- Deviation analysis
- Cause and consequence identification
- Safeguard detection
- Risk rating calculation
- Recommendation generation

### 4. Instrument Index Creation
- Tag number extraction and validation
- Instrument type classification
- Service description generation
- Location and P&ID sheet cross-reference
- Specifications extraction

### 5. Export and Reporting
- HAZOP Study Report (PDF/Word)
- Instrument Index (Excel/CSV)
- Summary reports and analytics
- Audit trail documentation

---

## Project Structure

```
pid-ocr-agent/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── config/            # Configuration management
│   │   ├── core/              # Core utilities
│   │   ├── models/            # Database models
│   │   ├── modules/           # Feature modules
│   │   │   ├── ocr/          # OCR processing
│   │   │   ├── pid_processor/ # P&ID analysis
│   │   │   ├── hazop_generator/ # HAZOP generation
│   │   │   ├── instrument_index/ # Instrument indexing
│   │   │   └── reporting/    # Report generation
│   │   ├── schemas/          # Pydantic schemas
│   │   └── services/         # Business services
│   ├── tests/                # Test suite
│   └── requirements.txt      # Python dependencies
│
├── frontend/                  # React frontend
│   ├── public/               # Static assets
│   └── src/
│       ├── components/       # Reusable components
│       ├── modules/          # Feature modules
│       ├── services/         # API services
│       └── types/            # TypeScript types
│
├── database/                 # Database scripts
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── docker/                  # Docker configurations
├── docker-compose.yml       # Service orchestration
└── README.md               # This file
```

---

## API Documentation

### Key Endpoints

#### Document Upload
```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data

Response: {
  "document_id": "uuid",
  "status": "processing",
  "page_count": 10
}
```

#### OCR Processing
```http
POST /api/v1/ocr/process/{document_id}

Response: {
  "status": "completed",
  "extracted_items": {
    "instruments": 45,
    "equipment": 23,
    "lines": 67
  }
}
```

#### Generate HAZOP
```http
POST /api/v1/hazop/generate/{document_id}

Response: {
  "hazop_id": "uuid",
  "nodes": 15,
  "deviations": 120,
  "status": "completed"
}
```

#### Generate Instrument Index
```http
POST /api/v1/instruments/generate-index/{document_id}

Response: {
  "index_id": "uuid",
  "instrument_count": 45,
  "status": "completed"
}
```

---

## Configuration

### Environment Variables

```bash
# Backend
DATABASE_URL=postgresql://user:pass@localhost:5432/pidocr
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# OCR Settings
TESSERACT_PATH=/usr/bin/tesseract
OCR_LANGUAGE=eng
OCR_DPI=300

# AI Model Settings
MODEL_PATH=/app/models
CONFIDENCE_THRESHOLD=0.75

# Application
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_ORIGINS=http://localhost:3000

# Frontend
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

---

## HAZOP Methodology

### Guide Words Applied
1. **NO/NONE** - Complete negation of design intent
2. **MORE** - Quantitative increase
3. **LESS** - Quantitative decrease
4. **AS WELL AS** - Qualitative increase
5. **PART OF** - Qualitative decrease
6. **REVERSE** - Logical opposite of intent
7. **OTHER THAN** - Complete substitution

### Process Parameters Analyzed
- Flow
- Pressure
- Temperature
- Level
- Composition
- pH
- Viscosity

---

## Instrument Classification

### ISA Standard Tags
- **FE** - Flow Element
- **FT** - Flow Transmitter
- **FC** - Flow Controller
- **PT** - Pressure Transmitter
- **TT** - Temperature Transmitter
- **LT** - Level Transmitter
- **LAHH** - Level Alarm High High
- **PSV** - Pressure Safety Valve
- **CV** - Control Valve
- And many more...

---

## Development

### Running Tests
```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm test
```

### Code Quality
```bash
# Backend linting
cd backend
flake8 app/
black app/
mypy app/

# Frontend linting
cd frontend
npm run lint
npm run type-check
```

---

## Performance

### Processing Benchmarks
- Single P&ID page OCR: ~5-10 seconds
- Symbol recognition: ~2-3 seconds per page
- HAZOP generation: ~30-60 seconds per document
- Instrument Index: ~10-20 seconds per document

### Scalability
- Concurrent document processing using Celery
- Horizontal scaling with load balancer
- Redis caching for improved performance
- Database optimization with indexes

---

## Security

### Authentication
- JWT-based authentication
- Role-based access control (RBAC)
- API key management

### Data Protection
- Encrypted document storage
- Audit logging for all operations
- GDPR compliance considerations
- Secure file upload validation

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

---

## License

Proprietary - KJV Solutions™

---

## Support

For technical support, contact:
- Email: support@kjvsolutions.com
- Documentation: https://docs.kjvsolutions.com
- Issue Tracker: GitHub Issues

---

## Changelog

### Version 1.0.0 (Initial Release)
- OCR processing for P&ID documents
- Automated HAZOP generation
- Instrument Index creation
- Multi-format export capabilities
- Web-based user interface
- Docker deployment support

---

## Roadmap

### Upcoming Features
- [ ] Machine learning model training for custom symbols
- [ ] 3D model integration
- [ ] Mobile app support
- [ ] Cloud deployment options (AWS, Azure, GCP)
- [ ] Advanced analytics dashboard
- [ ] Integration with ERP systems
- [ ] Multi-language support
- [ ] Collaborative editing features

---

**Built with ❤️ by KJV Solutions™**
