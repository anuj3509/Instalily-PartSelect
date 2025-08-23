"""
Database tools for LLM to query the read-optimized database
These tools provide structured access to real PartSelect data
"""

import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from pathlib import Path

from ..database.database_manager import PartSelectDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PartSearchRequest(BaseModel):
    """Request model for part search"""
    query: str = Field(description="Search query for parts (e.g., 'water filter', 'door seal')")
    brand: Optional[str] = Field(default=None, description="Filter by brand (e.g., 'Whirlpool', 'GE')")
    category: Optional[str] = Field(default=None, description="Filter by category (e.g., 'refrigerator', 'dishwasher')")
    max_price: Optional[float] = Field(default=None, description="Maximum price filter")
    in_stock_only: Optional[bool] = Field(default=True, description="Only show in-stock parts")
    limit: Optional[int] = Field(default=10, description="Maximum number of results")

class CompatibilitySearchRequest(BaseModel):
    """Request model for compatibility search"""
    model_number: str = Field(description="Appliance model number")
    appliance_type: Optional[str] = Field(default=None, description="Type of appliance ('refrigerator' or 'dishwasher')")

class RepairSearchRequest(BaseModel):
    """Request model for repair guide search"""
    symptom: str = Field(description="Problem description or symptom")
    appliance_type: Optional[str] = Field(default=None, description="Type of appliance ('refrigerator' or 'dishwasher')")
    limit: Optional[int] = Field(default=10, description="Maximum number of results")

class BlogSearchRequest(BaseModel):
    """Request model for blog search"""
    query: str = Field(description="Search query for blog content")
    limit: Optional[int] = Field(default=5, description="Maximum number of results")

