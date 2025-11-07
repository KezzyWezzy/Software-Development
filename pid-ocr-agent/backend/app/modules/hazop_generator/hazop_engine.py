"""
HAZOP (Hazard and Operability Study) Generation Engine
Automatically generates HAZOP studies from P&ID analysis
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Severity levels for risk assessment"""
    NEGLIGIBLE = 1
    MINOR = 2
    MODERATE = 3
    MAJOR = 4
    CATASTROPHIC = 5


class Likelihood(Enum):
    """Likelihood levels for risk assessment"""
    RARE = 1
    UNLIKELY = 2
    POSSIBLE = 3
    LIKELY = 4
    ALMOST_CERTAIN = 5


@dataclass
class GuideWord:
    """HAZOP Guide Word"""
    word: str
    meaning: str
    applicable_parameters: List[str]


@dataclass
class ProcessParameter:
    """Process parameter for HAZOP analysis"""
    name: str
    normal_value: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None


@dataclass
class HAZOPDeviation:
    """HAZOP Deviation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    guide_word: str = ""
    parameter: str = ""
    deviation: str = ""
    possible_causes: List[str] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)
    safeguards: List[str] = field(default_factory=list)
    severity: Optional[Severity] = None
    likelihood: Optional[Likelihood] = None
    risk_ranking: Optional[int] = None
    recommendations: List[str] = field(default_factory=list)
    action_party: Optional[str] = None
    target_date: Optional[datetime] = None


@dataclass
class HAZOPNode:
    """HAZOP Study Node"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_number: str = ""
    node_description: str = ""
    design_intent: str = ""
    equipment_list: List[str] = field(default_factory=list)
    instrument_list: List[str] = field(default_factory=list)
    deviations: List[HAZOPDeviation] = field(default_factory=list)


