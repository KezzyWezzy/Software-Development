"""
P&ID Symbol Recognition Engine
Detects and classifies symbols, equipment, and instruments in P&ID drawings
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DetectedSymbol:
    """Represents a detected symbol in a P&ID"""
    symbol_type: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    center: Tuple[int, int]
    properties: Dict
    tag: Optional[str] = None


class SymbolRecognizer:
    """
    Recognizes and classifies symbols in P&ID documents
    """

    def __init__(self):
        """Initialize symbol recognizer with templates"""
        self.symbol_templates = self._initialize_templates()
        self.equipment_types = [
            "PUMP", "COMPRESSOR", "VESSEL", "TANK", "HEAT_EXCHANGER",
            "VALVE", "CONTROL_VALVE", "CHECK_VALVE", "SAFETY_VALVE",
            "INSTRUMENT", "ANALYZER", "TRANSMITTER"
        ]

    def _initialize_templates(self) -> Dict[str, np.ndarray]:
        """
        Initialize symbol templates for template matching
        Can be extended with ML models for better accuracy
        """
        # This would typically load pre-trained templates or ML models
        # For now, returning empty dict as placeholder
        return {}

    def detect_symbols(self, image: np.ndarray) -> List[DetectedSymbol]:
        """
        Detect all symbols in a P&ID image

        Args:
            image: Input P&ID image

        Returns:
            List of detected symbols
        """
        symbols = []

        # Detect circles (instruments, vessels)
        circles = self._detect_circles(image)
        for circle in circles:
            x, y, r = circle
            symbol = DetectedSymbol(
                symbol_type="INSTRUMENT",
                confidence=0.85,
                bbox=(x - r, y - r, 2 * r, 2 * r),
                center=(x, y),
                properties={"radius": r}
            )
            symbols.append(symbol)

        # Detect rectangles (equipment, vessels)
        rectangles = self._detect_rectangles(image)
        for rect in rectangles:
            x, y, w, h = rect
            symbol = DetectedSymbol(
                symbol_type="EQUIPMENT",
                confidence=0.80,
                bbox=(x, y, w, h),
                center=(x + w // 2, y + h // 2),
                properties={"width": w, "height": h}
            )
            symbols.append(symbol)

        # Detect triangles (valves)
        triangles = self._detect_triangles(image)
        for triangle in triangles:
            x, y, w, h = triangle
            symbol = DetectedSymbol(
                symbol_type="VALVE",
                confidence=0.75,
                bbox=(x, y, w, h),
                center=(x + w // 2, y + h // 2),
                properties={"shape": "triangle"}
            )
            symbols.append(symbol)

        logger.info(f"Detected {len(symbols)} symbols")
        return symbols

    def _detect_circles(self, image: np.ndarray) -> List[Tuple[int, int, int]]:
        """Detect circular symbols (instruments)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 5)

        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=20,
            param1=50,
            param2=30,
            minRadius=10,
            maxRadius=50
        )

        if circles is not None:
            circles = np.uint16(np.around(circles))
            return [(x, y, r) for x, y, r in circles[0]]

        return []

    def _detect_rectangles(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect rectangular symbols (equipment)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        rectangles = []
        for contour in contours:
            approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)

            if len(approx) == 4:  # Rectangle
                x, y, w, h = cv2.boundingRect(approx)
                if 50 < w < 500 and 50 < h < 500:  # Size filters
                    rectangles.append((x, y, w, h))

        return rectangles

    def _detect_triangles(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect triangular symbols (valves)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        triangles = []
        for contour in contours:
            approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)

            if len(approx) == 3:  # Triangle
                x, y, w, h = cv2.boundingRect(approx)
                if 20 < w < 200 and 20 < h < 200:
                    triangles.append((x, y, w, h))

        return triangles

    def detect_lines(self, image: np.ndarray) -> List[Dict]:
        """
        Detect process lines (pipes) in P&ID

        Returns:
            List of detected lines with properties
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=100,
            minLineLength=50,
            maxLineGap=10
        )

        detected_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]

                # Calculate line properties
                length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi

                detected_lines.append({
                    "start": (x1, y1),
                    "end": (x2, y2),
                    "length": length,
                    "angle": angle
                })

        logger.info(f"Detected {len(detected_lines)} process lines")
        return detected_lines

    def classify_symbol(self, symbol_image: np.ndarray) -> Dict[str, float]:
        """
        Classify a symbol using ML model or template matching

        Args:
            symbol_image: Cropped symbol image

        Returns:
            Classification probabilities for each symbol type
        """
        # Placeholder for ML-based classification
        # In production, this would use a trained TensorFlow/PyTorch model

        # For now, return dummy classifications
        classifications = {
            "PUMP": 0.25,
            "VALVE": 0.20,
            "INSTRUMENT": 0.30,
            "VESSEL": 0.15,
            "HEAT_EXCHANGER": 0.10
        }

        return classifications

    def extract_connections(
        self,
        symbols: List[DetectedSymbol],
        lines: List[Dict]
    ) -> List[Tuple[int, int]]:
        """
        Determine which symbols are connected by process lines

        Args:
            symbols: List of detected symbols
            lines: List of detected lines

        Returns:
            List of symbol pairs that are connected
        """
        connections = []

        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols[i + 1:], start=i + 1):
                # Check if any line connects these two symbols
                for line in lines:
                    if self._line_connects_symbols(line, sym1, sym2):
                        connections.append((i, j))
                        break

        logger.info(f"Found {len(connections)} connections between symbols")
        return connections

    def _line_connects_symbols(
        self,
        line: Dict,
        sym1: DetectedSymbol,
        sym2: DetectedSymbol,
        threshold: int = 20
    ) -> bool:
        """Check if a line connects two symbols"""
        x1, y1 = line["start"]
        x2, y2 = line["end"]

        # Check if line endpoints are near symbol centers
        dist1_start = np.sqrt((x1 - sym1.center[0]) ** 2 + (y1 - sym1.center[1]) ** 2)
        dist1_end = np.sqrt((x2 - sym1.center[0]) ** 2 + (y2 - sym1.center[1]) ** 2)
        dist2_start = np.sqrt((x1 - sym2.center[0]) ** 2 + (y1 - sym2.center[1]) ** 2)
        dist2_end = np.sqrt((x2 - sym2.center[0]) ** 2 + (y2 - sym2.center[1]) ** 2)

        connects = (
            (dist1_start < threshold and dist2_end < threshold) or
            (dist1_end < threshold and dist2_start < threshold)
        )

        return connects


class InstrumentDetector:
    """
    Specialized detector for instruments in P&IDs
    """

    def __init__(self):
        self.isa_prefixes = [
            "FE", "FT", "FC", "FI", "FY", "FV", "FIC", "FRC",
            "PT", "PI", "PC", "PY", "PCV", "PSV", "PSHH", "PSL",
            "TT", "TI", "TC", "TE", "TY", "TCV",
            "LT", "LI", "LC", "LE", "LY", "LAH", "LAL", "LAHH", "LALL",
            "AT", "AE", "AI", "AC",
            "CV", "HV", "MOV", "SOV",
            "HS", "ZS", "FS"
        ]

    def identify_instrument_type(self, tag: str) -> Dict[str, str]:
        """
        Identify instrument type from tag

        Args:
            tag: Instrument tag (e.g., FT-101)

        Returns:
            Dictionary with instrument classification
        """
        tag_upper = tag.upper().replace("-", "").replace("_", "")

        for prefix in self.isa_prefixes:
            if tag_upper.startswith(prefix):
                return self._decode_isa_tag(prefix)

        return {
            "measured_variable": "UNKNOWN",
            "function": "UNKNOWN",
            "description": "Unknown instrument"
        }

    def _decode_isa_tag(self, prefix: str) -> Dict[str, str]:
        """Decode ISA tag prefix to instrument details"""
        first_letter_map = {
            "F": "Flow",
            "P": "Pressure",
            "T": "Temperature",
            "L": "Level",
            "A": "Analysis",
            "H": "Hand/Manual",
            "Z": "Position",
            "S": "Speed/Frequency"
        }

        function_map = {
            "E": "Element/Sensor",
            "T": "Transmitter",
            "I": "Indicator",
            "C": "Controller",
            "V": "Valve",
            "Y": "Relay/Compute",
            "A": "Alarm",
            "H": "High Alarm",
            "L": "Low Alarm",
            "S": "Switch"
        }

        first_letter = prefix[0] if prefix else "?"
        function_letters = prefix[1:] if len(prefix) > 1 else ""

        measured_var = first_letter_map.get(first_letter, "Unknown")

        if len(function_letters) >= 1:
            function = function_map.get(function_letters[0], "Unknown")
        else:
            function = "Unknown"

        description = f"{measured_var} {function}"

        return {
            "measured_variable": measured_var,
            "function": function,
            "description": description,
            "prefix": prefix
        }
