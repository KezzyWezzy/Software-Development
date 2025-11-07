"""
Instrument Index Generator
Creates comprehensive instrument indexes from P&ID analysis
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class InstrumentFunction(Enum):
    """Instrument function types"""
    ELEMENT = "Element/Sensor"
    TRANSMITTER = "Transmitter"
    INDICATOR = "Indicator"
    RECORDER = "Recorder"
    CONTROLLER = "Controller"
    SWITCH = "Switch"
    ALARM = "Alarm"
    VALVE = "Valve"
    RELAY = "Relay/Compute"
    UNKNOWN = "Unknown"


class MeasuredVariable(Enum):
    """Measured variables"""
    FLOW = "Flow"
    PRESSURE = "Pressure"
    TEMPERATURE = "Temperature"
    LEVEL = "Level"
    ANALYSIS = "Analysis"
    SPEED = "Speed/Frequency"
    WEIGHT = "Weight"
    POSITION = "Position"
    TIME = "Time"
    HAND = "Hand/Manual"
    UNKNOWN = "Unknown"


@dataclass
class Instrument:
    """Instrument data model"""
    tag: str
    measured_variable: MeasuredVariable = MeasuredVariable.UNKNOWN
    function: InstrumentFunction = InstrumentFunction.UNKNOWN
    service_description: str = ""
    location: str = ""
    pid_reference: str = ""
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    range_min: Optional[float] = None
    range_max: Optional[float] = None
    units: Optional[str] = None
    signal_type: Optional[str] = None  # 4-20mA, 0-10V, etc.
    process_connection: Optional[str] = None
    material: Optional[str] = None
    accuracy: Optional[str] = None
    notes: Optional[str] = None
    status: str = "Active"
    last_calibration: Optional[datetime] = None
    next_calibration: Optional[datetime] = None


@dataclass
class InstrumentIndex:
    """Complete Instrument Index"""
    project_name: str = ""
    pid_reference: str = ""
    revision: str = "0"
    date: datetime = field(default_factory=datetime.now)
    instruments: List[Instrument] = field(default_factory=list)


class InstrumentIndexGenerator:
    """
    Generator for creating comprehensive instrument indexes
    """

    def __init__(self):
        """Initialize generator with ISA standards"""
        self.first_letter_map = {
            "A": MeasuredVariable.ANALYSIS,
            "B": MeasuredVariable.UNKNOWN,  # User's choice
            "C": MeasuredVariable.UNKNOWN,  # User's choice
            "D": MeasuredVariable.UNKNOWN,  # Density/Specific Gravity
            "E": MeasuredVariable.UNKNOWN,  # Voltage
            "F": MeasuredVariable.FLOW,
            "G": MeasuredVariable.UNKNOWN,  # Gauging
            "H": MeasuredVariable.HAND,
            "I": MeasuredVariable.UNKNOWN,  # Current
            "J": MeasuredVariable.UNKNOWN,  # Power
            "K": MeasuredVariable.TIME,
            "L": MeasuredVariable.LEVEL,
            "M": MeasuredVariable.UNKNOWN,  # Moisture
            "N": MeasuredVariable.UNKNOWN,  # User's choice
            "O": MeasuredVariable.UNKNOWN,  # User's choice
            "P": MeasuredVariable.PRESSURE,
            "Q": MeasuredVariable.UNKNOWN,  # Quantity
            "R": MeasuredVariable.UNKNOWN,  # Radiation
            "S": MeasuredVariable.SPEED,
            "T": MeasuredVariable.TEMPERATURE,
            "U": MeasuredVariable.UNKNOWN,  # Multivariable
            "V": MeasuredVariable.UNKNOWN,  # Vibration
            "W": MeasuredVariable.WEIGHT,
            "X": MeasuredVariable.UNKNOWN,  # Unclassified
            "Y": MeasuredVariable.UNKNOWN,  # Event/State
            "Z": MeasuredVariable.POSITION
        }

        self.function_letter_map = {
            "E": InstrumentFunction.ELEMENT,
            "T": InstrumentFunction.TRANSMITTER,
            "I": InstrumentFunction.INDICATOR,
            "R": InstrumentFunction.RECORDER,
            "C": InstrumentFunction.CONTROLLER,
            "S": InstrumentFunction.SWITCH,
            "A": InstrumentFunction.ALARM,
            "V": InstrumentFunction.VALVE,
            "Y": InstrumentFunction.RELAY,
            "G": InstrumentFunction.UNKNOWN,  # Glass/Gauge
            "U": InstrumentFunction.UNKNOWN,  # Multifunctional
            "W": InstrumentFunction.UNKNOWN,  # Well
            "X": InstrumentFunction.UNKNOWN,  # Unclassified
            "Z": InstrumentFunction.UNKNOWN   # Safety/Position
        }

    def parse_tag(self, tag: str) -> Dict[str, any]:
        """
        Parse instrument tag according to ISA standards

        Args:
            tag: Instrument tag (e.g., FT-101, PT-2001A)

        Returns:
            Dictionary with parsed tag information
        """
        # Clean tag
        tag_clean = tag.upper().strip()

        # Extract tag components
        # Pattern: [Letters][Separator][Numbers][Loop/Suffix]
        pattern = r'^([A-Z]{2,4})[-_]?([0-9]{2,5})([A-Z]?)$'
        match = re.match(pattern, tag_clean)

        if not match:
            logger.warning(f"Tag {tag} does not match ISA pattern")
            return {
                "valid": False,
                "tag": tag,
                "measured_variable": MeasuredVariable.UNKNOWN,
                "function": InstrumentFunction.UNKNOWN
            }

        letters, number, suffix = match.groups()

        # Parse measured variable (first letter)
        first_letter = letters[0]
        measured_var = self.first_letter_map.get(
            first_letter,
            MeasuredVariable.UNKNOWN
        )

        # Parse function (subsequent letters)
        function_letters = letters[1:]
        function = InstrumentFunction.UNKNOWN

        if function_letters:
            # Try to match function from letters
            for letter in function_letters:
                func = self.function_letter_map.get(letter)
                if func and func != InstrumentFunction.UNKNOWN:
                    function = func
                    break

        # Generate description
        description = self._generate_description(
            measured_var,
            function,
            letters
        )

        return {
            "valid": True,
            "tag": tag,
            "letters": letters,
            "number": number,
            "suffix": suffix,
            "measured_variable": measured_var,
            "function": function,
            "description": description,
            "first_letter": first_letter,
            "function_letters": function_letters
        }

    def _generate_description(
        self,
        measured_var: MeasuredVariable,
        function: InstrumentFunction,
        tag_prefix: str
    ) -> str:
        """Generate service description from tag components"""

        # Special cases for common tags
        special_tags = {
            "FE": "Flow Element",
            "FT": "Flow Transmitter",
            "FC": "Flow Controller",
            "FI": "Flow Indicator",
            "FIC": "Flow Indicator Controller",
            "FRC": "Flow Recorder Controller",
            "PT": "Pressure Transmitter",
            "PI": "Pressure Indicator",
            "PC": "Pressure Controller",
            "PCV": "Pressure Control Valve",
            "PSV": "Pressure Safety Valve",
            "PSHH": "Pressure Switch High High",
            "PSL": "Pressure Switch Low",
            "PSLL": "Pressure Switch Low Low",
            "TT": "Temperature Transmitter",
            "TI": "Temperature Indicator",
            "TC": "Temperature Controller",
            "TE": "Temperature Element",
            "TCV": "Temperature Control Valve",
            "LT": "Level Transmitter",
            "LI": "Level Indicator",
            "LC": "Level Controller",
            "LE": "Level Element",
            "LAH": "Level Alarm High",
            "LAL": "Level Alarm Low",
            "LAHH": "Level Alarm High High",
            "LALL": "Level Alarm Low Low",
            "LSH": "Level Switch High",
            "LSL": "Level Switch Low",
            "AT": "Analytical Transmitter",
            "AI": "Analytical Indicator",
            "AE": "Analytical Element",
            "HS": "Hand Switch",
            "ZS": "Position Switch",
            "FS": "Flow Switch",
            "CV": "Control Valve",
            "HV": "Hand Valve",
            "MOV": "Motor Operated Valve",
            "SOV": "Solenoid Operated Valve"
        }

        if tag_prefix in special_tags:
            return special_tags[tag_prefix]

        # General description
        var_str = measured_var.value if measured_var != MeasuredVariable.UNKNOWN else ""
        func_str = function.value if function != InstrumentFunction.UNKNOWN else ""

        if var_str and func_str:
            return f"{var_str} {func_str}"
        elif var_str:
            return var_str
        elif func_str:
            return func_str
        else:
            return f"Instrument ({tag_prefix})"

    def create_instrument(
        self,
        tag: str,
        service_description: Optional[str] = None,
        **kwargs
    ) -> Instrument:
        """
        Create an instrument entry

        Args:
            tag: Instrument tag
            service_description: Service description (auto-generated if not provided)
            **kwargs: Additional instrument properties

        Returns:
            Instrument object
        """
        # Parse tag
        parsed = self.parse_tag(tag)

        # Use provided description or generate one
        if service_description:
            description = service_description
        else:
            description = parsed.get("description", "")

        # Create instrument
        instrument = Instrument(
            tag=tag,
            measured_variable=parsed.get("measured_variable", MeasuredVariable.UNKNOWN),
            function=parsed.get("function", InstrumentFunction.UNKNOWN),
            service_description=description,
            **kwargs
        )

        return instrument

    def generate_index_from_tags(
        self,
        tags: List[str],
        project_name: str,
        pid_reference: str,
        **kwargs
    ) -> InstrumentIndex:
        """
        Generate instrument index from list of tags

        Args:
            tags: List of instrument tags
            project_name: Project name
            pid_reference: P&ID reference
            **kwargs: Additional properties

        Returns:
            InstrumentIndex
        """
        index = InstrumentIndex(
            project_name=project_name,
            pid_reference=pid_reference
        )

        for tag in tags:
            # Skip if tag already exists
            if any(inst.tag == tag for inst in index.instruments):
                continue

            instrument = self.create_instrument(tag, **kwargs)
            index.instruments.append(instrument)

        # Sort instruments by tag
        index.instruments.sort(key=lambda x: x.tag)

        logger.info(f"Generated index with {len(index.instruments)} instruments")
        return index

    def enrich_instrument_data(
        self,
        instrument: Instrument,
        pid_text: str,
        equipment_data: Dict
    ) -> Instrument:
        """
        Enrich instrument data with additional information from P&ID

        Args:
            instrument: Instrument to enrich
            pid_text: Extracted text from P&ID
            equipment_data: Equipment and line data

        Returns:
            Enriched instrument
        """
        tag = instrument.tag

        # Try to find service information near the tag in P&ID text
        tag_pattern = re.escape(tag)
        context_pattern = f'{tag_pattern}[\\s\\S]{{0,100}}'

        matches = re.findall(context_pattern, pid_text, re.IGNORECASE)

        if matches:
            context = matches[0]

            # Extract potential service description
            # Look for common process fluids and services
            services = [
                "steam", "water", "condensate", "cooling", "process",
                "inlet", "outlet", "discharge", "suction", "supply",
                "return", "feed", "product", "recycle", "vent"
            ]

            for service in services:
                if service in context.lower():
                    if not instrument.service_description:
                        instrument.service_description = f"{instrument.service_description} - {service.title()}"

        # Extract location from equipment data if available
        if equipment_data and "location" in equipment_data:
            instrument.location = equipment_data["location"]

        return instrument

    def export_to_dict(self, index: InstrumentIndex) -> Dict:
        """Export instrument index to dictionary"""
        return {
            "project_name": index.project_name,
            "pid_reference": index.pid_reference,
            "revision": index.revision,
            "date": index.date.isoformat(),
            "instrument_count": len(index.instruments),
            "instruments": [
                {
                    "tag": inst.tag,
                    "measured_variable": inst.measured_variable.value,
                    "function": inst.function.value,
                    "service_description": inst.service_description,
                    "location": inst.location,
                    "pid_reference": inst.pid_reference,
                    "manufacturer": inst.manufacturer,
                    "model": inst.model,
                    "range_min": inst.range_min,
                    "range_max": inst.range_max,
                    "units": inst.units,
                    "signal_type": inst.signal_type,
                    "process_connection": inst.process_connection,
                    "material": inst.material,
                    "accuracy": inst.accuracy,
                    "notes": inst.notes,
                    "status": inst.status
                }
                for inst in index.instruments
            ]
        }

    def export_to_csv_data(self, index: InstrumentIndex) -> List[List[str]]:
        """Export instrument index to CSV format"""
        headers = [
            "Tag", "Measured Variable", "Function", "Service Description",
            "Location", "P&ID Reference", "Manufacturer", "Model",
            "Range Min", "Range Max", "Units", "Signal Type",
            "Process Connection", "Material", "Accuracy", "Status", "Notes"
        ]

        rows = [headers]

        for inst in index.instruments:
            row = [
                inst.tag,
                inst.measured_variable.value,
                inst.function.value,
                inst.service_description,
                inst.location,
                inst.pid_reference,
                inst.manufacturer or "",
                inst.model or "",
                str(inst.range_min) if inst.range_min else "",
                str(inst.range_max) if inst.range_max else "",
                inst.units or "",
                inst.signal_type or "",
                inst.process_connection or "",
                inst.material or "",
                inst.accuracy or "",
                inst.status,
                inst.notes or ""
            ]
            rows.append(row)

        return rows

    def filter_instruments(
        self,
        index: InstrumentIndex,
        measured_variable: Optional[MeasuredVariable] = None,
        function: Optional[InstrumentFunction] = None,
        location: Optional[str] = None
    ) -> List[Instrument]:
        """Filter instruments by criteria"""
        filtered = index.instruments

        if measured_variable:
            filtered = [i for i in filtered if i.measured_variable == measured_variable]

        if function:
            filtered = [i for i in filtered if i.function == function]

        if location:
            filtered = [i for i in filtered if location.lower() in i.location.lower()]

        return filtered

    def get_statistics(self, index: InstrumentIndex) -> Dict:
        """Get statistics about the instrument index"""
        stats = {
            "total_instruments": len(index.instruments),
            "by_measured_variable": {},
            "by_function": {},
            "by_status": {}
        }

        for inst in index.instruments:
            # Count by measured variable
            var_name = inst.measured_variable.value
            stats["by_measured_variable"][var_name] = \
                stats["by_measured_variable"].get(var_name, 0) + 1

            # Count by function
            func_name = inst.function.value
            stats["by_function"][func_name] = \
                stats["by_function"].get(func_name, 0) + 1

            # Count by status
            stats["by_status"][inst.status] = \
                stats["by_status"].get(inst.status, 0) + 1

        return stats