class PartSelectDatabaseTools:
    """Database tools for LLM to access real PartSelect data"""
    
    def __init__(self):
        self.db = PartSelectDatabase()
        
        # Initialize database if empty
        stats = self.db.get_database_stats()
        if stats.get('parts', 0) == 0:
            logger.info("Initializing database with data...")
            try:
                self.db.load_data_from_json()
                logger.info("Database initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
    
    def search_parts(self, request: PartSearchRequest) -> Dict[str, Any]:
        """
        Search for appliance parts in the database.
        Returns real parts with actual URLs, prices, and specifications.
        """
        try:
            filters = {}
            if request.brand:
                filters['brand'] = request.brand
            if request.category:
                filters['category'] = request.category
            if request.max_price:
                filters['max_price'] = request.max_price
            if request.in_stock_only:
                filters['in_stock'] = True
            
            results = self.db.search_parts(
                query=request.query,
                limit=request.limit,
                filters=filters
            )
            
            # Format results for LLM
            formatted_results = []
            for part in results:
                formatted_part = {
                    "part_number": part['part_number'],
                    "name": part['name'],
                    "description": part['description'],
                    "price": part['price'],
                    "brand": part['brand'],
                    "category": part['category'],
                    "product_url": part['product_url'],
                    "image_url": part['image_url'],
                    "in_stock": part['in_stock'],
                    "installation_guide": part.get('installation_guide'),
                    "install_video_url": part.get('install_video_url')
                }
                formatted_results.append(formatted_part)
            
            return {
                "success": True,
                "query": request.query,
                "total_results": len(formatted_results),
                "parts": formatted_results,
                "message": f"Found {len(formatted_results)} parts matching '{request.query}'"
            }
            
        except Exception as e:
            logger.error(f"Error in search_parts: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to search parts database"
            }
    
    def get_part_details(self, part_number: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific part by part number.
        Returns real part data with actual URLs and specifications.
        """
        try:
            part = self.db.get_part_by_number(part_number)
            
            if not part:
                return {
                    "success": False,
                    "message": f"Part {part_number} not found in database"
                }
            
            return {
                "success": True,
                "part": {
                    "part_number": part['part_number'],
                    "name": part['name'],
                    "description": part['description'],
                    "price": part['price'],
                    "brand": part['brand'],
                    "category": part['category'],
                    "product_url": part['product_url'],
                    "image_url": part['image_url'],
                    "in_stock": part['in_stock'],
                    "installation_guide": part.get('installation_guide'),
                    "install_video_url": part.get('install_video_url'),
                    "specifications": part.get('specifications', {})
                },
                "message": f"Found details for part {part_number}"
            }
            
        except Exception as e:
            logger.error(f"Error in get_part_details: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get details for part {part_number}"
            }
    
    def search_compatible_parts(self, request: CompatibilitySearchRequest) -> Dict[str, Any]:
        """
        Find parts compatible with a specific appliance model.
        Returns real compatibility data from the database.
        """
        try:
            results = self.db.search_compatible_parts(
                model_number=request.model_number,
                appliance_type=request.appliance_type
            )
            
            formatted_results = []
            for part in results:
                formatted_part = {
                    "part_number": part['part_number'],
                    "name": part['name'],
                    "description": part['description'],
                    "price": part['price'],
                    "brand": part['brand'],
                    "product_url": part['product_url'],
                    "model_number": part['model_number'],
                    "appliance_type": part['appliance_type']
                }
                formatted_results.append(formatted_part)
            
            return {
                "success": True,
                "model_number": request.model_number,
                "appliance_type": request.appliance_type,
                "total_results": len(formatted_results),
                "compatible_parts": formatted_results,
                "message": f"Found {len(formatted_results)} parts compatible with model {request.model_number}"
            }
            
        except Exception as e:
            logger.error(f"Error in search_compatible_parts: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to search compatible parts for model {request.model_number}"
            }
    
    def search_repair_guides(self, request: RepairSearchRequest) -> Dict[str, Any]:
        """
        Search for repair guides and troubleshooting information.
        Returns real repair guides with actual video URLs and part recommendations.
        """
        try:
            results = self.db.search_repairs(
                symptom=request.symptom,
                appliance_type=request.appliance_type,
                limit=request.limit
            )
            
            formatted_results = []
            for repair in results:
                formatted_repair = {
                    "appliance_type": repair['appliance_type'],
                    "symptom": repair['symptom'],
                    "description": repair['description'],
                    "difficulty": repair['difficulty'],
                    "percentage_reported": repair['percentage_reported'],
                    "parts_needed": repair['parts_needed'],
                    "symptom_detail_url": repair['symptom_detail_url'],
                    "repair_video_url": repair['repair_video_url']
                }
                formatted_results.append(formatted_repair)
            
            return {
                "success": True,
                "symptom": request.symptom,
                "appliance_type": request.appliance_type,
                "total_results": len(formatted_results),
                "repair_guides": formatted_results,
                "message": f"Found {len(formatted_results)} repair guides for '{request.symptom}'"
            }
            
        except Exception as e:
            logger.error(f"Error in search_repair_guides: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to search repair guides for '{request.symptom}'"
            }
    
    def search_blog_content(self, request: BlogSearchRequest) -> Dict[str, Any]:
        """
        Search for blog articles and educational content.
        Returns real blog articles with actual URLs.
        """
        try:
            results = self.db.search_blogs(
                query=request.query,
                limit=request.limit
            )
            
            formatted_results = []
            for blog in results:
                formatted_blog = {
                    "title": blog['title'],
                    "url": blog['url'],
                    "excerpt": blog['excerpt'],
                    "author": blog['author'],
                    "date_published": blog['date_published'],
                    "category": blog['category'],
                    "snippet": blog.get('snippet', '')
                }
                formatted_results.append(formatted_blog)
            
            return {
                "success": True,
                "query": request.query,
                "total_results": len(formatted_results),
                "blog_articles": formatted_results,
                "message": f"Found {len(formatted_results)} blog articles about '{request.query}'"
            }
            
        except Exception as e:
            logger.error(f"Error in search_blog_content: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to search blog content for '{request.query}'"
            }
    
    def get_available_brands(self, appliance_type: str = None) -> Dict[str, Any]:
        """Get list of available brands in the database"""
        try:
            brands = self.db.get_brands(appliance_type=appliance_type)
            
            return {
                "success": True,
                "appliance_type": appliance_type,
                "brands": brands,
                "total_brands": len(brands),
                "message": f"Found {len(brands)} brands" + (f" for {appliance_type}" if appliance_type else "")
            }
            
        except Exception as e:
            logger.error(f"Error in get_available_brands: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get available brands"
            }
    
    def get_price_range(self, category: str = None) -> Dict[str, Any]:
        """Get price range for parts in a category"""
        try:
            min_price, max_price = self.db.get_price_range(category=category)
            
            return {
                "success": True,
                "category": category,
                "min_price": min_price,
                "max_price": max_price,
                "message": f"Price range: ${min_price:.2f} - ${max_price:.2f}" + (f" for {category}" if category else "")
            }
            
        except Exception as e:
            logger.error(f"Error in get_price_range: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get price range"
            }

# Tool functions that can be called by LLM
def search_parts_tool(query: str, brand: str = None, category: str = None, 
                     max_price: float = None, in_stock_only: bool = True, limit: int = 10) -> str:
    """Search for appliance parts with filters"""
    tools = PartSelectDatabaseTools()
    request = PartSearchRequest(
        query=query,
        brand=brand,
        category=category,
        max_price=max_price,
        in_stock_only=in_stock_only,
        limit=limit
    )
    result = tools.search_parts(request)
    return json.dumps(result, indent=2)

def get_part_details_tool(part_number: str) -> str:
    """Get detailed information about a specific part"""
    tools = PartSelectDatabaseTools()
    result = tools.get_part_details(part_number)
    return json.dumps(result, indent=2)

def search_compatible_parts_tool(model_number: str, appliance_type: str = None) -> str:
    """Find parts compatible with a specific appliance model"""
    tools = PartSelectDatabaseTools()
    request = CompatibilitySearchRequest(
        model_number=model_number,
        appliance_type=appliance_type
    )
    result = tools.search_compatible_parts(request)
    return json.dumps(result, indent=2)

def search_repair_guides_tool(symptom: str, appliance_type: str = None, limit: int = 10) -> str:
    """Search for repair guides and troubleshooting information"""
    tools = PartSelectDatabaseTools()
    request = RepairSearchRequest(
        symptom=symptom,
        appliance_type=appliance_type,
        limit=limit
    )
    result = tools.search_repair_guides(request)
    return json.dumps(result, indent=2)

def search_blog_content_tool(query: str, limit: int = 5) -> str:
    """Search for blog articles and educational content"""
    tools = PartSelectDatabaseTools()
    request = BlogSearchRequest(query=query, limit=limit)
    result = tools.search_blog_content(request)
    return json.dumps(result, indent=2)

def get_available_brands_tool(appliance_type: str = None) -> str:
    """Get list of available brands"""
    tools = PartSelectDatabaseTools()
    result = tools.get_available_brands(appliance_type)
    return json.dumps(result, indent=2)

def get_price_range_tool(category: str = None) -> str:
    """Get price range for parts in a category"""
    tools = PartSelectDatabaseTools()
    result = tools.get_price_range(category)
    return json.dumps(result, indent=2)

# Available tools for LLM
AVAILABLE_TOOLS = {
    "search_parts": {
        "function": search_parts_tool,
        "description": "Search for appliance parts with optional filters",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for parts"},
                "brand": {"type": "string", "description": "Filter by brand (optional)"},
                "category": {"type": "string", "description": "Filter by category (optional)"},
                "max_price": {"type": "number", "description": "Maximum price filter (optional)"},
                "in_stock_only": {"type": "boolean", "description": "Only show in-stock parts", "default": True},
                "limit": {"type": "integer", "description": "Maximum number of results", "default": 10}
            },
            "required": ["query"]
        }
    },
    "get_part_details": {
        "function": get_part_details_tool,
        "description": "Get detailed information about a specific part by part number",
        "parameters": {
            "type": "object",
            "properties": {
                "part_number": {"type": "string", "description": "Part number to lookup"}
            },
            "required": ["part_number"]
        }
    },
    "search_compatible_parts": {
        "function": search_compatible_parts_tool,
        "description": "Find parts compatible with a specific appliance model",
        "parameters": {
            "type": "object",
            "properties": {
                "model_number": {"type": "string", "description": "Appliance model number"},
                "appliance_type": {"type": "string", "description": "Type of appliance (refrigerator/dishwasher)"}
            },
            "required": ["model_number"]
        }
    },
    "search_repair_guides": {
        "function": search_repair_guides_tool,
        "description": "Search for repair guides and troubleshooting information",
        "parameters": {
            "type": "object",
            "properties": {
                "symptom": {"type": "string", "description": "Problem description or symptom"},
                "appliance_type": {"type": "string", "description": "Type of appliance (refrigerator/dishwasher)"},
                "limit": {"type": "integer", "description": "Maximum number of results", "default": 10}
            },
            "required": ["symptom"]
        }
    },
    "search_blog_content": {
        "function": search_blog_content_tool,
        "description": "Search for blog articles and educational content",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for blog content"},
                "limit": {"type": "integer", "description": "Maximum number of results", "default": 5}
            },
            "required": ["query"]
        }
    },
    "get_available_brands": {
        "function": get_available_brands_tool,
        "description": "Get list of available brands in the database",
        "parameters": {
            "type": "object",
            "properties": {
                "appliance_type": {"type": "string", "description": "Filter by appliance type (optional)"}
            }
        }
    },
    "get_price_range": {
        "function": get_price_range_tool,
        "description": "Get price range for parts in a category",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Part category to check (optional)"}
            }
        }
    }
}

if __name__ == "__main__":
    # Test the tools
    tools = PartSelectDatabaseTools()
    
    print("Testing part search...")
    result = tools.search_parts(PartSearchRequest(query="water filter", limit=3))
    print(f"Found {result.get('total_results', 0)} parts")
    
    print("\nTesting repair search...")
    result = tools.search_repair_guides(RepairSearchRequest(symptom="leaking", appliance_type="dishwasher"))
    print(f"Found {result.get('total_results', 0)} repair guides")
