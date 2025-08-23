"""
Vector database setup and data ingestion for PartSelect agents
Uses ChromaDB for vector storage with specialized collections
"""

import os
import json
import pandas as pd
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
import logging
from pathlib import Path
from dotenv import load_dotenv
import voyageai

# Load environment variables from project root
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PartSelectVectorStore:
    def __init__(self, persist_directory: str = "vector_db"):
        """Initialize ChromaDB with persistent storage"""
        self.persist_directory = persist_directory
        
        # Create client with persistence
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Use Voyage AI embeddings (better and more cost-effective than OpenAI)
        self.voyage_client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
        self.embedding_function = self._create_voyage_embedding_function()
        
        # Initialize collections
        self.parts_collection = None
        self.repairs_collection = None
        self.blogs_collection = None
        
    def setup_collections(self):
        """Create or get existing collections"""
        logger.info("Setting up vector collections...")
        
        # Parts collection - for detailed part information
        self.parts_collection = self.client.get_or_create_collection(
            name="parts",
            embedding_function=self.embedding_function,
            metadata={"description": "Appliance parts with detailed specifications"}
        )
        
        # Repairs collection - for symptom-based troubleshooting
        self.repairs_collection = self.client.get_or_create_collection(
            name="repairs",
            embedding_function=self.embedding_function,
            metadata={"description": "Repair guides and troubleshooting"}
        )
        
        # Blogs collection - for additional resources
        self.blogs_collection = self.client.get_or_create_collection(
            name="blogs",
            embedding_function=self.embedding_function,
            metadata={"description": "Blog posts and educational content"}
        )
        
        logger.info("Collections setup complete")
    
    def _create_voyage_embedding_function(self):
        """Create a custom embedding function for Voyage AI compatible with ChromaDB"""
        
        class VoyageEmbeddingFunction:
            def __init__(self, client):
                self.client = client
                self.model = "voyage-3.5"
            
            def __call__(self, input):
                """Generate embeddings for input texts using Voyage AI"""
                try:
                    # Convert single string to list if needed
                    if isinstance(input, str):
                        input = [input]
                    
                    # Get embeddings from Voyage AI
                    result = self.client.embed(
                        input, 
                        model=self.model,
                        input_type="document"
                    )
                    
                    return result.embeddings
                except Exception as e:
                    logger.error(f"Error getting Voyage embeddings: {str(e)}")
                    raise
            
            # ChromaDB expects these methods
            def name(self):
                return f"voyage-{self.model}-embeddings"
            
            def model_name(self):
                return self.model
        
        return VoyageEmbeddingFunction(self.voyage_client)
    
    def ingest_parts_data(self, json_file_path: str):
        """Ingest parts data from JSON file"""
        logger.info(f"Ingesting parts data from {json_file_path}")
        
        # Check if collection already has data
        if self.parts_collection.count() > 0:
            logger.info(f"Parts collection already contains {self.parts_collection.count()} items")
            return
            
        with open(json_file_path, 'r', encoding='utf-8') as f:
            parts_data = json.load(f)
        
        documents = []
        metadatas = []
        ids = []
        
        for i, part in enumerate(parts_data):
            # Create rich document text for embedding
            doc_text = self._create_parts_document_text(part)
            documents.append(doc_text)
            
            # Store metadata for retrieval
            metadata = {
                "part_number": str(part.get("part_number", "")),
                "name": str(part.get("name", "")),
                "brand": str(part.get("brand", "")),
                "category": str(part.get("category", "")),
                "price": float(part.get("price", 0.0)),
                "install_difficulty": str(part.get("install_difficulty", "")),
                "install_time": str(part.get("install_time", "")),
                "product_url": str(part.get("product_url", "")),
                "install_video_url": str(part.get("install_video_url", "")),
                "appliance_types": str(part.get("appliance_types", [])),
                "symptoms": str(part.get("symptoms", [])),
                "data_type": "part"
            }
            metadatas.append(metadata)
            ids.append(f"part_{i}")
        
        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            self.parts_collection.add(
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids
            )
        
        logger.info(f"Ingested {len(documents)} parts into vector store")
    
    def ingest_repairs_data(self, json_file_path: str):
        """Ingest repairs data from JSON file"""
        logger.info(f"Ingesting repairs data from {json_file_path}")
        
        if self.repairs_collection.count() > 0:
            logger.info(f"Repairs collection already contains {self.repairs_collection.count()} items")
            return
            
        with open(json_file_path, 'r', encoding='utf-8') as f:
            repairs_data = json.load(f)
        
        documents = []
        metadatas = []
        ids = []
        
        for i, repair in enumerate(repairs_data):
            # Create document text focused on symptoms and solutions
            doc_text = self._create_repairs_document_text(repair)
            documents.append(doc_text)
            
            metadata = {
                "appliance": str(repair.get("appliance", "")),
                "symptom": str(repair.get("symptom", "")),
                "parts": str(repair.get("parts", [])),
                "difficulty": str(repair.get("difficulty", "")),
                "percentage": str(repair.get("percentage", "")),
                "repair_video_url": str(repair.get("repair_video_url", "")),
                "symptom_detail_url": str(repair.get("symptom_detail_url", "")),
                "data_type": "repair"
            }
            metadatas.append(metadata)
            ids.append(f"repair_{i}")
        
        # Add to collection
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            self.repairs_collection.add(
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids
            )
        
        logger.info(f"Ingested {len(documents)} repairs into vector store")
    
    def ingest_blogs_data(self, json_file_path: str):
        """Ingest blog data from JSON file"""
        logger.info(f"Ingesting blogs data from {json_file_path}")
        
        if self.blogs_collection.count() > 0:
            logger.info(f"Blogs collection already contains {self.blogs_collection.count()} items")
            return
            
        with open(json_file_path, 'r', encoding='utf-8') as f:
            blogs_data = json.load(f)
        
        documents = []
        metadatas = []
        ids = []
        
        for i, blog in enumerate(blogs_data):
            # Use title as document text
            doc_text = str(blog.get("title", ""))
            if not doc_text.strip():
                continue
                
            documents.append(doc_text)
            
            metadata = {
                "title": str(blog.get("title", "")),
                "url": str(blog.get("url", "")),
                "data_type": "blog"
            }
            metadatas.append(metadata)
            ids.append(f"blog_{i}")
        
        if documents:
            # Add to collection
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i+batch_size]
                batch_metas = metadatas[i:i+batch_size]
                batch_ids = ids[i:i+batch_size]
                
                self.blogs_collection.add(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids
                )
        
        logger.info(f"Ingested {len(documents)} blogs into vector store")
    
    def ingest_csv_parts_data(self, csv_file_path: str):
        """Ingest parts data from CSV file"""
        logger.info(f"Ingesting CSV parts data from {csv_file_path}")
        
        # Check if collection already has CSV data
        existing_count = self.parts_collection.count()
        if existing_count > 0:
            logger.info(f"Parts collection already contains {existing_count} items, adding CSV data...")
            
        # Read CSV file
        df = pd.read_csv(csv_file_path)
        logger.info(f"Loaded {len(df)} rows from CSV")
        
        documents = []
        metadatas = []
        ids = []
        
        for i, row in df.iterrows():
            # Create rich document text for embedding
            doc_text = self._create_csv_parts_document_text(row)
            documents.append(doc_text)
            
            # Store metadata for retrieval
            metadata = {
                "part_number": str(row.get("part_number", "")),
                "name": str(row.get("name", "")),
                "manufacturer": str(row.get("manufacturer", "")),
                "price": float(row.get("price", 0.0)) if pd.notna(row.get("price")) else 0.0,
                "installation_difficulty": str(row.get("installation_difficulty", "")),
                "installation_time": str(row.get("installation_time", "")),
                "product_url": str(row.get("product_url", "")),
                "video_url": str(row.get("video_url", "")),
                "product_types": str(row.get("product_types", "")),
                "symptoms": str(row.get("symptoms", "")),
                "availability": str(row.get("availability", "")),
                "data_type": "csv_part"
            }
            metadatas.append(metadata)
            ids.append(f"csv_part_{i}")
        
        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            end_idx = min(i + batch_size, len(documents))
            batch_docs = documents[i:end_idx]
            batch_metas = metadatas[i:end_idx]
            batch_ids = ids[i:end_idx]
            
            self.parts_collection.add(
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids
            )
        
        logger.info(f"Ingested {len(documents)} CSV parts into vector store")
    
    def _create_csv_parts_document_text(self, row: pd.Series) -> str:
        """Create document text for CSV parts embedding"""
        text_parts = []
        
        # Core part information
        if pd.notna(row.get("name")):
            text_parts.append(f"Part: {row['name']}")
        if pd.notna(row.get("part_number")):
            text_parts.append(f"Part Number: {row['part_number']}")
        if pd.notna(row.get("manufacturer")):
            text_parts.append(f"Manufacturer: {row['manufacturer']}")
        
        # Functional information
        if pd.notna(row.get("symptoms")):
            text_parts.append(f"Symptoms: {row['symptoms']}")
        
        if pd.notna(row.get("product_types")):
            text_parts.append(f"Product types: {row['product_types']}")
        
        # Installation information
        if pd.notna(row.get("installation_difficulty")):
            text_parts.append(f"Installation difficulty: {row['installation_difficulty']}")
        if pd.notna(row.get("installation_time")):
            text_parts.append(f"Installation time: {row['installation_time']}")
        
        # Additional information
        if pd.notna(row.get("availability")):
            text_parts.append(f"Availability: {row['availability']}")
        
        return " | ".join(text_parts)
    
    def _create_parts_document_text(self, part: Dict[str, Any]) -> str:
        """Create rich document text for parts embedding"""
        text_parts = []
        
        # Core part information
        if part.get("name"):
            text_parts.append(f"Part: {part['name']}")
        if part.get("part_number"):
            text_parts.append(f"Part Number: {part['part_number']}")
        if part.get("brand"):
            text_parts.append(f"Brand: {part['brand']}")
        if part.get("category"):
            text_parts.append(f"Category: {part['category']}")
        
        # Functional information
        if part.get("symptoms"):
            symptoms = part["symptoms"] if isinstance(part["symptoms"], list) else [part["symptoms"]]
            text_parts.append(f"Fixes symptoms: {', '.join(str(s) for s in symptoms)}")
        
        if part.get("appliance_types"):
            appliances = part["appliance_types"] if isinstance(part["appliance_types"], list) else [part["appliance_types"]]
            text_parts.append(f"Compatible with: {', '.join(str(a) for a in appliances)}")
        
        # Installation information
        if part.get("install_difficulty"):
            text_parts.append(f"Installation difficulty: {part['install_difficulty']}")
        if part.get("install_time"):
            text_parts.append(f"Installation time: {part['install_time']}")
        
        return " | ".join(text_parts)
    
    def _create_repairs_document_text(self, repair: Dict[str, Any]) -> str:
        """Create document text for repairs embedding"""
        text_parts = []
        
        if repair.get("appliance"):
            text_parts.append(f"Appliance: {repair['appliance']}")
        if repair.get("symptom"):
            text_parts.append(f"Symptom: {repair['symptom']}")
        if repair.get("parts"):
            parts = repair["parts"] if isinstance(repair["parts"], list) else [repair["parts"]]
            text_parts.append(f"Required parts: {', '.join(str(p) for p in parts)}")
        if repair.get("difficulty"):
            text_parts.append(f"Difficulty: {repair['difficulty']}")
        
        return " | ".join(text_parts)
    
    def get_collection_stats(self):
        """Get statistics about the collections"""
        stats = {
            "parts": self.parts_collection.count() if self.parts_collection else 0,
            "repairs": self.repairs_collection.count() if self.repairs_collection else 0,
            "blogs": self.blogs_collection.count() if self.blogs_collection else 0
        }
        return stats

