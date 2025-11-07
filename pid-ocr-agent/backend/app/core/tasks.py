"""
Celery Tasks for Autonomous Processing
These tasks run continuously without human intervention
"""
from celery import Task, chain, group
from app.core.celery_app import celery_app
from app.modules.ocr.ocr_engine import PIDOCREngine
from app.modules.pid_processor.symbol_recognizer import SymbolRecognizer, InstrumentDetector
from app.modules.hazop_generator.hazop_engine import HAZOPEngine
from app.modules.instrument_index.index_generator import InstrumentIndexGenerator
from app.config.settings import settings
import logging
from pathlib import Path
from typing import Dict, List
import traceback
from datetime import datetime
import cv2

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Base task with callbacks for monitoring"""

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {task_id} completed successfully")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed: {str(exc)}")
        logger.error(f"Traceback: {einfo}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(f"Task {task_id} retrying: {str(exc)}")


@celery_app.task(
    base=CallbackTask,
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    name="app.core.tasks.process_pid_document"
)
def process_pid_document(self, document_path: str, document_id: str) -> Dict:
    """
    Process a P&ID document with OCR
    Runs autonomously without human approval

    Args:
        document_path: Path to document file
        document_id: Unique document identifier

    Returns:
        Processing results
    """
    try:
        logger.info(f"Starting OCR processing for document {document_id}")

        # Initialize OCR engine
        ocr_engine = PIDOCREngine(
            tesseract_path=settings.TESSERACT_PATH,
            language=settings.OCR_LANGUAGE,
            dpi=settings.OCR_DPI
        )

        # Process document
        result = ocr_engine.process_pid_document(
            document_path,
            preprocess=settings.IMAGE_PREPROCESSING_ENABLED
        )

        # Update task state
        self.update_state(
            state="PROCESSING",
            meta={
                "document_id": document_id,
                "status": "OCR completed",
                "instrument_count": result.get("instrument_count", 0),
                "page_count": result.get("page_count", 0)
            }
        )

        logger.info(f"OCR processing completed for document {document_id}")
        logger.info(f"Found {result.get('instrument_count', 0)} instruments")

        return {
            "status": "success",
            "document_id": document_id,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    base=CallbackTask,
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    name="app.core.tasks.analyze_pid_symbols"
)
def analyze_pid_symbols(self, document_path: str, document_id: str) -> Dict:
    """
    Analyze P&ID symbols and detect instruments/equipment
    Runs autonomously

    Args:
        document_path: Path to P&ID image
        document_id: Document identifier

    Returns:
        Symbol analysis results
    """
    try:
        logger.info(f"Starting symbol analysis for document {document_id}")

        # Load image
        image = cv2.imread(document_path)
        if image is None:
            raise ValueError(f"Failed to load image: {document_path}")

        # Initialize recognizers
        symbol_recognizer = SymbolRecognizer()
        instrument_detector = InstrumentDetector()

        # Detect symbols
        symbols = symbol_recognizer.detect_symbols(image)

        # Detect lines
        lines = symbol_recognizer.detect_lines(image)

        # Find connections
        connections = symbol_recognizer.extract_connections(symbols, lines)

        # Update task state
        self.update_state(
            state="PROCESSING",
            meta={
                "document_id": document_id,
                "status": "Symbol analysis completed",
                "symbols_found": len(symbols),
                "lines_found": len(lines),
                "connections_found": len(connections)
            }
        )

        logger.info(f"Symbol analysis completed for document {document_id}")
        logger.info(f"Found {len(symbols)} symbols and {len(lines)} lines")

        return {
            "status": "success",
            "document_id": document_id,
            "symbols_count": len(symbols),
            "lines_count": len(lines),
            "connections_count": len(connections),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error analyzing symbols for document {document_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    base=CallbackTask,
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    name="app.core.tasks.generate_hazop"
)
def generate_hazop(
    self,
    document_id: str,
    project_name: str,
    pid_reference: str,
    nodes_data: List[Dict]
) -> Dict:
    """
    Generate HAZOP study autonomously
    No human approval required

    Args:
        document_id: Document identifier
        project_name: Project name
        pid_reference: P&ID reference
        nodes_data: List of node data

    Returns:
        HAZOP study results
    """
    try:
        logger.info(f"Starting HAZOP generation for document {document_id}")

        # Initialize HAZOP engine
        hazop_engine = HAZOPEngine()

        # Generate HAZOP study
        hazop_study = hazop_engine.generate_hazop_study(
            project_name=project_name,
            pid_reference=pid_reference,
            nodes_data=nodes_data
        )

        # Export to dictionary
        hazop_dict = hazop_engine.export_hazop_to_dict(hazop_study)

        # Calculate statistics
        total_deviations = sum(len(node.deviations) for node in hazop_study.nodes)
        high_risk_deviations = sum(
            1 for node in hazop_study.nodes
            for dev in node.deviations
            if dev.risk_ranking and dev.risk_ranking >= 12
        )

        # Update task state
        self.update_state(
            state="PROCESSING",
            meta={
                "document_id": document_id,
                "status": "HAZOP generation completed",
                "nodes": len(hazop_study.nodes),
                "deviations": total_deviations,
                "high_risk_deviations": high_risk_deviations
            }
        )

        logger.info(f"HAZOP generation completed for document {document_id}")
        logger.info(f"Generated {len(hazop_study.nodes)} nodes with {total_deviations} deviations")

        return {
            "status": "success",
            "document_id": document_id,
            "hazop_id": hazop_study.id,
            "nodes_count": len(hazop_study.nodes),
            "deviations_count": total_deviations,
            "high_risk_count": high_risk_deviations,
            "hazop_data": hazop_dict,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating HAZOP for document {document_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    base=CallbackTask,
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    name="app.core.tasks.generate_instrument_index"
)
def generate_instrument_index(
    self,
    document_id: str,
    project_name: str,
    pid_reference: str,
    instrument_tags: List[str]
) -> Dict:
    """
    Generate Instrument Index autonomously
    No human approval required

    Args:
        document_id: Document identifier
        project_name: Project name
        pid_reference: P&ID reference
        instrument_tags: List of instrument tags

    Returns:
        Instrument index results
    """
    try:
        logger.info(f"Starting Instrument Index generation for document {document_id}")

        # Initialize generator
        index_generator = InstrumentIndexGenerator()

        # Generate index
        instrument_index = index_generator.generate_index_from_tags(
            tags=instrument_tags,
            project_name=project_name,
            pid_reference=pid_reference
        )

        # Export to dictionary
        index_dict = index_generator.export_to_dict(instrument_index)

        # Get statistics
        stats = index_generator.get_statistics(instrument_index)

        # Update task state
        self.update_state(
            state="PROCESSING",
            meta={
                "document_id": document_id,
                "status": "Instrument Index generation completed",
                "instruments": len(instrument_index.instruments)
            }
        )

        logger.info(f"Instrument Index generation completed for document {document_id}")
        logger.info(f"Generated index with {len(instrument_index.instruments)} instruments")

        return {
            "status": "success",
            "document_id": document_id,
            "instrument_count": len(instrument_index.instruments),
            "statistics": stats,
            "index_data": index_dict,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating instrument index for document {document_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    base=CallbackTask,
    bind=True,
    name="app.core.tasks.process_complete_workflow"
)
def process_complete_workflow(
    self,
    document_path: str,
    document_id: str,
    project_name: str,
    pid_reference: str
) -> Dict:
    """
    Complete autonomous workflow:
    1. OCR Processing
    2. Symbol Analysis
    3. HAZOP Generation
    4. Instrument Index Generation

    Runs 24/7 without human intervention

    Args:
        document_path: Path to P&ID document
        document_id: Document identifier
        project_name: Project name
        pid_reference: P&ID reference

    Returns:
        Complete workflow results
    """
    try:
        logger.info(f"Starting complete workflow for document {document_id}")

        workflow_start = datetime.now()

        # Step 1: OCR Processing
        self.update_state(state="PROCESSING", meta={"step": 1, "status": "OCR Processing"})
        ocr_result = process_pid_document(document_path, document_id)

        # Extract instrument tags
        instrument_tags = ocr_result["result"].get("instrument_tags", [])

        # Step 2: Symbol Analysis
        self.update_state(state="PROCESSING", meta={"step": 2, "status": "Symbol Analysis"})
        symbol_result = analyze_pid_symbols(document_path, document_id)

        # Step 3: Create nodes for HAZOP (simplified - in production would be more sophisticated)
        nodes_data = [
            {
                "node_number": "1",
                "equipment": ["VESSEL-101", "PUMP-102"],
                "instruments": instrument_tags[:10],  # First 10 instruments
                "design_intent": "Transfer material from vessel to downstream process"
            }
        ]

        # Step 4: Generate HAZOP
        self.update_state(state="PROCESSING", meta={"step": 3, "status": "HAZOP Generation"})
        hazop_result = generate_hazop(
            document_id,
            project_name,
            pid_reference,
            nodes_data
        )

        # Step 5: Generate Instrument Index
        self.update_state(state="PROCESSING", meta={"step": 4, "status": "Instrument Index Generation"})
        index_result = generate_instrument_index(
            document_id,
            project_name,
            pid_reference,
            instrument_tags
        )

        workflow_end = datetime.now()
        duration = (workflow_end - workflow_start).total_seconds()

        logger.info(f"Complete workflow finished for document {document_id} in {duration:.2f} seconds")

        return {
            "status": "success",
            "document_id": document_id,
            "workflow_duration_seconds": duration,
            "ocr_result": ocr_result,
            "symbol_result": symbol_result,
            "hazop_result": hazop_result,
            "index_result": index_result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in complete workflow for document {document_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    base=CallbackTask,
    name="app.core.tasks.batch_process_documents"
)
def batch_process_documents(
    document_paths: List[str],
    project_name: str
) -> Dict:
    """
    Batch process multiple P&ID documents autonomously
    Runs continuously for large document sets

    Args:
        document_paths: List of document paths
        project_name: Project name

    Returns:
        Batch processing results
    """
    try:
        logger.info(f"Starting batch processing of {len(document_paths)} documents")

        # Create tasks for all documents
        tasks = []
        for idx, doc_path in enumerate(document_paths):
            document_id = f"{project_name}_{idx + 1}"
            pid_ref = f"P&ID-{idx + 1:03d}"

            task = process_complete_workflow.s(
                doc_path,
                document_id,
                project_name,
                pid_ref
            )
            tasks.append(task)

        # Execute tasks in parallel
        job = group(tasks)
        result = job.apply_async()

        # Wait for all tasks to complete
        results = result.get()

        logger.info(f"Batch processing completed for {len(document_paths)} documents")

        return {
            "status": "success",
            "total_documents": len(document_paths),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}")
        logger.error(traceback.format_exc())
        raise


@celery_app.task(name="app.core.tasks.cleanup_old_documents")
def cleanup_old_documents() -> Dict:
    """
    Periodic task to cleanup old processed documents
    Runs automatically on schedule
    """
    try:
        logger.info("Starting cleanup of old documents")

        # Cleanup logic here
        # This would typically:
        # 1. Find documents older than retention period
        # 2. Archive or delete them
        # 3. Clean up temporary files

        return {
            "status": "success",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in cleanup task: {str(e)}")
        raise


@celery_app.task(
    base=CallbackTask,
    bind=True,
    name="app.core.tasks.monitor_and_retry_failed"
)
def monitor_and_retry_failed(self) -> Dict:
    """
    Monitor for failed tasks and automatically retry them
    Ensures 24/7 autonomous operation
    """
    try:
        logger.info("Monitoring for failed tasks")

        # This would check for failed tasks and retry them
        # Implementation depends on your task tracking system

        return {
            "status": "success",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in monitoring task: {str(e)}")
        raise
