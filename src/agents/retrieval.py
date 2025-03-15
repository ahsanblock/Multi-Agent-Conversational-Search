from astrapy import DataAPIClient, Collection
from langchain.tools import Tool
from langchain_openai import OpenAIEmbeddings
from typing import Dict, Any, List
from ..models.schemas import Product, SearchQuery, SearchResult
from ..config.settings import settings
import numpy as np
import logging

logger = logging.getLogger(__name__)

class RetrievalAgent:
    """
    Agent responsible for retrieving relevant products and information from various data sources.
    Handles both structured (SQL/NoSQL) and unstructured (vector) data retrieval.
    """
    
    def __init__(self):
        """Initialize basic attributes"""
        self.agent_settings = None
        self.embeddings = None
        self.astra_collection = None
    
    @classmethod
    async def create(cls, agent_settings: Dict[str, Any]):
        """Factory method to create and initialize the agent"""
        self = cls()
        self.agent_settings = agent_settings
        
        # Initialize OpenAI embeddings
        if settings.OPENAI_API_KEY:
            try:
                self.embeddings = OpenAIEmbeddings(
                    api_key=settings.OPENAI_API_KEY,
                    model="text-embedding-3-small"  # Cheaper model
                )
                logger.info("Successfully initialized OpenAI embeddings with text-embedding-3-small model")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI embeddings: {str(e)}")
        
        # Initialize Astra DB collection
        try:
            logger.info("Initializing Astra DB connection...")
            client = DataAPIClient(settings.ASTRA_DB_TOKEN)
            database = client.get_database(settings.ASTRA_DB_ENDPOINT)
            self.astra_collection = database.get_collection("product_search")
            logger.info("Successfully initialized Astra DB collection 'product_search'")
            
            # Test the connection
            try:
                test_result = self.astra_collection.find_one({})
                if test_result:
                    logger.info("Successfully tested Astra DB connection and found a record")
                else:
                    logger.info("Successfully tested Astra DB connection but no records found")
                    # Initialize sample products if no records exist
                    await self.initialize_sample_products()
            except Exception as e:
                logger.error(f"Failed to test Astra DB connection: {str(e)}")
                raise
                
        except Exception as e:
            logger.error(f"Failed to initialize Astra DB: {str(e)}")
            logger.error(f"Token (first 10 chars): {settings.ASTRA_DB_TOKEN[:10]}...")
            logger.error(f"Endpoint: {settings.ASTRA_DB_ENDPOINT}")
            raise
            
        return self
    
    async def vector_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search using embeddings
        
        Args:
            query (str): The search query
            top_k (int): Number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of similar products
        """
        if not self.embeddings:
            logger.info("Using keyword search - OpenAI embeddings not available")
            return await self._keyword_search(query, top_k)
            
        try:
            # Generate query embedding
            query_embedding = await self.embeddings.aembed_query(query)
            
            # Search in Astra DB collection
            results = await self._vector_search(query_embedding, top_k)
            
            if not results:
                logger.warning("No results from vector search, falling back to keyword search")
                return await self._keyword_search(query, top_k)
                
            return results
        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            return await self._keyword_search(query, top_k)
            
    async def _vector_search(self, query_vector: List[float], top_k: int) -> List[SearchResult]:
        """
        Search for similar products using vector similarity
        
        Args:
            query_vector (List[float]): Query embedding vector
            top_k (int): Number of results to return
            
        Returns:
            List[SearchResult]: List of similar products with search metadata
        """
        try:
            if not self.astra_collection:
                logger.error("Astra DB collection not initialized")
                return []

            # First, check if we have any documents at all
            all_docs = list(self.astra_collection.find({}, limit=1))
            logger.debug(f"Sample document from collection: {all_docs[0] if all_docs else 'No documents found'}")
                
            # Ensure query_vector is a list
            if not isinstance(query_vector, list):
                query_vector = query_vector.tolist()
            
            logger.debug(f"Performing vector search with dimensions: {len(query_vector)}")
            
            # Perform vector search with proper syntax
            cursor = self.astra_collection.find(
                filter={},
                sort={"$vector": query_vector},  # Sort by vector similarity (as a JSON object)
                limit=top_k,
                include_similarity=True
            )
            
            # Convert cursor to list
            records = list(cursor)
            logger.debug(f"Vector search returned {len(records)} records")
            
            if records:
                logger.debug(f"First record structure: {records[0]}")
            
            if not records:
                logger.warning("No records found in vector search response")
                return []
                
            # Process and score each product
            products = []
            for record in records:
                try:
                    # Skip non-dict records
                    if not isinstance(record, dict):
                        continue
                        
                    # Extract product data with proper type conversion
                    product_data = Product(
                        id=str(record.get("_id", "")),
                        name=str(record.get("name", "")),
                        description=str(record.get("description", "")),
                        price=float(record.get("price", 0.0)),
                        category=str(record.get("category", "")),
                        attributes={
                            "subcategory": str(record.get("subcategory", "")),
                            "brand": str(record.get("brand", "")),
                            "features": record.get("features", []),
                            "rating": float(record.get("rating", 0.0))
                        }
                    )
                    
                    # Get similarity score from vector search
                    similarity = float(record.get("$similarity", 0.5))
                    
                    # Create SearchResult object
                    search_result = SearchResult(
                        product=product_data,
                        relevance_score=similarity,
                        personalization_score=None,
                        explanation=None
                    )
                    
                    products.append(search_result)
                except Exception as e:
                    logger.error(f"Error processing record: {str(e)}")
                    logger.error(f"Record data: {record}")
                    continue
                    
            # Sort by score and return top_k
            products.sort(key=lambda x: x.relevance_score, reverse=True)
            return products[:top_k]
            
        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            return []
            
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.5
            
    async def _keyword_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Fallback keyword-based search when vector search is not available"""
        try:
            if not self.astra_collection:
                logger.error("Astra DB collection not initialized")
                return []
                
            # Get all records from product_search collection
            cursor = self.astra_collection.find(
                filter={},
                limit=50
            )
            
            # Convert cursor to list
            records = list(cursor)
            
            if not records:
                logger.warning("No records found in response")
                return []
                
            # Convert query to lowercase for case-insensitive matching
            query = query.lower()
            query_terms = set(query.split())
            
            # Process and score each product
            products = []
            for record in records:
                try:
                    # Skip non-dict records
                    if not isinstance(record, dict):
                        continue
                        
                    # Extract product data with proper type conversion
                    product_data = Product(
                        id=str(record.get("_id", "")),
                        name=str(record.get("name", "")),
                        description=str(record.get("description", "")),
                        price=float(record.get("price", 0.0)),
                        category=str(record.get("category", "")),
                        attributes={
                            **record.get("attributes", {}),
                            "relevance_score": float(record.get("relevance_score", 0.5)),
                            "popularity_score": float(record.get("popularity_score", 0.5)),
                            "rating": float(record.get("rating", 0.0))
                        }
                    )
                    
                    # Calculate match score based on keyword presence
                    name_desc = (product_data.name + " " + product_data.description).lower()
                    category = product_data.category.lower()
                    attributes = " ".join(str(v) for v in product_data.attributes.values()).lower()
                    
                    # Count matching terms in different fields
                    name_desc_matches = sum(1 for term in query_terms if term in name_desc)
                    category_matches = sum(1 for term in query_terms if term in category)
                    attribute_matches = sum(1 for term in query_terms if term in attributes)
                    
                    # Calculate weighted score
                    match_score = (
                        name_desc_matches * 0.5 +  # Name and description matches
                        category_matches * 0.3 +   # Category matches
                        attribute_matches * 0.2    # Attribute matches
                    ) / len(query_terms)  # Normalize by query length
                    
                    # Combine with existing relevance score
                    base_score = float(record.get("relevance_score", 0.5))
                    final_score = (match_score + base_score) / 2
                    
                    # Create SearchResult object
                    search_result = SearchResult(
                        product=product_data,
                        relevance_score=final_score,
                        personalization_score=None,
                        explanation=None
                    )
                    
                    products.append(search_result)
                except Exception as e:
                    logger.error(f"Error processing record: {str(e)}")
                    logger.error(f"Record data: {record}")
                    continue
                    
            # Sort by score and return top_k
            products.sort(key=lambda x: x.relevance_score, reverse=True)
            return products[:top_k]
            
        except Exception as e:
            logger.error(f"Error in keyword search: {str(e)}")
            return []
        
    async def structured_search(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """
        Search in structured data sources (e.g., SQL database)
        
        Args:
            query (SearchQuery): The search query with filters
            
        Returns:
            List[Dict[str, Any]]: List of matching products
        """
        # Return mock data for now
        return []
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the retrieval task
        
        Args:
            input_data (Dict[str, Any]): Input data including query and parameters
            
        Returns:
            Dict[str, Any]: Retrieved results with a valid response structure
        """
        query = input_data.get('query')
        if not query:
            raise ValueError("Query is required for retrieval")
            
        try:
            # Perform vector search
            vector_results = await self.vector_search(query)
            
            # Perform structured search if needed
            structured_results = []
            if input_data.get('use_structured_search', False):
                structured_results = await self.structured_search(
                    SearchQuery(**input_data)
                )
                
            # Combine and deduplicate results
            all_results = self._combine_results(vector_results, structured_results)
            
            # Convert SearchResult objects to dictionaries
            serializable_results = []
            for result in all_results:
                serializable_results.append({
                    "product": {
                        "id": result.product.id,
                        "name": result.product.name,
                        "description": result.product.description,
                        "price": result.product.price,
                        "category": result.product.category,
                        "attributes": result.product.attributes
                    },
                    "relevance_score": result.relevance_score,
                    "personalization_score": result.personalization_score,
                    "explanation": result.explanation
                })
            
            # Ensure we return a valid response structure even with no results
            response = {
                'results': serializable_results,
                'total_results': len(serializable_results),
                'sources': ['vector_store', 'structured_db'] if structured_results else ['vector_store'],
                'query': query,
                'success': True,
                'error': None,
                'messages': [
                    {
                        'role': 'system',
                        'content': 'Search results processed successfully.'
                    }
                ]
            }
            
            # Add a message if no results were found
            if not serializable_results:
                response['messages'].append({
                    'role': 'assistant',
                    'content': f'No products found matching your query: "{query}". Try broadening your search terms or using different keywords.'
                })
            
            return response
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error executing retrieval task: {error_msg}")
            
            # Return a valid error response structure
            return {
                'results': [],
                'total_results': 0,
                'sources': [],
                'query': query,
                'success': False,
                'error': error_msg,
                'messages': [
                    {
                        'role': 'system',
                        'content': 'An error occurred while processing your search.'
                    },
                    {
                        'role': 'assistant',
                        'content': 'I apologize, but I encountered an error while searching. Please try again with different search terms.'
                    }
                ]
            }
        
    def _combine_results(
        self,
        vector_results: List[Dict[str, Any]],
        structured_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Combine and deduplicate results from different sources
        
        Args:
            vector_results (List[Dict[str, Any]]): Results from vector search
            structured_results (List[Dict[str, Any]]): Results from structured search
            
        Returns:
            List[Dict[str, Any]]: Combined and deduplicated results
        """
        # Use a dictionary to deduplicate by product ID
        combined = {}
        
        # Add vector results
        for result in vector_results:
            product_id = result.product.id
            if product_id not in combined or result.relevance_score > combined[product_id].relevance_score:
                combined[product_id] = result
                
        # Add structured results
        for result in structured_results:
            product_id = result.product.id
            if product_id not in combined or result.relevance_score > combined[product_id].relevance_score:
                combined[product_id] = result
                
        return list(combined.values())
        
    async def initialize_sample_products(self):
        """Initialize sample products with proper vector embeddings"""
        sample_products = [
            {
                "_id": "laptop_1",
                "name": "Dell XPS 15 Laptop",
                "description": "High-performance laptop with 15.6\" 4K OLED display, Intel Core i9, 32GB RAM, 1TB SSD",
                "price": 1999.99,
                "category": "Electronics",
                "subcategory": "Laptops",
                "brand": "Dell",
                "features": [
                    "4K OLED Display",
                    "Intel Core i9",
                    "32GB RAM",
                    "1TB SSD",
                    "NVIDIA RTX 3050 Ti"
                ],
                "rating": 4.8
            },
            {
                "_id": "laptop_2",
                "name": "ASUS ROG Strix G15 Gaming Laptop",
                "description": "Powerful gaming laptop with AMD Ryzen 9, RTX 4070, 16GB RAM, 1TB NVMe SSD",
                "price": 1699.99,
                "category": "Electronics",
                "subcategory": "Gaming Laptops",
                "brand": "ASUS",
                "features": [
                    "165Hz Display",
                    "AMD Ryzen 9",
                    "16GB RAM",
                    "RTX 4070",
                    "RGB Keyboard"
                ],
                "rating": 4.7
            },
            {
                "_id": "laptop_3",
                "name": "MacBook Air M2",
                "description": "Ultra-thin laptop with Apple M2 chip, 13.6\" Liquid Retina display, 8GB RAM, 256GB SSD",
                "price": 1199.99,
                "category": "Electronics",
                "subcategory": "Laptops",
                "brand": "Apple",
                "features": [
                    "M2 Chip",
                    "Liquid Retina Display",
                    "18-hour battery life",
                    "MagSafe charging",
                    "1080p webcam"
                ],
                "rating": 4.9
            },
            {
                "_id": "laptop_4",
                "name": "Lenovo ThinkPad X1 Carbon",
                "description": "Business laptop with Intel Core i7, 14\" WQUXGA display, 16GB RAM, 512GB SSD",
                "price": 1499.99,
                "category": "Electronics",
                "subcategory": "Business Laptops",
                "brand": "Lenovo",
                "features": [
                    "WQUXGA Display",
                    "Intel Core i7",
                    "16GB RAM",
                    "512GB SSD",
                    "Fingerprint reader"
                ],
                "rating": 4.6
            },
            {
                "_id": "desktop_1",
                "name": "HP Pavilion Gaming Desktop",
                "description": "Gaming desktop with AMD Ryzen 7, RTX 3060, 16GB RAM, 1TB SSD + 2TB HDD",
                "price": 1299.99,
                "category": "Electronics",
                "subcategory": "Gaming Desktops",
                "brand": "HP",
                "features": [
                    "AMD Ryzen 7",
                    "RTX 3060",
                    "16GB RAM",
                    "Dual Storage",
                    "RGB lighting"
                ],
                "rating": 4.5
            }
        ]
        
        for product in sample_products:
            try:
                success = await self.add_product(product)
                if success:
                    logger.info(f"Added product: {product['name']}")
                else:
                    logger.error(f"Failed to add product: {product['name']}")
            except Exception as e:
                logger.error(f"Error adding product {product['name']}: {str(e)}")

    async def _generate_product_embedding(self, product: Dict[str, Any]) -> List[float]:
        """
        Generate vector embedding for a product
        
        Args:
            product (Dict[str, Any]): Product data
            
        Returns:
            List[float]: Vector embedding
        """
        if not self.embeddings:
            logger.error("OpenAI embeddings not initialized")
            return None
        
        try:
            # Combine relevant product fields for embedding
            text_to_embed = f"{product['name']} {product['description']} {product['category']} {product['subcategory']} {product['brand']} {' '.join(product['features'])}"
            vector = await self.embeddings.aembed_query(text_to_embed)
            return vector
        except Exception as e:
            logger.error(f"Error generating product embedding: {str(e)}")
            return None

    async def add_product(self, product: Dict[str, Any]) -> bool:
        """
        Add a product to the collection with vector embedding
        
        Args:
            product (Dict[str, Any]): Product data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Generate vector embedding
            vector = await self._generate_product_embedding(product)
            if vector is None:
                logger.error("Failed to generate vector embedding for product")
                return False
            
            # Convert vector to list if it's not already
            if not isinstance(vector, list):
                vector = vector.tolist()
            
            # Add vector to product data
            product_with_vector = {
                **product,
                "$vector": vector  # Store vector with $ prefix
            }
            
            # Log the product data for debugging
            logger.debug(f"Inserting product with vector dimensions: {len(vector)}")
            logger.debug(f"Product data structure: {product_with_vector}")
            
            # Insert into Astra DB
            result = self.astra_collection.insert_one(product_with_vector)
            logger.info(f"Successfully added product: {product['name']}")
            return True
        except Exception as e:
            logger.error(f"Error adding product: {str(e)}")
            return False 