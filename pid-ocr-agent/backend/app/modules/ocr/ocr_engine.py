"""
OCR Engine for P&ID Document Processing
Handles text extraction from scanned and digital P&ID documents
"""
import cv2
import numpy as np
import pytesseract
from PIL import Image
from pdf2image import convert_from_path, convert_from_bytes
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class OCREngine:
    """
    Advanced OCR Engine for P&ID documents with preprocessing and optimization
    """

    def __init__(
        self,
        tesseract_path: Optional[str] = None,
        language: str = "eng",
        dpi: int = 300,
        psm: int = 3,
        oem: int = 3
    ):
        """
        Initialize OCR Engine

        Args:
            tesseract_path: Path to tesseract executable
            language: OCR language (default: eng)
            dpi: DPI for PDF conversion (default: 300)
            psm: Page segmentation mode (default: 3 - auto)
            oem: OCR Engine mode (default: 3 - default)
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

        self.language = language
        self.dpi = dpi
        self.psm = psm
        self.oem = oem
        self.config = f'--oem {oem} --psm {psm}'

        logger.info(f"OCR Engine initialized with language={language}, dpi={dpi}")

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR accuracy

        Args:
            image: Input image as numpy array

        Returns:
            Preprocessed image
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        # Increase contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast = clahe.apply(denoised)

        # Binarization using adaptive thresholding
        binary = cv2.adaptiveThreshold(
            contrast,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

        # Morphological operations to remove noise
        kernel = np.ones((1, 1), np.uint8)
        morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        return morph

    def extract_text_from_image(
        self,
        image: np.ndarray,
        preprocess: bool = True
    ) -> Dict[str, any]:
        """
        Extract text from an image using OCR

        Args:
            image: Input image as numpy array
            preprocess: Apply preprocessing (default: True)

        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            if preprocess:
                processed_image = self.preprocess_image(image)
            else:
                processed_image = image

            # Convert numpy array to PIL Image
            pil_image = Image.fromarray(processed_image)

            # Extract text
            text = pytesseract.image_to_string(
                pil_image,
                lang=self.language,
                config=self.config
            )

            # Get detailed data including confidence scores
            data = pytesseract.image_to_data(
                pil_image,
                lang=self.language,
                config=self.config,
                output_type=pytesseract.Output.DICT
            )

            # Calculate average confidence
            confidences = [
                float(conf) for conf in data['conf']
                if conf != '-1' and conf != ''
            ]
            avg_confidence = np.mean(confidences) if confidences else 0.0

            return {
                "text": text.strip(),
                "confidence": avg_confidence,
                "word_count": len(text.split()),
                "details": data,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            return {
                "text": "",
                "confidence": 0.0,
                "word_count": 0,
                "details": None,
                "status": "error",
                "error": str(e)
            }

    def pdf_to_images(
        self,
        pdf_path: str,
        dpi: Optional[int] = None
    ) -> List[np.ndarray]:
        """
        Convert PDF pages to images

        Args:
            pdf_path: Path to PDF file
            dpi: DPI for conversion (uses default if not specified)

        Returns:
            List of images as numpy arrays
        """
        dpi = dpi or self.dpi

        try:
            # Convert PDF to images
            images = convert_from_path(
                pdf_path,
                dpi=dpi,
                fmt='png'
            )

            # Convert PIL images to numpy arrays
            np_images = [np.array(img) for img in images]

            logger.info(f"Converted {len(np_images)} pages from PDF")
            return np_images

        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            return []

    def pdf_to_images_from_bytes(
        self,
        pdf_bytes: bytes,
        dpi: Optional[int] = None
    ) -> List[np.ndarray]:
        """
        Convert PDF bytes to images

        Args:
            pdf_bytes: PDF file as bytes
            dpi: DPI for conversion

        Returns:
            List of images as numpy arrays
        """
        dpi = dpi or self.dpi

        try:
            images = convert_from_bytes(
                pdf_bytes,
                dpi=dpi,
                fmt='png'
            )

            np_images = [np.array(img) for img in images]
            logger.info(f"Converted {len(np_images)} pages from PDF bytes")
            return np_images

        except Exception as e:
            logger.error(f"PDF bytes conversion failed: {str(e)}")
            return []

    def extract_text_from_pdf(
        self,
        pdf_path: str,
        preprocess: bool = True
    ) -> List[Dict[str, any]]:
        """
        Extract text from all pages of a PDF

        Args:
            pdf_path: Path to PDF file
            preprocess: Apply image preprocessing

        Returns:
            List of extraction results for each page
        """
        results = []

        # First try to extract text directly (for digital PDFs)
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                if text.strip():  # If text found, it's a digital PDF
                    results.append({
                        "page": page_num + 1,
                        "text": text.strip(),
                        "confidence": 100.0,  # Direct extraction
                        "word_count": len(text.split()),
                        "method": "direct",
                        "status": "success"
                    })
                else:
                    # No text found, treat as scanned image
                    results.append(None)

            doc.close()

            # If all pages have text, return direct extraction results
            if all(r is not None for r in results):
                logger.info(f"Digital PDF: extracted text from {len(results)} pages directly")
                return results

        except Exception as e:
            logger.warning(f"Direct text extraction failed, falling back to OCR: {str(e)}")

        # Convert to images and perform OCR
        images = self.pdf_to_images(pdf_path)

        if not images:
            return []

        results = []
        for idx, image in enumerate(images):
            logger.info(f"Processing page {idx + 1}/{len(images)}")

            ocr_result = self.extract_text_from_image(image, preprocess=preprocess)
            ocr_result["page"] = idx + 1
            ocr_result["method"] = "ocr"
            results.append(ocr_result)

        return results

    def detect_text_boxes(
        self,
        image: np.ndarray
    ) -> List[Tuple[int, int, int, int]]:
        """
        Detect text regions in an image using EAST text detector or contours

        Args:
            image: Input image

        Returns:
            List of bounding boxes (x, y, w, h)
        """
        # Preprocess
        processed = self.preprocess_image(image)

        # Find contours
        contours, _ = cv2.findContours(
            processed,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Filter and sort contours
        text_boxes = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            # Filter by size (adjust thresholds as needed)
            if w > 20 and h > 10 and w < 1000 and h < 500:
                text_boxes.append((x, y, w, h))

        # Sort by y-coordinate (top to bottom), then x-coordinate (left to right)
        text_boxes.sort(key=lambda b: (b[1], b[0]))

        return text_boxes

    def extract_text_from_regions(
        self,
        image: np.ndarray,
        regions: List[Tuple[int, int, int, int]]
    ) -> List[Dict[str, any]]:
        """
        Extract text from specific regions of an image

        Args:
            image: Input image
            regions: List of regions as (x, y, w, h)

        Returns:
            List of extraction results for each region
        """
        results = []

        for idx, (x, y, w, h) in enumerate(regions):
            # Extract region
            roi = image[y:y+h, x:x+w]

            # Perform OCR
            ocr_result = self.extract_text_from_image(roi, preprocess=True)
            ocr_result["region"] = idx + 1
            ocr_result["bbox"] = (x, y, w, h)

            if ocr_result["text"]:
                results.append(ocr_result)

        return results

    def batch_process(
        self,
        image_paths: List[str],
        preprocess: bool = True
    ) -> List[Dict[str, any]]:
        """
        Process multiple images in batch

        Args:
            image_paths: List of image file paths
            preprocess: Apply preprocessing

        Returns:
            List of extraction results
        """
        results = []

        for idx, img_path in enumerate(image_paths):
            logger.info(f"Processing image {idx + 1}/{len(image_paths)}: {img_path}")

            try:
                # Load image
                image = cv2.imread(img_path)

                if image is None:
                    logger.error(f"Failed to load image: {img_path}")
                    continue

                # Extract text
                result = self.extract_text_from_image(image, preprocess=preprocess)
                result["file_path"] = img_path
                result["file_name"] = Path(img_path).name

                results.append(result)

            except Exception as e:
                logger.error(f"Failed to process {img_path}: {str(e)}")
                results.append({
                    "file_path": img_path,
                    "file_name": Path(img_path).name,
                    "status": "error",
                    "error": str(e)
                })

        return results


class PIDOCREngine(OCREngine):
    """
    Specialized OCR Engine for P&ID documents with domain-specific optimizations
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # P&ID specific settings
        self.instrument_tag_pattern = r'[A-Z]{2,4}[-_]?[0-9]{3,5}[A-Z]?'
        self.line_number_pattern = r'[0-9]{1,4}[-"][A-Z]{2,6}[-"][0-9]{1,4}["]?'

    def extract_instrument_tags(self, text: str) -> List[str]:
        """
        Extract instrument tags from text using pattern matching

        Args:
            text: Input text

        Returns:
            List of identified instrument tags
        """
        import re

        tags = re.findall(self.instrument_tag_pattern, text)
        return list(set(tags))  # Remove duplicates

    def extract_line_numbers(self, text: str) -> List[str]:
        """
        Extract line numbers from text

        Args:
            text: Input text

        Returns:
            List of identified line numbers
        """
        import re

        line_numbers = re.findall(self.line_number_pattern, text)
        return list(set(line_numbers))

    def process_pid_document(
        self,
        file_path: str,
        preprocess: bool = True
    ) -> Dict[str, any]:
        """
        Process a P&ID document and extract relevant information

        Args:
            file_path: Path to P&ID document (PDF or image)
            preprocess: Apply preprocessing

        Returns:
            Comprehensive extraction results
        """
        file_path_obj = Path(file_path)
        file_ext = file_path_obj.suffix.lower()

        if file_ext == '.pdf':
            pages = self.extract_text_from_pdf(file_path, preprocess=preprocess)
        else:
            image = cv2.imread(file_path)
            if image is None:
                return {"status": "error", "error": "Failed to load image"}

            result = self.extract_text_from_image(image, preprocess=preprocess)
            pages = [result]

        # Aggregate results
        all_text = " ".join([page["text"] for page in pages if page.get("text")])

        # Extract P&ID specific elements
        instrument_tags = self.extract_instrument_tags(all_text)
        line_numbers = self.extract_line_numbers(all_text)

        return {
            "file_name": file_path_obj.name,
            "page_count": len(pages),
            "pages": pages,
            "full_text": all_text,
            "instrument_tags": instrument_tags,
            "line_numbers": line_numbers,
            "instrument_count": len(instrument_tags),
            "line_count": len(line_numbers),
            "status": "success"
        }