def main():
    """Main ingestion function"""
    # Get data directory path
    data_dir = Path(__file__).parent.parent.parent.parent / "scraping" / "data"
    
    # Initialize vector store
    vector_store = PartSelectVectorStore()
    vector_store.setup_collections()
    
    # Ingest data
    parts_file = data_dir / "all_parts.json"
    repairs_file = data_dir / "all_repairs.json"
    blogs_file = data_dir / "partselect_blogs.json"
    csv_parts_file = data_dir / "all_partselect_parts.csv"
    
    if parts_file.exists():
        vector_store.ingest_parts_data(str(parts_file))
    else:
        logger.warning(f"Parts file not found: {parts_file}")
    
    if csv_parts_file.exists():
        vector_store.ingest_csv_parts_data(str(csv_parts_file))
    else:
        logger.warning(f"CSV parts file not found: {csv_parts_file}")
    
    if repairs_file.exists():
        vector_store.ingest_repairs_data(str(repairs_file))
    else:
        logger.warning(f"Repairs file not found: {repairs_file}")
    
    if blogs_file.exists():
        vector_store.ingest_blogs_data(str(blogs_file))
    else:
        logger.warning(f"Blogs file not found: {blogs_file}")
    
    # Print statistics
    stats = vector_store.get_collection_stats()
    logger.info("Vector store statistics:")
    for collection, count in stats.items():
        logger.info(f"  {collection}: {count} documents")

if __name__ == "__main__":
    main()
