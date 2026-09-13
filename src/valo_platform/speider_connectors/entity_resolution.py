"""Entity Resolution Engine

Identifies and resolves entities across multiple data sources.
Maps entities from different connectors to canonical representations.
"""

from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import hashlib


@dataclass
class EntitySignature:
    """Signature for entity matching."""
    entity_type: str  # "company", "person", "role"
    primary_id: str  # org_number, person_id, etc.
    source: str  # connector source name
    name: Optional[str] = None
    additional_attrs: Dict[str, any] = field(default_factory=dict)

    def canonical_key(self) -> str:
        """Generate canonical key for deduplication."""
        key_parts = [self.entity_type, self.name or "", self.source]
        key_str = "|".join(str(p) for p in key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()[:16]


@dataclass
class EntityCluster:
    """Cluster of equivalent entities across sources."""
    cluster_id: str
    entity_type: str
    primary_entity: EntitySignature  # canonical representation
    equivalent_entities: List[EntitySignature] = field(default_factory=list)
    confidence: float = 0.0  # 0.0-1.0
    matching_fields: List[str] = field(default_factory=list)  # fields that matched
    created_at: datetime = field(default_factory=datetime.utcnow)


class EntityResolutionEngine:
    """Resolves entities across multiple data sources."""

    def __init__(self):
        """Initialize entity resolution engine."""
        self.clusters: Dict[str, EntityCluster] = {}
        self.signature_to_cluster: Dict[str, str] = {}
        self._similarity_cache: Dict[Tuple[str, str], float] = {}

    def add_entity(self, signature: EntitySignature) -> str:
        """Add entity and find/create cluster.

        Returns:
            Cluster ID
        """
        canonical_key = signature.canonical_key()

        # Check if entity already in a cluster
        if canonical_key in self.signature_to_cluster:
            cluster_id = self.signature_to_cluster[canonical_key]
            cluster = self.clusters[cluster_id]
            cluster.equivalent_entities.append(signature)
            return cluster_id

        # Try to find similar entities in existing clusters
        best_match_cluster_id = None
        best_similarity = 0.0
        best_matching_fields = []

        for cluster_id, cluster in self.clusters.items():
            if cluster.entity_type != signature.entity_type:
                continue

            # Compare with primary entity
            similarity, matching_fields = self._compare_entities(
                signature,
                cluster.primary_entity,
            )

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_cluster_id = cluster_id
                best_matching_fields = matching_fields

        # Threshold for entity matching (>0.6 = likely same entity)
        if best_similarity > 0.6:
            cluster = self.clusters[best_match_cluster_id]
            cluster.equivalent_entities.append(signature)
            cluster.confidence = max(cluster.confidence, best_similarity)
            cluster.matching_fields = list(set(cluster.matching_fields + best_matching_fields))
            self.signature_to_cluster[canonical_key] = best_match_cluster_id
            return best_match_cluster_id

        # Create new cluster
        cluster_id = f"CLUSTER-{len(self.clusters)}"
        cluster = EntityCluster(
            cluster_id=cluster_id,
            entity_type=signature.entity_type,
            primary_entity=signature,
            confidence=1.0,
        )
        self.clusters[cluster_id] = cluster
        self.signature_to_cluster[canonical_key] = cluster_id

        return cluster_id

    def _compare_entities(
        self,
        entity1: EntitySignature,
        entity2: EntitySignature,
    ) -> Tuple[float, List[str]]:
        """Compare two entities for similarity.

        Returns:
            (similarity_score, list_of_matching_fields)
        """
        cache_key = (entity1.canonical_key(), entity2.canonical_key())
        if cache_key in self._similarity_cache:
            # Return cached score but recompute matching fields
            similarity = self._similarity_cache[cache_key]
            matching_fields = self._get_matching_fields(entity1, entity2)
            return similarity, matching_fields

        matching_fields = self._get_matching_fields(entity1, entity2)
        total_fields = 3  # type, name, source (at minimum)

        # Score: (matching_fields / total_fields)
        similarity = len(matching_fields) / total_fields

        self._similarity_cache[cache_key] = similarity
        return similarity, matching_fields

    def _get_matching_fields(self, entity1: EntitySignature, entity2: EntitySignature) -> List[str]:
        """Get list of fields that match between entities."""
        matching = []

        if entity1.entity_type == entity2.entity_type:
            matching.append("entity_type")

        # Primary ID match (strong signal) - only if from same source
        if entity1.primary_id == entity2.primary_id and entity1.source == entity2.source:
            matching.append("primary_id")
            return matching  # If primary ID matches, that's sufficient

        # Name matching (fuzzy) - only if primary IDs don't match
        if entity1.name and entity2.name:
            if self._fuzzy_match(entity1.name, entity2.name) > 0.9:
                matching.append("name")

        # Additional attributes
        for key in entity1.additional_attrs:
            if key in entity2.additional_attrs:
                if entity1.additional_attrs[key] == entity2.additional_attrs[key]:
                    matching.append(f"attr_{key}")

        return matching

    def _fuzzy_match(self, str1: str, str2: str) -> float:
        """Simple fuzzy string matching score."""
        s1 = str1.lower().strip()
        s2 = str2.lower().strip()

        if s1 == s2:
            return 1.0

        # Check if one contains the other (common pattern)
        if s1 in s2 or s2 in s1:
            return 0.85

        # Levenshtein-like distance (simplified)
        common_chars = set(s1) & set(s2)
        if len(s1) == 0 or len(s2) == 0:
            return 0.0

        similarity = len(common_chars) / max(len(s1), len(s2))
        return similarity

    def get_cluster(self, cluster_id: str) -> Optional[EntityCluster]:
        """Get entity cluster by ID."""
        return self.clusters.get(cluster_id)

    def find_cluster_for_entity(self, signature: EntitySignature) -> Optional[EntityCluster]:
        """Find cluster for an entity signature."""
        canonical_key = signature.canonical_key()
        cluster_id = self.signature_to_cluster.get(canonical_key)
        if cluster_id:
            return self.clusters[cluster_id]
        return None

    def get_canonical_entity(self, signature: EntitySignature) -> Optional[EntitySignature]:
        """Get canonical representation of an entity."""
        cluster = self.find_cluster_for_entity(signature)
        if cluster:
            return cluster.primary_entity
        return None

    def list_clusters(self, entity_type: Optional[str] = None, min_confidence: float = 0.0) -> List[EntityCluster]:
        """List entity clusters."""
        clusters = []
        for cluster in self.clusters.values():
            if entity_type and cluster.entity_type != entity_type:
                continue
            if cluster.confidence >= min_confidence:
                clusters.append(cluster)
        return clusters

    def merge_clusters(self, cluster_id1: str, cluster_id2: str) -> str:
        """Manually merge two clusters.

        Returns:
            Merged cluster ID
        """
        if cluster_id1 not in self.clusters or cluster_id2 not in self.clusters:
            raise ValueError("Invalid cluster IDs")

        cluster1 = self.clusters[cluster_id1]
        cluster2 = self.clusters[cluster_id2]

        if cluster1.entity_type != cluster2.entity_type:
            raise ValueError("Cannot merge clusters of different entity types")

        # Merge cluster2 into cluster1
        cluster1.equivalent_entities.extend(cluster2.equivalent_entities)
        cluster1.confidence = max(cluster1.confidence, cluster2.confidence)
        cluster1.matching_fields = list(set(cluster1.matching_fields + cluster2.matching_fields))

        # Update mappings
        for signature in cluster2.equivalent_entities:
            self.signature_to_cluster[signature.canonical_key()] = cluster_id1

        # Remove cluster2
        del self.clusters[cluster_id2]

        return cluster_id1

    def get_resolution_stats(self) -> Dict[str, any]:
        """Get entity resolution statistics."""
        stats = {
            "total_clusters": len(self.clusters),
            "total_entities": sum(
                1 + len(c.equivalent_entities) for c in self.clusters.values()
            ),
            "by_type": {},
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
        }

        for cluster in self.clusters.values():
            entity_type = cluster.entity_type
            if entity_type not in stats["by_type"]:
                stats["by_type"][entity_type] = {"clusters": 0, "entities": 0}

            stats["by_type"][entity_type]["clusters"] += 1
            stats["by_type"][entity_type]["entities"] += 1 + len(cluster.equivalent_entities)

            if cluster.confidence >= 0.9:
                stats["high_confidence"] += 1
            elif cluster.confidence >= 0.7:
                stats["medium_confidence"] += 1
            else:
                stats["low_confidence"] += 1

        return stats
