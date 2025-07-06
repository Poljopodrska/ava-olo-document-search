"""
Knowledge Search - Agricultural knowledge retrieval (RAG)
Handles FIS documents and agricultural best practices
"""
import logging
from typing import Dict, Any, Optional, List
import os
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
import json
from datetime import datetime

load_dotenv()

logger = logging.getLogger(__name__)

class KnowledgeSearch:
    """
    Agricultural knowledge search using Pinecone vector database
    Contains FIS documents, best practices, and agricultural knowledge
    """
    
    def __init__(self):
        self.pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.index_name = os.getenv('PINECONE_INDEX_NAME', 'ava-olo-knowledge')
        self.index = self.pc.Index(self.index_name)
        self.embedding_model = "text-embedding-ada-002"
        
    async def search(self, query: str, filters: Dict[str, Any] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search agricultural knowledge base
        
        Args:
            query: Search query (any language)
            filters: Optional filters (crop_type, document_type, etc.)
            top_k: Number of results to return
            
        Returns:
            List of relevant documents with metadata
        """
        try:
            # Generate embedding for the query
            embedding = await self._get_embedding(query)
            
            # Build filter for Pinecone query
            pinecone_filter = self._build_filter(filters) if filters else None
            
            # Search Pinecone
            results = self.index.query(
                vector=embedding,
                filter=pinecone_filter,
                top_k=top_k,
                include_metadata=True
            )
            
            # Process results
            documents = []
            for match in results.matches:
                doc = {
                    "id": match.id,
                    "score": match.score,
                    "text": match.metadata.get("text", ""),
                    "source": match.metadata.get("source", "unknown"),
                    "document_type": match.metadata.get("document_type", "general"),
                    "language": match.metadata.get("language", "hr"),
                    "metadata": match.metadata
                }
                
                # Extract specific agricultural info if available
                if "crop" in match.metadata:
                    doc["crop"] = match.metadata["crop"]
                if "chemical" in match.metadata:
                    doc["chemical"] = match.metadata["chemical"]
                if "phi_days" in match.metadata:
                    doc["phi_days"] = match.metadata["phi_days"]
                    
                documents.append(doc)
            
            logger.info(f"Found {len(documents)} documents for query: {query}")
            return documents
            
        except Exception as e:
            logger.error(f"Knowledge search error: {str(e)}")
            return []
    
    async def search_pesticide_info(self, chemical_name: str, crop: str = None) -> Dict[str, Any]:
        """
        Specialized search for pesticide information
        Handles queries like "Koliko je karenca za Prosaro u pšenici?"
        """
        try:
            # Build specialized query
            query = f"{chemical_name}"
            if crop:
                query += f" {crop}"
            
            # Search with specific filters
            filters = {
                "document_type": "pesticide",
                "chemical": chemical_name.lower()
            }
            if crop:
                filters["crop"] = crop.lower()
            
            documents = await self.search(query, filters, top_k=3)
            
            # Extract PHI (karenca) information
            phi_info = None
            for doc in documents:
                if "phi_days" in doc.get("metadata", {}):
                    phi_info = {
                        "chemical": chemical_name,
                        "crop": crop or doc.get("crop", ""),
                        "phi_days": doc["metadata"]["phi_days"],
                        "source": doc["source"],
                        "additional_info": doc["text"]
                    }
                    break
            
            if phi_info:
                return {
                    "found": True,
                    "pesticide_info": phi_info,
                    "documents": documents
                }
            else:
                return {
                    "found": False,
                    "message": f"No PHI information found for {chemical_name}",
                    "documents": documents
                }
                
        except Exception as e:
            logger.error(f"Pesticide search error: {str(e)}")
            return {
                "found": False,
                "error": str(e)
            }
    
    async def search_crop_protection(self, crop: str, problem: str = None) -> List[Dict[str, Any]]:
        """
        Search for crop protection recommendations
        """
        try:
            # Build query based on crop and problem
            query = f"{crop} protection"
            if problem:
                query += f" {problem}"
            
            filters = {
                "document_type": "crop_protection",
                "crop": crop.lower()
            }
            
            documents = await self.search(query, filters, top_k=5)
            
            # Group by protection type
            protection_info = {
                "fungicides": [],
                "insecticides": [],
                "herbicides": [],
                "general": []
            }
            
            for doc in documents:
                protection_type = doc.get("metadata", {}).get("protection_type", "general")
                protection_info[protection_type].append({
                    "chemical": doc.get("metadata", {}).get("chemical", ""),
                    "target": doc.get("metadata", {}).get("target_pest", ""),
                    "dosage": doc.get("metadata", {}).get("dosage", ""),
                    "timing": doc.get("metadata", {}).get("application_timing", ""),
                    "text": doc["text"]
                })
            
            return protection_info
            
        except Exception as e:
            logger.error(f"Crop protection search error: {str(e)}")
            return {"error": str(e)}
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation error: {str(e)}")
            raise
    
    def _build_filter(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Build Pinecone filter from user filters"""
        pinecone_filter = {}
        
        if "document_type" in filters:
            pinecone_filter["document_type"] = filters["document_type"]
        
        if "crop" in filters:
            pinecone_filter["crop"] = filters["crop"].lower()
        
        if "chemical" in filters:
            pinecone_filter["chemical"] = filters["chemical"].lower()
        
        if "language" in filters:
            pinecone_filter["language"] = filters["language"]
        
        return pinecone_filter
    
    async def add_document(self, document: Dict[str, Any]) -> bool:
        """
        Add document to knowledge base
        Used for indexing FIS documents and other agricultural content
        """
        try:
            # Generate embedding
            embedding = await self._get_embedding(document["text"])
            
            # Prepare metadata
            metadata = {
                "text": document["text"],
                "source": document.get("source", "manual"),
                "document_type": document.get("document_type", "general"),
                "language": document.get("language", "hr"),
                "indexed_at": datetime.now().isoformat()
            }
            
            # Add agricultural specific metadata
            if "crop" in document:
                metadata["crop"] = document["crop"].lower()
            if "chemical" in document:
                metadata["chemical"] = document["chemical"].lower()
            if "phi_days" in document:
                metadata["phi_days"] = document["phi_days"]
            
            # Generate ID
            doc_id = f"{document.get('source', 'doc')}_{hash(document['text'])}"
            
            # Upsert to Pinecone
            self.index.upsert(
                vectors=[(doc_id, embedding, metadata)]
            )
            
            logger.info(f"Added document {doc_id} to knowledge base")
            return True
            
        except Exception as e:
            logger.error(f"Error adding document: {str(e)}")
            return False
    
    async def bulk_index_fis_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Bulk index FIS documents
        Returns statistics about indexing
        """
        stats = {
            "total": len(documents),
            "success": 0,
            "failed": 0
        }
        
        for doc in documents:
            success = await self.add_document(doc)
            if success:
                stats["success"] += 1
            else:
                stats["failed"] += 1
        
        logger.info(f"Bulk indexing complete: {stats}")
        return stats