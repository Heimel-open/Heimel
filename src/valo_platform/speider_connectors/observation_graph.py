"""Observation Graph

Models composed observations and correlations across entities and signals.
Enables temporal and causal reasoning about entity behavior and relationships.
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SignalRelationType(str, Enum):
    """Types of relationships between signals."""
    CORRELATED = "correlated"  # signals change together
    CAUSAL = "causal"  # signal A causes signal B
    CONFLICT = "conflict"  # signals contradict
    COMPOUND = "compound"  # aggregated from multiple signals
    SEQUENTIAL = "sequential"  # signals in temporal sequence


class RelationshipType(str, Enum):
    """Types of relationships between entities."""
    SHAREHOLDER = "shareholder"
    BOARD_MEMBER = "board_member"
    DIRECTOR = "director"
    EMPLOYEE = "employee"
    COUNTERPARTY = "counterparty"
    SUPPLIER = "supplier"
    CUSTOMER = "customer"
    COMPETITOR = "competitor"
    RELATED_ENTITY = "related_entity"


@dataclass
class Signal:
    """Observable signal from a connector."""
    signal_id: str
    signal_type: str  # "anomaly", "transaction", "grant", etc.
    entity_id: str  # what entity this signal is about
    source: str  # which connector
    value: any  # signal value
    confidence: float  # 0.0-1.0
    timestamp: datetime
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class SignalRelation:
    """Relationship between two signals."""
    relation_id: str
    signal_id_1: str
    signal_id_2: str
    relation_type: SignalRelationType
    strength: float  # 0.0-1.0
    explanation: Optional[str] = None
    discovered_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EntityRelation:
    """Relationship between entities."""
    relation_id: str
    entity_id_1: str
    entity_id_2: str
    relation_type: RelationshipType
    metadata: Dict[str, any] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=datetime.utcnow)


class ObservationGraph:
    """Graph of observations, signals, and relationships."""

    def __init__(self):
        """Initialize observation graph."""
        self.signals: Dict[str, Signal] = {}
        self.signal_relations: Dict[str, SignalRelation] = {}
        self.entity_relations: Dict[str, EntityRelation] = {}

        # Index for fast lookup
        self._signals_by_entity: Dict[str, Set[str]] = {}
        self._signals_by_type: Dict[str, Set[str]] = {}
        self._signals_by_source: Dict[str, Set[str]] = {}
        self._entities_with_relations: Dict[str, Set[str]] = {}

    def add_signal(self, signal: Signal) -> str:
        """Add signal to graph.

        Returns:
            Signal ID
        """
        self.signals[signal.signal_id] = signal

        # Update indices
        if signal.entity_id not in self._signals_by_entity:
            self._signals_by_entity[signal.entity_id] = set()
        self._signals_by_entity[signal.entity_id].add(signal.signal_id)

        if signal.signal_type not in self._signals_by_type:
            self._signals_by_type[signal.signal_type] = set()
        self._signals_by_type[signal.signal_type].add(signal.signal_id)

        if signal.source not in self._signals_by_source:
            self._signals_by_source[signal.source] = set()
        self._signals_by_source[signal.source].add(signal.signal_id)

        return signal.signal_id

    def add_signal_relation(self, relation: SignalRelation) -> str:
        """Add relationship between signals."""
        self.signal_relations[relation.relation_id] = relation
        return relation.relation_id

    def add_entity_relation(self, relation: EntityRelation) -> str:
        """Add relationship between entities."""
        self.entity_relations[relation.relation_id] = relation

        # Update entity relations index
        for entity_id in [relation.entity_id_1, relation.entity_id_2]:
            if entity_id not in self._entities_with_relations:
                self._entities_with_relations[entity_id] = set()

        self._entities_with_relations[relation.entity_id_1].add(relation.entity_id_2)
        self._entities_with_relations[relation.entity_id_2].add(relation.entity_id_1)

        return relation.relation_id

    def get_entity_signals(self, entity_id: str) -> List[Signal]:
        """Get all signals for an entity."""
        signal_ids = self._signals_by_entity.get(entity_id, set())
        return [self.signals[sid] for sid in signal_ids]

    def get_signals_by_type(self, signal_type: str) -> List[Signal]:
        """Get all signals of a type."""
        signal_ids = self._signals_by_type.get(signal_type, set())
        return [self.signals[sid] for sid in signal_ids]

    def get_signals_by_source(self, source: str) -> List[Signal]:
        """Get all signals from a source."""
        signal_ids = self._signals_by_source.get(source, set())
        return [self.signals[sid] for sid in signal_ids]

    def get_signal(self, signal_id: str) -> Optional[Signal]:
        """Get signal by ID."""
        return self.signals.get(signal_id)

    def get_related_entities(self, entity_id: str) -> List[Tuple[str, RelationshipType]]:
        """Get entities related to this entity."""
        related = self._entities_with_relations.get(entity_id, set())
        result = []

        for related_entity_id in related:
            # Find the relation
            for rel in self.entity_relations.values():
                if (rel.entity_id_1 == entity_id and rel.entity_id_2 == related_entity_id) or \
                   (rel.entity_id_2 == entity_id and rel.entity_id_1 == related_entity_id):
                    result.append((related_entity_id, rel.relation_type))
                    break

        return result

    def find_signal_correlations(self, signal_id: str) -> List[SignalRelation]:
        """Find all relations involving a signal."""
        correlations = []
        for rel in self.signal_relations.values():
            if rel.signal_id_1 == signal_id or rel.signal_id_2 == signal_id:
                correlations.append(rel)
        return correlations

    def get_entity_graph(self, entity_id: str, depth: int = 2) -> Dict[str, any]:
        """Get entity subgraph (entity + related entities + depth levels).

        Args:
            entity_id: Starting entity
            depth: How many relationship hops to include

        Returns:
            Subgraph with entities, relations, and signals
        """
        visited = set()
        to_visit = {(entity_id, 0)}
        entities = {}
        relations = []

        while to_visit:
            current_id, current_depth = to_visit.pop()

            if current_id in visited:
                continue
            visited.add(current_id)

            # Get signals for this entity
            entity_signals = self.get_entity_signals(current_id)
            entities[current_id] = {
                "entity_id": current_id,
                "signal_count": len(entity_signals),
                "signals": [
                    {
                        "signal_id": s.signal_id,
                        "signal_type": s.signal_type,
                        "value": s.value,
                        "confidence": s.confidence,
                        "timestamp": s.timestamp.isoformat(),
                    }
                    for s in entity_signals
                ],
            }

            # Get related entities
            if current_depth < depth:
                for related_id, rel_type in self.get_related_entities(current_id):
                    to_visit.add((related_id, current_depth + 1))
                    relations.append({
                        "entity_1": current_id,
                        "entity_2": related_id,
                        "relation_type": rel_type.value,
                    })

        return {
            "root_entity": entity_id,
            "entity_count": len(entities),
            "entities": entities,
            "relation_count": len(relations),
            "relations": relations,
        }

    def detect_anomalous_patterns(self, entity_id: str) -> List[Dict[str, any]]:
        """Detect anomalous patterns in entity signals.

        Returns:
            List of detected patterns
        """
        signals = self.get_entity_signals(entity_id)

        patterns = []

        # Pattern 1: High-confidence signals from multiple sources
        sources_seen = {}
        for signal in signals:
            if signal.confidence > 0.8:
                if signal.signal_type not in sources_seen:
                    sources_seen[signal.signal_type] = set()
                sources_seen[signal.signal_type].add(signal.source)

        for signal_type, sources in sources_seen.items():
            if len(sources) >= 2:
                patterns.append({
                    "pattern_type": "multi_source_agreement",
                    "signal_type": signal_type,
                    "source_count": len(sources),
                    "sources": list(sources),
                    "significance": "confirmed observation from multiple sources",
                })

        # Pattern 2: Conflicting signals
        for i, sig1 in enumerate(signals):
            for sig2 in signals[i + 1:]:
                if sig1.signal_type == sig2.signal_type:
                    if sig1.value != sig2.value:
                        patterns.append({
                            "pattern_type": "conflicting_signals",
                            "signal_type": sig1.signal_type,
                            "source_1": sig1.source,
                            "source_2": sig2.source,
                            "significance": "data inconsistency between sources",
                        })

        # Pattern 3: Temporal clustering
        if len(signals) > 2:
            sorted_signals = sorted(signals, key=lambda s: s.timestamp)
            for i in range(len(sorted_signals) - 1):
                time_diff = (sorted_signals[i + 1].timestamp - sorted_signals[i].timestamp).total_seconds()
                if time_diff < 3600:  # Within 1 hour
                    patterns.append({
                        "pattern_type": "temporal_cluster",
                        "signals": 2,
                        "time_window_seconds": time_diff,
                        "significance": "multiple signals in short time window",
                    })

        return patterns

    def get_graph_statistics(self) -> Dict[str, any]:
        """Get graph statistics."""
        return {
            "total_signals": len(self.signals),
            "total_signal_relations": len(self.signal_relations),
            "total_entity_relations": len(self.entity_relations),
            "signals_by_type": {k: len(v) for k, v in self._signals_by_type.items()},
            "signals_by_source": {k: len(v) for k, v in self._signals_by_source.items()},
            "entities_with_signals": len(self._signals_by_entity),
            "entities_with_relations": len(self._entities_with_relations),
        }
