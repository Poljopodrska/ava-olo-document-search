"""
Information Relevance Hierarchy System - Constitutional Amendment #13
Manages the three-tier information priority system

Constitutional compliance:
- Privacy-first: Farmer data never leaves system
- LLM-first: All decisions made by AI, not hardcoded
- Transparency: Full audit trail of information sources
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import IntEnum
import logging
from datetime import datetime
import hashlib
import json

# Import from agricultural-core where these are now located
# In production, this would be:
# from ava_olo_agricultural_core.core.localization_handler import InformationRelevance, InformationItem, LocalizationContext
# For now, we'll define minimal versions here to avoid circular dependencies

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

class InformationRelevance(Enum):
    """Information relevance hierarchy as per Constitutional Amendment #13"""
    FARMER_SPECIFIC = "FARMER"
    COUNTRY_SPECIFIC = "COUNTRY"
    GLOBAL = "GLOBAL"

@dataclass
class InformationItem:
    """Represents a piece of information with its relevance level"""
    content: str
    relevance: InformationRelevance
    farmer_id: Optional[int] = None
    country_code: Optional[str] = None
    language: Optional[str] = None
    source_type: str = "unknown"
    metadata: Optional[Dict] = None

@dataclass
class LocalizationContext:
    """Context for localization decisions"""
    whatsapp_number: str
    country_code: str
    country_name: str
    languages: List[str]
    farmer_id: Optional[int] = None
    preferred_language: Optional[str] = None
    timezone: Optional[str] = None
    agricultural_zones: Optional[List[str]] = None

logger = logging.getLogger(__name__)


class RelevancePriority(IntEnum):
    """Priority levels for information relevance"""
    FARMER_SPECIFIC = 1    # Highest priority
    COUNTRY_SPECIFIC = 2   # Medium priority  
    GLOBAL = 3            # Lowest priority


@dataclass
class InformationSource:
    """Represents a source of information with metadata"""
    source_id: str
    source_type: str  # 'database', 'rag', 'external', 'cache'
    source_name: str
    can_access_farmer_data: bool = False
    can_access_country_data: bool = True
    can_access_global_data: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InformationQuery:
    """Query for information with context"""
    query_text: str
    context: LocalizationContext
    required_relevance_levels: List[InformationRelevance] = field(
        default_factory=lambda: [
            InformationRelevance.FARMER_SPECIFIC,
            InformationRelevance.COUNTRY_SPECIFIC,
            InformationRelevance.GLOBAL
        ]
    )
    max_items_per_level: int = 5
    include_metadata: bool = True


@dataclass
class InformationResult:
    """Result of information query with hierarchy"""
    query: InformationQuery
    farmer_items: List[InformationItem] = field(default_factory=list)
    country_items: List[InformationItem] = field(default_factory=list)
    global_items: List[InformationItem] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_all_items_by_priority(self) -> List[InformationItem]:
        """Get all items sorted by relevance priority"""
        return self.farmer_items + self.country_items + self.global_items
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "query": self.query.query_text,
            "farmer_id": self.query.context.farmer_id,
            "country_code": self.query.context.country_code,
            "items": {
                "farmer_specific": [{"content": item.content, "source": item.source_type} 
                                  for item in self.farmer_items],
                "country_specific": [{"content": item.content, "source": item.source_type} 
                                   for item in self.country_items],
                "global": [{"content": item.content, "source": item.source_type} 
                          for item in self.global_items]
            },
            "metadata": self.metadata
        }