@dataclass
class HAZOPStudy:
    """Complete HAZOP Study"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_name: str = ""
    pid_reference: str = ""
    study_date: datetime = field(default_factory=datetime.now)
    revision: str = "0"
    nodes: List[HAZOPNode] = field(default_factory=list)
    team_members: List[str] = field(default_factory=list)
    methodology: str = "Standard HAZOP"
    status: str = "Draft"


class HAZOPEngine:
    """
    Engine for automated HAZOP study generation
    """

    def __init__(self):
        """Initialize HAZOP engine with standard guide words and templates"""
        self.guide_words = self._initialize_guide_words()
        self.parameters = self._initialize_parameters()
        self.cause_templates = self._initialize_cause_templates()
        self.consequence_templates = self._initialize_consequence_templates()
        self.safeguard_templates = self._initialize_safeguard_templates()

    def _initialize_guide_words(self) -> List[GuideWord]:
        """Initialize standard HAZOP guide words"""
        return [
            GuideWord(
                word="NO/NONE",
                meaning="Complete negation of design intent",
                applicable_parameters=["FLOW", "PRESSURE", "TEMPERATURE", "LEVEL", "COMPOSITION"]
            ),
            GuideWord(
                word="MORE",
                meaning="Quantitative increase",
                applicable_parameters=["FLOW", "PRESSURE", "TEMPERATURE", "LEVEL", "CONCENTRATION"]
            ),
            GuideWord(
                word="LESS",
                meaning="Quantitative decrease",
                applicable_parameters=["FLOW", "PRESSURE", "TEMPERATURE", "LEVEL", "CONCENTRATION"]
            ),
            GuideWord(
                word="AS WELL AS",
                meaning="Qualitative increase (additional activity)",
                applicable_parameters=["COMPOSITION", "PHASE", "IMPURITIES"]
            ),
            GuideWord(
                word="PART OF",
                meaning="Qualitative decrease (missing component)",
                applicable_parameters=["COMPOSITION", "CONCENTRATION"]
            ),
            GuideWord(
                word="REVERSE",
                meaning="Logical opposite of intent",
                applicable_parameters=["FLOW", "REACTION", "ROTATION"]
            ),
            GuideWord(
                word="OTHER THAN",
                meaning="Complete substitution",
                applicable_parameters=["COMPOSITION", "ACTIVITY", "SERVICE"]
            ),
            GuideWord(
                word="EARLY",
                meaning="Timing too soon",
                applicable_parameters=["SEQUENCE", "TIME"]
            ),
            GuideWord(
                word="LATE",
                meaning="Timing too late",
                applicable_parameters=["SEQUENCE", "TIME"]
            ),
            GuideWord(
                word="BEFORE",
                meaning="Wrong sequence (too early)",
                applicable_parameters=["SEQUENCE"]
            ),
            GuideWord(
                word="AFTER",
                meaning="Wrong sequence (too late)",
                applicable_parameters=["SEQUENCE"]
            )
        ]

    def _initialize_parameters(self) -> List[ProcessParameter]:
        """Initialize standard process parameters"""
        return [
            ProcessParameter("FLOW", description="Rate of material flow"),
            ProcessParameter("PRESSURE", unit="psig", description="System pressure"),
            ProcessParameter("TEMPERATURE", unit="°F", description="Process temperature"),
            ProcessParameter("LEVEL", unit="%", description="Liquid level"),
            ProcessParameter("COMPOSITION", description="Material composition"),
            ProcessParameter("PH", description="Acidity/alkalinity"),
            ProcessParameter("VISCOSITY", description="Fluid viscosity"),
            ProcessParameter("CONCENTRATION", description="Component concentration"),
            ProcessParameter("PHASE", description="Material phase (solid/liquid/gas)"),
            ProcessParameter("REACTION", description="Chemical reaction"),
            ProcessParameter("SEPARATION", description="Phase separation"),
            ProcessParameter("MIXING", description="Material mixing"),
            ProcessParameter("TIME", description="Process timing"),
            ProcessParameter("SEQUENCE", description="Operation sequence")
        ]

    def _initialize_cause_templates(self) -> Dict[str, List[str]]:
        """Initialize cause templates for common deviations"""
        return {
            "NO FLOW": [
                "Pump failure",
                "Valve closed inadvertently",
                "Line blockage",
                "Upstream vessel empty",
                "Power failure",
                "Instrument failure",
                "Operator error"
            ],
            "MORE FLOW": [
                "Control valve fails open",
                "Valve opened too much",
                "Pump running at excessive speed",
                "Upstream pressure increase",
                "Downstream pressure decrease",
                "Control system malfunction"
            ],
            "LESS FLOW": [
                "Partial line blockage",
                "Pump wear/degradation",
                "Control valve partially closed",
                "Upstream pressure drop",
                "Downstream pressure increase",
                "Viscosity increase"
            ],
            "MORE PRESSURE": [
                "Downstream valve closed",
                "Relief valve failure",
                "Thermal expansion",
                "Control valve fails closed",
                "Pump dead-heading",
                "External fire"
            ],
            "LESS PRESSURE": [
                "Leak in system",
                "Relief valve opens",
                "Vapor lock",
                "Upstream pressure drop",
                "Control failure"
            ],
            "MORE TEMPERATURE": [
                "Heat exchanger fouling",
                "Cooling failure",
                "External fire",
                "Exothermic reaction",
                "Hot recycle",
                "Heat tracing malfunction"
            ],
            "LESS TEMPERATURE": [
                "Loss of heating",
                "Endothermic reaction",
                "Cold feed",
                "Excessive cooling",
                "Heat exchanger failure"
            ],
            "MORE LEVEL": [
                "Inlet flow increase",
                "Outlet flow decrease",
                "Level control failure",
                "Downstream blockage",
                "Foaming"
            ],
            "LESS LEVEL": [
                "Inlet flow decrease",
                "Outlet flow increase",
                "Leak in vessel",
                "Level control failure",
                "Vortexing"
            ],
            "REVERSE FLOW": [
                "Pressure reversal",
                "Check valve failure",
                "Siphoning",
                "Pump reversal",
                "Valve lineup error"
            ]
        }

    def _initialize_consequence_templates(self) -> Dict[str, List[str]]:
        """Initialize consequence templates"""
        return {
            "NO FLOW": [
                "Process shutdown",
                "Equipment damage due to dead-heading",
                "Loss of cooling leading to temperature rise",
                "Reactor runaway",
                "Product quality deviation"
            ],
            "MORE FLOW": [
                "Vessel overflow",
                "Equipment flooding",
                "Downstream equipment overload",
                "Loss of containment",
                "Off-spec product"
            ],
            "LESS FLOW": [
                "Insufficient cooling",
                "Temperature excursion",
                "Incomplete reaction",
                "Equipment overheating",
                "Product off-spec"
            ],
            "MORE PRESSURE": [
                "Equipment overpressure",
                "Vessel rupture",
                "Relief valve lift",
                "Flange leak",
                "Piping failure",
                "Personnel injury",
                "Environmental release"
            ],
            "LESS PRESSURE": [
                "Loss of containment",
                "Vapor formation",
                "Pump cavitation",
                "Air ingress",
                "Contamination"
            ],
            "MORE TEMPERATURE": [
                "Equipment damage",
                "Material degradation",
                "Runaway reaction",
                "Fire/explosion",
                "Toxic release",
                "Personnel injury"
            ],
            "LESS TEMPERATURE": [
                "Freezing",
                "Solidification",
                "Incomplete reaction",
                "Wax formation",
                "Viscosity increase"
            ],
            "MORE LEVEL": [
                "Vessel overflow",
                "Loss of containment",
                "Liquid carryover",
                "Equipment damage",
                "Environmental release"
            ],
            "LESS LEVEL": [
                "Loss of NPSH",
                "Pump cavitation",
                "Vortexing",
                "Gas blowby",
                "Process upset"
            ],
            "REVERSE FLOW": [
                "Equipment damage",
                "Contamination",
                "Loss of containment",
                "Process upset",
                "Off-spec product"
            ]
        }

    def _initialize_safeguard_templates(self) -> Dict[str, List[str]]:
        """Initialize safeguard templates"""
        return {
            "NO FLOW": [
                "Low flow alarm (FAL)",
                "Pump status indication",
                "Backup pump",
                "Flow switch",
                "Operator rounds"
            ],
            "MORE FLOW": [
                "High flow alarm (FAH)",
                "Flow control valve",
                "High level alarm on downstream vessel",
                "Overflow protection"
            ],
            "LESS FLOW": [
                "Low flow alarm (FAL)",
                "Minimum flow recirculation",
                "Flow indication",
                "Operating procedures"
            ],
            "MORE PRESSURE": [
                "Pressure relief valve (PSV)",
                "High pressure alarm (PAH)",
                "Pressure indicator",
                "Rupture disk",
                "Emergency shutdown system"
            ],
            "LESS PRESSURE": [
                "Low pressure alarm (PAL)",
                "Check valve",
                "Pressure indicator",
                "Operating procedures"
            ],
            "MORE TEMPERATURE": [
                "High temperature alarm (TAH)",
                "Temperature interlock",
                "Cooling system",
                "Relief valve",
                "Emergency cooling"
            ],
            "LESS TEMPERATURE": [
                "Low temperature alarm (TAL)",
                "Temperature control",
                "Heat tracing",
                "Insulation"
            ],
            "MORE LEVEL": [
                "High level alarm (LAH)",
                "High-high level alarm (LAHH)",
                "Overflow line",
                "Level control",
                "Automatic shutdown"
            ],
            "LESS LEVEL": [
                "Low level alarm (LAL)",
                "Low-low level alarm (LALL)",
                "Pump trip on low level",
                "Level indicator"
            ],
            "REVERSE FLOW": [
                "Check valve",
                "Flow indication",
                "Interlocks",
                "Operating procedures"
            ]
        }

    def generate_deviation_description(
        self,
        guide_word: str,
        parameter: str
    ) -> str:
        """Generate deviation description from guide word and parameter"""
        return f"{guide_word} {parameter}".upper()

    def generate_deviations(
        self,
        node: HAZOPNode,
        parameters: Optional[List[str]] = None
    ) -> List[HAZOPDeviation]:
        """
        Generate deviations for a node

        Args:
            node: HAZOP node
            parameters: List of parameters to analyze (default: all)

        Returns:
            List of deviations
        """
        if parameters is None:
            parameters = [p.name for p in self.parameters]

        deviations = []

        for guide_word_obj in self.guide_words:
            guide_word = guide_word_obj.word

            for parameter in parameters:
                # Check if guide word is applicable to parameter
                if parameter not in guide_word_obj.applicable_parameters:
                    continue

                deviation_desc = self.generate_deviation_description(
                    guide_word, parameter
                )

                # Get causes, consequences, and safeguards from templates
                causes = self.cause_templates.get(deviation_desc, [
                    f"Equipment failure affecting {parameter.lower()}",
                    f"Instrumentation failure",
                    f"Operator error",
                    f"Control system malfunction"
                ])

                consequences = self.consequence_templates.get(deviation_desc, [
                    f"Process upset",
                    f"Equipment damage",
                    f"Safety hazard",
                    f"Environmental impact"
                ])

                safeguards = self.safeguard_templates.get(deviation_desc, [
                    f"Alarms and indication",
                    f"Operating procedures",
                    f"Operator training"
                ])

                # Calculate risk
                severity, likelihood, risk_ranking = self.assess_risk(
                    consequences,
                    safeguards
                )

                # Generate recommendations
                recommendations = self.generate_recommendations(
                    deviation_desc,
                    risk_ranking,
                    safeguards
                )

                deviation = HAZOPDeviation(
                    guide_word=guide_word,
                    parameter=parameter,
                    deviation=deviation_desc,
                    possible_causes=causes[:3],  # Top 3 causes
                    consequences=consequences[:3],  # Top 3 consequences
                    safeguards=safeguards[:3],  # Top 3 safeguards
                    severity=severity,
                    likelihood=likelihood,
                    risk_ranking=risk_ranking,
                    recommendations=recommendations
                )

                deviations.append(deviation)

        logger.info(f"Generated {len(deviations)} deviations for node {node.node_number}")
        return deviations

    def assess_risk(
        self,
        consequences: List[str],
        safeguards: List[str]
    ) -> Tuple[Severity, Likelihood, int]:
        """
        Assess risk level based on consequences and safeguards

        Returns:
            Tuple of (severity, likelihood, risk_ranking)
        """
        # Simple risk assessment logic
        # In production, this would be more sophisticated

        # Determine severity based on consequences
        severity_keywords = {
            Severity.CATASTROPHIC: ["death", "fatality", "explosion", "major fire", "rupture"],
            Severity.MAJOR: ["injury", "release", "damage", "fire", "environmental"],
            Severity.MODERATE: ["minor injury", "upset", "shutdown", "off-spec"],
            Severity.MINOR: ["nuisance", "delay"],
            Severity.NEGLIGIBLE: []
        }

        severity = Severity.MODERATE  # Default

        consequence_text = " ".join(consequences).lower()
        for sev_level, keywords in severity_keywords.items():
            if any(keyword in consequence_text for keyword in keywords):
                severity = sev_level
                break

        # Determine likelihood based on number of safeguards
        num_safeguards = len(safeguards)

        if num_safeguards >= 3:
            likelihood = Likelihood.UNLIKELY
        elif num_safeguards == 2:
            likelihood = Likelihood.POSSIBLE
        elif num_safeguards == 1:
            likelihood = Likelihood.LIKELY
        else:
            likelihood = Likelihood.ALMOST_CERTAIN

        # Calculate risk ranking (severity × likelihood)
        risk_ranking = severity.value * likelihood.value

        return severity, likelihood, risk_ranking

    def generate_recommendations(
        self,
        deviation: str,
        risk_ranking: int,
        existing_safeguards: List[str]
    ) -> List[str]:
        """Generate recommendations based on risk level"""
        recommendations = []

        # High risk (>12)
        if risk_ranking >= 12:
            recommendations.append("Install additional independent protection layer")
            recommendations.append("Implement automatic shutdown system")
            recommendations.append("Review and enhance operator training")

        # Medium risk (6-12)
        elif risk_ranking >= 6:
            recommendations.append("Install high/low alarm if not present")
            recommendations.append("Update operating procedures")
            recommendations.append("Consider additional safeguards")

        # Low risk (<6)
        else:
            recommendations.append("Verify existing safeguards are adequate")
            recommendations.append("Include in operator training")

        # Check for missing common safeguards
        safeguard_text = " ".join(existing_safeguards).lower()

        if "alarm" not in safeguard_text:
            recommendations.append("Consider installing alarm for early detection")

        if "procedure" not in safeguard_text:
            recommendations.append("Develop operating procedure for this scenario")

        return recommendations[:3]  # Return top 3 recommendations

    def create_node_from_equipment(
        self,
        node_number: str,
        equipment_list: List[str],
        instrument_list: List[str],
        design_intent: str
    ) -> HAZOPNode:
        """Create a HAZOP node from equipment and instrument lists"""
        node = HAZOPNode(
            node_number=node_number,
            node_description=f"Node {node_number}: {', '.join(equipment_list[:3])}",
            design_intent=design_intent,
            equipment_list=equipment_list,
            instrument_list=instrument_list
        )

        # Generate deviations for this node
        node.deviations = self.generate_deviations(node)

        return node

    def generate_hazop_study(
        self,
        project_name: str,
        pid_reference: str,
        nodes_data: List[Dict],
        team_members: Optional[List[str]] = None
    ) -> HAZOPStudy:
        """
        Generate complete HAZOP study

        Args:
            project_name: Project name
            pid_reference: P&ID reference number
            nodes_data: List of node data dictionaries
            team_members: List of team member names

        Returns:
            Complete HAZOP study
        """
        study = HAZOPStudy(
            project_name=project_name,
            pid_reference=pid_reference,
            team_members=team_members or []
        )

        for node_data in nodes_data:
            node = self.create_node_from_equipment(
                node_number=node_data.get("node_number", ""),
                equipment_list=node_data.get("equipment", []),
                instrument_list=node_data.get("instruments", []),
                design_intent=node_data.get("design_intent", "")
            )

            study.nodes.append(node)

        logger.info(f"Generated HAZOP study with {len(study.nodes)} nodes")
        return study

    def export_hazop_to_dict(self, study: HAZOPStudy) -> Dict:
        """Export HAZOP study to dictionary format"""
        return {
            "id": study.id,
            "project_name": study.project_name,
            "pid_reference": study.pid_reference,
            "study_date": study.study_date.isoformat(),
            "revision": study.revision,
            "methodology": study.methodology,
            "status": study.status,
            "team_members": study.team_members,
            "nodes": [
                {
                    "id": node.id,
                    "node_number": node.node_number,
                    "node_description": node.node_description,
                    "design_intent": node.design_intent,
                    "equipment_list": node.equipment_list,
                    "instrument_list": node.instrument_list,
                    "deviations": [
                        {
                            "id": dev.id,
                            "guide_word": dev.guide_word,
                            "parameter": dev.parameter,
                            "deviation": dev.deviation,
                            "possible_causes": dev.possible_causes,
                            "consequences": dev.consequences,
                            "safeguards": dev.safeguards,
                            "severity": dev.severity.name if dev.severity else None,
                            "likelihood": dev.likelihood.name if dev.likelihood else None,
                            "risk_ranking": dev.risk_ranking,
                            "recommendations": dev.recommendations
                        }
                        for dev in node.deviations
                    ]
                }
                for node in study.nodes
            ]
        }
