"""
AVA OLO Document Search Core - Information Hierarchy
Constitutional Amendment #13 Implementation

This package contains the information relevance hierarchy system:
- information_hierarchy: Manages 3-tier information priority
"""

from .information_hierarchy import (
    InformationHierarchyManager,
    InformationQuery,
    InformationResult,
    InformationSource,
    RelevancePriority
)

__all__ = [
    'InformationHierarchyManager',
    'InformationQuery',
    'InformationResult',
    'InformationSource',
    'RelevancePriority'
]

# Version info
__version__ = '1.0.0'
__amendment__ = 13