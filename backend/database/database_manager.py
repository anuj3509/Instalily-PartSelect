"""
Database manager for PartSelect RAG system
Handles all database operations with read-optimized queries
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PartSelectDatabase:
    """Read-optimized database manager for PartSelect data"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to backend/database/partselect.db
            current_dir = Path(__file__).parent
            db_path = current_dir / "partselect.db"
        
        self.db_path = str(db_path)
        self.schema_path = Path(__file__).parent / "schema.sql"
        self._init_database()
    
    def _init_database(self):
        """Initialize database with schema if it doesn't exist"""
        try:
            with self.get_connection() as conn:
                # Read and execute schema
                if self.schema_path.exists():
                    with open(self.schema_path, 'r') as f:
                        schema_sql = f.read()
                    conn.executescript(schema_sql)
                    conn.commit()
                    logger.info("Database schema initialized successfully")
                else:
                    logger.error(f"Schema file not found: {self.schema_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def search_parts(self, query: str, limit: int = 10, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search parts using full-text search and filters"""
        try:
            with self.get_connection() as conn:
                # Build FTS query
                fts_query = f'"{query}"' if ' ' in query else query
                
                sql = """
                SELECT p.*, 
                       snippet(parts_fts, 1, '<mark>', '</mark>', '...', 32) as snippet
                FROM parts p
                JOIN parts_fts ON parts_fts.rowid = p.id
                WHERE parts_fts MATCH ?
                """
                
                params = [fts_query]
                
                # Add filters
                if filters:
                    if filters.get('brand'):
                        sql += " AND p.brand = ?"
                        params.append(filters['brand'])
                    if filters.get('category'):
                        sql += " AND p.category = ?"
                        params.append(filters['category'])
                    if filters.get('max_price'):
                        sql += " AND p.price <= ?"
                        params.append(filters['max_price'])
                    if filters.get('in_stock'):
                        sql += " AND p.in_stock = 1"
                
                sql += " ORDER BY bm25(parts_fts) LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(sql, params)
                results = [dict(row) for row in cursor.fetchall()]
                
                # Parse JSON fields
                for result in results:
                    if result.get('specifications'):
                        try:
                            result['specifications'] = json.loads(result['specifications'])
                        except json.JSONDecodeError:
                            result['specifications'] = {}
                
                logger.info(f"Found {len(results)} parts for query: {query}")
                return results
                
        except Exception as e:
            logger.error(f"Error searching parts: {e}")
            return []
    
    def get_part_by_number(self, part_number: str) -> Optional[Dict[str, Any]]:
        """Get specific part by part number"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM parts WHERE part_number = ?",
                    [part_number]
                )
                result = cursor.fetchone()
                
                if result:
                    part = dict(result)
                    if part.get('specifications'):
                        try:
                            part['specifications'] = json.loads(part['specifications'])
                        except json.JSONDecodeError:
                            part['specifications'] = {}
                    return part
                return None
                
        except Exception as e:
            logger.error(f"Error getting part {part_number}: {e}")
            return None
    
    def search_compatible_parts(self, model_number: str, appliance_type: str = None) -> List[Dict[str, Any]]:
        """Find parts compatible with a specific model"""
        try:
            with self.get_connection() as conn:
                sql = """
                SELECT p.*, pc.model_number, pc.appliance_type
                FROM parts p
                JOIN part_compatibility pc ON p.part_number = pc.part_number
                WHERE pc.model_number = ?
                """
                params = [model_number]
                
                if appliance_type:
                    sql += " AND pc.appliance_type = ?"
                    params.append(appliance_type)
                
                sql += " ORDER BY p.name"
                
                cursor = conn.execute(sql, params)
                results = [dict(row) for row in cursor.fetchall()]
                
                logger.info(f"Found {len(results)} compatible parts for model: {model_number}")
                return results
                
        except Exception as e:
            logger.error(f"Error searching compatible parts: {e}")
            return []
    
    def search_repairs(self, symptom: str, appliance_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search repair guides by symptom"""
        try:
            with self.get_connection() as conn:
                fts_query = f'"{symptom}"' if ' ' in symptom else symptom
                
                sql = """
                SELECT r.*,
                       snippet(repairs_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
                FROM repairs r
                JOIN repairs_fts ON repairs_fts.rowid = r.id
                WHERE repairs_fts MATCH ?
                """
                params = [fts_query]
                
                if appliance_type:
                    sql += " AND r.appliance_type = ?"
                    params.append(appliance_type)
                
                sql += " ORDER BY bm25(repairs_fts) LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(sql, params)
                results = [dict(row) for row in cursor.fetchall()]
                
                logger.info(f"Found {len(results)} repair guides for symptom: {symptom}")
                return results
                
        except Exception as e:
            logger.error(f"Error searching repairs: {e}")
            return []
    
    def search_blogs(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search blog content"""
        try:
            with self.get_connection() as conn:
                fts_query = f'"{query}"' if ' ' in query else query
                
                sql = """
                SELECT b.*,
                       snippet(blogs_fts, 1, '<mark>', '</mark>', '...', 64) as snippet
                FROM blogs b
                JOIN blogs_fts ON blogs_fts.rowid = b.id
                WHERE blogs_fts MATCH ?
                ORDER BY bm25(blogs_fts)
                LIMIT ?
                """
                
                cursor = conn.execute(sql, [fts_query, limit])
                results = [dict(row) for row in cursor.fetchall()]
                
                # Parse JSON fields
                for result in results:
                    if result.get('tags'):
                        try:
                            result['tags'] = json.loads(result['tags'])
                        except json.JSONDecodeError:
                            result['tags'] = []
                
                logger.info(f"Found {len(results)} blog articles for query: {query}")
                return results
                
        except Exception as e:
            logger.error(f"Error searching blogs: {e}")
            return []
    
    def get_brands(self, appliance_type: str = None) -> List[str]:
        """Get list of available brands"""
        try:
            with self.get_connection() as conn:
                sql = "SELECT DISTINCT brand FROM parts WHERE brand IS NOT NULL"
                params = []
                
                if appliance_type:
                    sql += " AND category = ?"
                    params.append(appliance_type)
                
                sql += " ORDER BY brand"
                
                cursor = conn.execute(sql, params)
                brands = [row[0] for row in cursor.fetchall()]
                return brands
                
        except Exception as e:
            logger.error(f"Error getting brands: {e}")
            return []
    
    def get_categories(self, appliance_type: str = None) -> List[Dict[str, str]]:
        """Get available part categories"""
        try:
            with self.get_connection() as conn:
                sql = "SELECT * FROM part_categories"
                params = []
                
                if appliance_type:
                    sql += " WHERE appliance_type = ?"
                    params.append(appliance_type)
                
                sql += " ORDER BY category_name"
                
                cursor = conn.execute(sql, params)
                categories = [dict(row) for row in cursor.fetchall()]
                return categories
                
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    def get_price_range(self, category: str = None) -> Tuple[float, float]:
        """Get price range for parts"""
        try:
            with self.get_connection() as conn:
                sql = "SELECT MIN(price), MAX(price) FROM parts WHERE price IS NOT NULL"
                params = []
                
                if category:
                    sql += " AND category = ?"
                    params.append(category)
                
                cursor = conn.execute(sql, params)
                result = cursor.fetchone()
                
                if result and result[0] is not None:
                    return float(result[0]), float(result[1])
                return 0.0, 0.0
                
        except Exception as e:
            logger.error(f"Error getting price range: {e}")
            return 0.0, 0.0
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                stats = {}
                
                # Count records in each table
                tables = ['parts', 'repairs', 'blogs', 'part_compatibility']
                for table in tables:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[table] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def load_data_from_json(self):
        """Load data from scraped JSON files into database"""
        try:
            data_dir = Path(__file__).parent.parent.parent / "scraping" / "data"
            
            # Load parts data
            parts_file = data_dir / "all_parts.json"
            if parts_file.exists():
                self._load_parts_data(str(parts_file))
            
            # Load PartSelect parts data
            partselect_parts_file = data_dir / "all_partselect_parts.json"
            if partselect_parts_file.exists():
                self._load_partselect_parts_data(str(partselect_parts_file))
            
            # Load repairs data
            repairs_file = data_dir / "all_repairs.json"
            if repairs_file.exists():
                self._load_repairs_data(str(repairs_file))
            
            # Load blogs data
            blogs_file = data_dir / "partselect_blogs.json"
            if blogs_file.exists():
                self._load_blogs_data(str(blogs_file))
            
            logger.info("Data loading completed successfully")
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def load_partselect_parts_only(self):
        """Load only PartSelect parts data"""
        try:
            data_dir = Path(__file__).parent.parent.parent / "scraping" / "data"
            partselect_parts_file = data_dir / "all_partselect_parts.json"
            
            if partselect_parts_file.exists():
                logger.info(f"Loading PartSelect parts from: {partselect_parts_file}")
                self._load_partselect_parts_data(str(partselect_parts_file))
                logger.info("PartSelect parts data loading completed successfully")
            else:
                logger.error(f"PartSelect parts file not found: {partselect_parts_file}")
                
        except Exception as e:
            logger.error(f"Error loading PartSelect parts data: {e}")
            raise
    
    def _load_parts_data(self, json_file: str):
        """Load parts data from JSON file"""
        with open(json_file, 'r') as f:
            parts_data = json.load(f)
        
        with self.get_connection() as conn:
            for part in parts_data:
                # Insert part
                conn.execute("""
                    INSERT OR REPLACE INTO parts 
                    (part_number, name, description, price, brand, category, 
                     image_url, product_url, installation_guide, install_video_url, 
                     in_stock, specifications)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    part.get('part_number'),
                    part.get('name'),
                    part.get('description'),
                    part.get('price'),
                    part.get('brand'),
                    part.get('category'),
                    part.get('image_url'),
                    part.get('product_url'),
                    part.get('installation_guide'),
                    part.get('install_video_url'),
                    part.get('in_stock', True),
                    json.dumps(part.get('specifications', {}))
                ])
                
                # Insert compatibility data
                if part.get('compatibility_models'):
                    for model in part['compatibility_models']:
                        if model.strip():  # Skip empty models
                            conn.execute("""
                                INSERT OR IGNORE INTO part_compatibility 
                                (part_number, model_number, appliance_type)
                                VALUES (?, ?, ?)
                            """, [
                                part.get('part_number'),
                                model.strip(),
                                part.get('category')
                            ])
            
            conn.commit()
            logger.info(f"Loaded {len(parts_data)} parts into database")
    
    def _load_partselect_parts_data(self, json_file: str):
        """Load PartSelect parts data from JSON file with new schema"""
        with open(json_file, 'r') as f:
            parts_data = json.load(f)
        
        with self.get_connection() as conn:
            for part in parts_data:
                # Determine category from product_types
                category = None
                product_types = part.get('product_types', '').lower()
                if 'dishwasher' in product_types:
                    category = 'dishwasher'
                elif 'refrigerator' in product_types:
                    category = 'refrigerator'
                
                # Convert availability to boolean for in_stock
                availability = part.get('availability', '').lower()
                in_stock = availability == 'in stock'
                
                # Insert part with new schema
                conn.execute("""
                    INSERT OR REPLACE INTO parts 
                    (part_number, name, price, brand, manufacturer, manufacturer_id, 
                     category, product_url, installation_difficulty, installation_time, 
                     video_url, symptoms, product_types, replacement_parts, 
                     availability, in_stock, specifications)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    part.get('part_number'),
                    part.get('name'),
                    part.get('price'),
                    part.get('manufacturer'),  # Use manufacturer as brand for consistency
                    part.get('manufacturer'),
                    part.get('manufacturer_id'),
                    category,
                    part.get('product_url'),
                    part.get('installation_difficulty'),
                    part.get('installation_time'),
                    part.get('video_url'),
                    part.get('symptoms'),
                    part.get('product_types'),
                    part.get('replacement_parts'),
                    part.get('availability'),
                    in_stock,
                    json.dumps({
                        'part_number': part.get('part_number'),
                        'manufacturer_id': part.get('manufacturer_id'),
                        'category': category,
                        'url': part.get('product_url')
                    })
                ])
            
            conn.commit()
            logger.info(f"Loaded {len(parts_data)} PartSelect parts into database")
    
    def _load_repairs_data(self, json_file: str):
        """Load repairs data from JSON file"""
        with open(json_file, 'r') as f:
            repairs_data = json.load(f)
        
        with self.get_connection() as conn:
            for repair in repairs_data:
                conn.execute("""
                    INSERT OR REPLACE INTO repairs 
                    (appliance_type, symptom, description, difficulty, 
                     percentage_reported, parts_needed, symptom_detail_url, repair_video_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    repair.get('product', '').lower(),  # Convert to lowercase
                    repair.get('symptom'),
                    repair.get('description'),
                    repair.get('difficulty'),
                    repair.get('percentage'),
                    repair.get('parts'),
                    repair.get('symptom_detail_url'),
                    repair.get('repair_video_url')
                ])
            
            conn.commit()
            logger.info(f"Loaded {len(repairs_data)} repair guides into database")
    
    def _load_blogs_data(self, json_file: str):
        """Load blogs data from JSON file"""
        with open(json_file, 'r') as f:
            blogs_data = json.load(f)
        
        with self.get_connection() as conn:
            for blog in blogs_data:
                conn.execute("""
                    INSERT OR REPLACE INTO blogs 
                    (title, url, excerpt, author, date_published, category, 
                     tags, content, image_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    blog.get('title'),
                    blog.get('url'),
                    blog.get('excerpt'),
                    blog.get('author'),
                    blog.get('date'),
                    blog.get('category'),
                    json.dumps(blog.get('tags', [])),
                    blog.get('content'),
                    blog.get('image_url')
                ])
            
            conn.commit()
            logger.info(f"Loaded {len(blogs_data)} blog articles into database")

# Test the database
if __name__ == "__main__":
    db = PartSelectDatabase()
    
    # Load data if database is empty
    stats = db.get_database_stats()
    if stats.get('parts', 0) == 0:
        print("Loading data from JSON files...")
        db.load_data_from_json()
    
    # Print stats
    stats = db.get_database_stats()
    print("Database Statistics:")
    for table, count in stats.items():
        print(f"  {table}: {count} records")
    
    # Test search
    print("\nTesting part search:")
    results = db.search_parts("water filter", limit=3)
    for result in results:
        print(f"  - {result['name']} ({result['part_number']}) - ${result['price']}")