class InformationHierarchyManager:
    """
    Manages the information hierarchy system
    Ensures constitutional compliance for data privacy and relevance
    """
    
    def __init__(self):
        self.sources: Dict[str, InformationSource] = {}
        self._register_default_sources()
    
    def _register_default_sources(self):
        """Register default information sources"""
        # Database source - can access all levels
        self.register_source(InformationSource(
            source_id="farmer_db",
            source_type="database",
            source_name="Farmer Database",
            can_access_farmer_data=True,
            can_access_country_data=True,
            can_access_global_data=False
        ))
        
        # RAG source - country and global only
        self.register_source(InformationSource(
            source_id="rag_knowledge",
            source_type="rag",
            source_name="Agricultural Knowledge Base",
            can_access_farmer_data=False,
            can_access_country_data=True,
            can_access_global_data=True
        ))
        
        # External source - global only (privacy protection)
        self.register_source(InformationSource(
            source_id="external_search",
            source_type="external",
            source_name="Web Search (Perplexity)",
            can_access_farmer_data=False,
            can_access_country_data=False,
            can_access_global_data=True
        ))
    
    def register_source(self, source: InformationSource):
        """Register an information source"""
        self.sources[source.source_id] = source
        logger.info(f"Registered information source: {source.source_name}")
    
    def query_information(self, query: InformationQuery) -> InformationResult:
        """
        Query information from all sources respecting hierarchy
        Constitutional compliance: Enforces privacy rules
        """
        result = InformationResult(query=query)
        
        # Track which sources were used
        sources_used = []
        
        # Query each relevance level
        if InformationRelevance.FARMER_SPECIFIC in query.required_relevance_levels:
            farmer_items = self._query_farmer_specific(query)
            result.farmer_items = farmer_items[:query.max_items_per_level]
            if farmer_items:
                sources_used.append("farmer_specific")
        
        if InformationRelevance.COUNTRY_SPECIFIC in query.required_relevance_levels:
            country_items = self._query_country_specific(query)
            result.country_items = country_items[:query.max_items_per_level]
            if country_items:
                sources_used.append("country_specific")
        
        if InformationRelevance.GLOBAL in query.required_relevance_levels:
            global_items = self._query_global(query)
            result.global_items = global_items[:query.max_items_per_level]
            if global_items:
                sources_used.append("global")
        
        # Add metadata
        result.metadata = {
            "query_timestamp": datetime.utcnow().isoformat(),
            "sources_used": sources_used,
            "total_items": len(result.get_all_items_by_priority()),
            "context_hash": self._hash_context(query.context)
        }
        
        # Log for transparency
        self._log_query(result)
        
        return result
    
    def _query_farmer_specific(self, query: InformationQuery) -> List[InformationItem]:
        """
        Query farmer-specific information
        Privacy protection: Only from authorized sources
        """
        items = []
        
        for source_id, source in self.sources.items():
            if source.can_access_farmer_data and query.context.farmer_id:
                # In real implementation, this would call the actual source
                # For now, we'll create placeholder logic
                logger.debug(f"Querying farmer data from {source.source_name}")
                
                # Example: Query farmer's database records
                if source.source_type == "database":
                    # This would be replaced with actual database query
                    items.extend(self._mock_farmer_database_query(query))
        
        return items
    
    def _query_country_specific(self, query: InformationQuery) -> List[InformationItem]:
        """Query country-specific information"""
        items = []
        
        for source_id, source in self.sources.items():
            if source.can_access_country_data and query.context.country_code:
                logger.debug(f"Querying country data from {source.source_name}")
                
                # Example: Query country-specific knowledge
                if source.source_type == "rag":
                    # This would be replaced with actual RAG query
                    items.extend(self._mock_country_rag_query(query))
        
        return items
    
    def _query_global(self, query: InformationQuery) -> List[InformationItem]:
        """Query global information"""
        items = []
        
        for source_id, source in self.sources.items():
            if source.can_access_global_data:
                logger.debug(f"Querying global data from {source.source_name}")
                
                # Example: Query global knowledge
                if source.source_type in ["rag", "external"]:
                    # This would be replaced with actual query
                    items.extend(self._mock_global_query(query))
        
        return items
    
    def _hash_context(self, context: LocalizationContext) -> str:
        """Create hash of context for caching"""
        context_str = f"{context.whatsapp_number}:{context.country_code}:{context.preferred_language}"
        return hashlib.sha256(context_str.encode()).hexdigest()[:16]
    
    def _log_query(self, result: InformationResult):
        """Log query for transparency and debugging"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": result.query.query_text,
            "farmer_id": result.query.context.farmer_id,
            "country": result.query.context.country_code,
            "items_found": {
                "farmer": len(result.farmer_items),
                "country": len(result.country_items),
                "global": len(result.global_items)
            }
        }
        logger.info(f"Information query completed: {json.dumps(log_entry)}")
    
    # Mock methods for demonstration - replace with actual implementations
    def _mock_farmer_database_query(self, query: InformationQuery) -> List[InformationItem]:
        """Mock farmer database query - replace with actual implementation"""
        # In real implementation, this would query the PostgreSQL database
        return [
            InformationItem(
                content=f"Farmer {query.context.farmer_id}'s fields and current crops",
                relevance=InformationRelevance.FARMER_SPECIFIC,
                farmer_id=query.context.farmer_id,
                source_type="database",
                metadata={"table": "fields", "query_type": "farmer_overview"}
            )
        ]
    
    def _mock_country_rag_query(self, query: InformationQuery) -> List[InformationItem]:
        """Mock country RAG query - replace with actual implementation"""
        # In real implementation, this would query the RAG system
        return [
            InformationItem(
                content=f"Agricultural regulations in {query.context.country_name}",
                relevance=InformationRelevance.COUNTRY_SPECIFIC,
                country_code=query.context.country_code,
                source_type="rag",
                metadata={"document": "country_regulations", "relevance_score": 0.95}
            )
        ]
    
    def _mock_global_query(self, query: InformationQuery) -> List[InformationItem]:
        """Mock global query - replace with actual implementation"""
        # In real implementation, this would query global sources
        return [
            InformationItem(
                content="General agricultural best practices",
                relevance=InformationRelevance.GLOBAL,
                source_type="rag",
                metadata={"document": "global_agriculture", "relevance_score": 0.85}
            )
        ]
    
    def validate_privacy_compliance(self, item: InformationItem, source: InformationSource) -> bool:
        """
        Validate that an information item complies with privacy rules
        Constitutional compliance: Privacy-first principle
        """
        # Farmer data can only come from authorized sources
        if item.relevance == InformationRelevance.FARMER_SPECIFIC:
            if not source.can_access_farmer_data:
                logger.error(f"Privacy violation: {source.source_name} attempted to provide farmer data")
                return False
        
        # Country data restrictions
        if item.relevance == InformationRelevance.COUNTRY_SPECIFIC:
            if not source.can_access_country_data:
                logger.error(f"Privacy violation: {source.source_name} attempted to provide country data")
                return False
        
        return True
    
    def get_source_capabilities(self) -> Dict[str, Dict[str, bool]]:
        """Get capabilities of all registered sources"""
        return {
            source_id: {
                "farmer_data": source.can_access_farmer_data,
                "country_data": source.can_access_country_data,
                "global_data": source.can_access_global_data,
                "source_type": source.source_type
            }
            for source_id, source in self.sources.items()
        }


# Example usage
if __name__ == "__main__":
    from localization_handler import LocalizationContext
    
    # Initialize manager
    manager = InformationHierarchyManager()
    
    # Create test context
    context = LocalizationContext(
        whatsapp_number="+359123456789",
        country_code="BG",
        country_name="Bulgaria",
        languages=["bg"],
        farmer_id=123,
        preferred_language="bg"
    )
    
    # Create query
    query = InformationQuery(
        query_text="When should I harvest my mangoes?",
        context=context
    )
    
    # Execute query
    result = manager.query_information(query)
    
    # Display results
    print("Information Hierarchy Results:")
    print(f"Query: {result.query.query_text}")
    print(f"\nFarmer-specific items: {len(result.farmer_items)}")
    for item in result.farmer_items:
        print(f"  - {item.content}")
    
    print(f"\nCountry-specific items: {len(result.country_items)}")
    for item in result.country_items:
        print(f"  - {item.content}")
    
    print(f"\nGlobal items: {len(result.global_items)}")
    for item in result.global_items:
        print(f"  - {item.content}")
    
    print(f"\nMetadata: {json.dumps(result.metadata, indent=2)}")