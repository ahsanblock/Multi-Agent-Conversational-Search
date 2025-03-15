from crewai import Agent
from langchain.tools import Tool
from typing import Dict, Any, List, Optional
from ..models.schemas import SearchResult
from ..mcp import mcp_request
from ..config.settings import settings
import logging

logger = logging.getLogger(__name__)

class ResponseGeneratorAgent:
    """
    Agent responsible for generating natural language responses from search results.
    Uses Claude AI via MCP to create human-like, contextual responses.
    """
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialize the Response Generator Agent
        
        Args:
            settings (Dict[str, Any]): Application configuration settings
        """
        self.settings = settings
        logger.info("Initialized Response Generator Agent")
        
    def get_agent(self) -> Agent:
        """
        Create and return the CrewAI agent for response generation
        
        Returns:
            Agent: The configured CrewAI agent
        """
        return Agent(
            role='Response Generator',
            goal='Generate natural and helpful responses from search results',
            backstory="""You are an expert in natural language generation and 
            conversation design. Your role is to convert structured search results 
            into helpful, natural responses that highlight the most relevant information.""",
            tools=[
                Tool(
                    name='generate_response',
                    func=self.generate_response,
                    description='Generate natural language response from search results'
                ),
                Tool(
                    name='generate_suggestions',
                    func=self.generate_suggestions,
                    description='Generate relevant search suggestions'
                )
            ],
            verbose=self.settings.DEBUG if hasattr(self.settings, 'DEBUG') else False
        )
        
    async def generate_response(
        self,
        results: List[Dict[str, Any]],
        query: str,
        query_type: str,
        user_data: Dict[str, Any] = None
    ) -> str:
        """
        Generate natural language response from search results
        
        Args:
            results (List[Dict[str, Any]]): Search results to describe
            query (str): Original search query
            query_type (str): Type of query
            user_data (Dict[str, Any], optional): User data for personalization
            
        Returns:
            str: Generated natural language response
        """
        try:
            # Handle empty results case first
            if not results:
                return f"I couldn't find any products matching your search for '{query}'. Try broadening your search terms or using different keywords."
                
            # Log the first result for debugging
            if results:
                logger.debug(f"First result structure: {results[0]}")
                
            if not self.settings.MOCK_RESPONSES:
                # Prepare context for Claude
                context = self._prepare_context(results, query, query_type, user_data)
                
                # Generate response using Claude
                response = await self._generate_claude_response(
                    context,
                    self._get_response_template(query_type)
                )
                
                return response or f"I found {len(results)} products matching your search for '{query}', but I'm having trouble generating a detailed response."
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return self._generate_mock_response(results)
        
    async def generate_suggestions(
        self,
        results: List[Dict[str, Any]],
        query: str,
        user_data: Dict[str, Any] = None
    ) -> List[str]:
        """
        Generate relevant search suggestions using MCP
        
        Args:
            results (List[Dict[str, Any]]): Current search results
            query (str): Original search query
            user_data (Dict[str, Any], optional): User data for personalization
            
        Returns:
            List[str]: List of search suggestions
        """
        try:
            # Prepare context for suggestions
            context = {
                'query': query,
                'results': [r.get('product', {}).get('name', '') for r in results[:5] if isinstance(r, dict)],
                'categories': list(set(r.get('product', {}).get('category', '') for r in results if isinstance(r, dict))),
                'user_preferences': user_data.get('preferences', {}) if user_data else {}
            }
            
            # Use MCP to generate suggestions
            
            prompt = f"""
            Based on the search query "{query}" and the following product context:
            - Products: {', '.join(context['results'])}
            - Categories: {', '.join(context['categories'])}
            
            Generate 3-5 relevant alternative search suggestions that would help the user find similar or related products.
            Each suggestion should be on a new line without bullets or numbers.
            """
            
            response = await mcp_request(
                "generate_response",
                {
                    "prompt": prompt,
                    "max_tokens": 500,
                    "temperature": 0.7,
                    "model": settings.OPENAI_MODEL
                }
            )
            
            if response and isinstance(response, dict) and 'content' in response:
                # Parse suggestions into list
                suggestions = [
                    s.strip() for s in response['content'].split('\n')
                    if s.strip() and not s.startswith('-')
                ]
                return suggestions[:5]  # Limit to 5 suggestions
            else:
                logger.error(f"Unexpected response format from MCP: {response}")
                return []
                
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            return []
        
    def _prepare_context(
        self,
        results: List[Dict[str, Any]],
        query: str,
        query_type: str,
        user_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Prepare context for response generation
        
        Args:
            results (List[Dict[str, Any]]): Search results
            query (str): Original query
            query_type (str): Type of query
            user_data (Dict[str, Any], optional): User data
            
        Returns:
            Dict[str, Any]: Prepared context
        """
        try:
            processed_results = []
            for r in results[:5]:  # Focus on top 5 results
                if not isinstance(r, dict) or 'product' not in r:
                    continue
                    
                product = r.get('product', {})
                if not product:
                    continue
                    
                processed_results.append({
                    'name': product.get('name', ''),
                    'description': product.get('description', ''),
                    'price': product.get('price', 0.0),
                    'category': product.get('category', ''),
                    'relevance_score': r.get('score', 0.0),
                    'attributes': product.get('attributes', {}),
                    'rating': product.get('rating', 0.0)
                })
                
            return {
                'query': query,
                'query_type': query_type,
                'results': processed_results,
                'user_preferences': user_data.get('preferences', {}) if user_data else {},
                'total_results': len(results)
            }
            
        except Exception as e:
            logger.error(f"Error preparing context: {str(e)}")
            return {
                'query': query,
                'query_type': query_type,
                'results': [],
                'user_preferences': {},
                'total_results': 0
            }
        
    def _get_response_template(self, query_type: str) -> str:
        """
        Get response template based on query type
        
        Args:
            query_type (str): Type of query
            
        Returns:
            str: Response template
        """
        templates = {
            'product_search': """
                Based on your search for {query}, I found {total_results} products. 
                Here are the most relevant options:
                
                {results_summary}
                
                {personalization_note}
                
                Would you like more details about any of these products?
            """,
            'comparison': """
                Let me compare the products you're interested in:
                
                {comparison_summary}
                
                Key differences:
                {differences}
                
                Based on your preferences, I recommend {recommendation}.
            """,
            'recommendation': """
                Based on your preferences and search for {query}, here are my top recommendations:
                
                {recommendations}
                
                These recommendations are based on {criteria}.
            """
        }
        
        return templates.get(query_type, templates['product_search'])
        
    async def _generate_claude_response(
        self,
        context: Dict[str, Any],
        template: str
    ) -> str:
        """
        Generate response using Claude AI via MCP
        
        Args:
            context (Dict[str, Any]): Context for response generation
            template (str): Response template
            
        Returns:
            str: Generated response
        """
        try:
            # Format prompt for Claude
            prompt = f"""
            Context: {context}
            
            Template: {template}
            
            Generate a natural, helpful response that:
            1. Addresses the user's query directly
            2. Highlights the most relevant information
            3. Includes personalized explanations when available
            4. Maintains a conversational tone
            5. Provides clear next steps or suggestions
            
            Response:
            """
            
            # Use mock response if MOCK_RESPONSES is enabled
            if self.settings.MOCK_RESPONSES:
                return self._generate_mock_response(context.get('results', []))
                
            # Return mock response if no results
            if not context.get('results'):
                return f"I couldn't find any products matching your search for '{context.get('query', '')}'. Try broadening your search terms or using different keywords."
                
            # Use MCP to generate response
            
            response = await mcp_request(
                "generate_response",
                {
                    "prompt": prompt,
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "model": settings.OPENAI_MODEL
                }
            )
            
            if response and isinstance(response, dict) and 'content' in response:
                return response['content']
            else:
                logger.error(f"Unexpected response format from MCP: {response}")
                return self._generate_mock_response(context.get('results', []))
                
        except Exception as e:
            logger.error(f"Error in Claude response generation: {str(e)}")
            return self._generate_mock_response(context.get('results', []))
        
    def _generate_mock_response(self, results: List[Dict[str, Any]]) -> str:
        """Generate a mock response when Claude is not available"""
        try:
            if not results:
                return "I couldn't find any products matching your search criteria. Please try a different search or adjust your filters."
                
            # Get the top 3 products
            top_products = results[:3]
            
            # Generate a response based on the products
            response = "Here are some products that match your search:\n\n"
            
            for result in top_products:
                try:
                    # Extract product data safely
                    product = result.get('product', {}) if isinstance(result, dict) else {}
                    if not product:
                        continue
                        
                    # Basic product information
                    response += f"• {product.get('name', 'Unknown Product')}"
                    if product.get('description'):
                        response += f" - {product['description']}"
                    response += "\n"
                    
                    # Price
                    if 'price' in product:
                        try:
                            price = float(product['price'])
                            response += f"  Price: ${price:.2f}\n"
                        except (ValueError, TypeError):
                            pass
                            
                    # Attributes
                    attributes = product.get('attributes', {})
                    if isinstance(attributes, dict):
                        if 'camera_score' in attributes:
                            response += f"  Camera Score: {attributes['camera_score']}/100\n"
                        if 'performance_score' in attributes:
                            response += f"  Performance Score: {attributes['performance_score']}/100\n"
                        if 'battery_score' in attributes:
                            response += f"  Battery Score: {attributes['battery_score']}/100\n"
                            
                    # Rating
                    if 'rating' in product:
                        try:
                            rating = float(product['rating'])
                            response += f"  Rating: {rating:.1f} stars\n"
                        except (ValueError, TypeError):
                            pass
                            
                    response += "\n"
                    
                except Exception as e:
                    logger.error(f"Error processing product in mock response: {str(e)}")
                    continue
                    
            response += "\nWould you like more details about any of these products?"
            return response
            
        except Exception as e:
            logger.error(f"Error generating mock response: {str(e)}")
            return "I found some products that might interest you, but I'm having trouble generating a detailed response."
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the response generation task
        
        Args:
            input_data (Dict[str, Any]): Input data including results and parameters
            
        Returns:
            Dict[str, Any]: Generated response and metadata
        """
        try:
            # Extract results from the input data
            results = []
            if isinstance(input_data, dict):
                if isinstance(input_data.get('results'), list):
                    results = input_data['results']
                elif isinstance(input_data.get('results'), dict):
                    results = input_data['results'].get('results', [])
                    
            # Log the results structure for debugging
            logger.debug(f"Processing results structure: {results[:1] if results else 'No results'}")
            
            query = input_data.get('query', '')
            query_type = input_data.get('query_type', 'product_search')
            user_data = input_data.get('user_data')
            
            # Generate main response
            response = await self.generate_response(results, query, query_type, user_data)
            
            # Generate suggestions if needed
            suggestions = []
            if input_data.get('generate_suggestions', True):
                suggestions = await self.generate_suggestions(results, query, user_data)
                
            # Ensure we have a valid messages array
            messages = []
            if response:
                messages.append({
                    'role': 'assistant',
                    'content': response
                })
                
                # Add suggestions as a follow-up message if available
                if suggestions:
                    suggestion_text = "\n\nYou might also be interested in:\n" + "\n".join(f"- {s}" for s in suggestions)
                    messages.append({
                        'role': 'assistant',
                        'content': suggestion_text
                    })
            else:
                messages.append({
                    'role': 'assistant',
                    'content': 'I apologize, but I was unable to generate a response for your search.'
                })
                
            return {
                'generated_response': response,
                'suggestions': suggestions,
                'response_type': query_type,
                'messages': messages,
                'success': True,
                'error': None
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in response generation: {error_msg}")
            
            # Return a valid error response
            return {
                'generated_response': None,
                'suggestions': [],
                'response_type': 'error',
                'messages': [
                    {
                        'role': 'assistant',
                        'content': 'I apologize, but I encountered an error while generating a response. Please try again.'
                    }
                ],
                'success': False,
                'error': error_msg
            } 