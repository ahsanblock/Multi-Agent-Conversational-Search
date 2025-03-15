from crewai import Agent
from langchain.tools import Tool
from typing import Dict, Any, List
import json
import logging
from openai import AsyncOpenAI
from ..config.settings import settings

logger = logging.getLogger(__name__)

class PlannerAgent:
    """
    Agent responsible for planning the execution strategy for processing search queries.
    Determines which agents should be activated and in what order based on the query type.
    """
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialize the Planner Agent
        
        Args:
            settings (Dict[str, Any]): Application configuration settings
        """
        self.settings = settings
        self.openai_client = None
        if hasattr(self.settings, 'OPENAI_API_KEY') and self.settings.OPENAI_API_KEY:
            try:
                self.openai_client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)
                logger.info("Successfully initialized OpenAI client")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        
    def get_agent(self) -> Agent:
        """
        Create and return the CrewAI agent for planning
        
        Returns:
            Agent: The configured CrewAI agent
        """
        return Agent(
            role='Search Query Planner',
            goal='Plan and coordinate the execution of search queries',
            backstory="""You are an expert search query planner with deep knowledge of 
            e-commerce systems and search optimization. Your role is to analyze queries 
            and determine the most efficient execution strategy.""",
            tools=[
                Tool(
                    name='analyze_query',
                    func=self.analyze_query,
                    description='Analyze a search query to determine required agents and execution order'
                )
            ],
            verbose=self.settings.DEBUG if hasattr(self.settings, 'DEBUG') else False
        )
        
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze a search query to determine its type and required processing steps
        
        Args:
            query (str): The search query to analyze
            
        Returns:
            Dict[str, Any]: Query analysis results
        """
        if not self.openai_client or self.settings.MOCK_RESPONSES:
            return self._generate_mock_plan(query)
            
        try:
            # Generate plan using GPT-4
            prompt = f"""
            Analyze the following e-commerce search query and create a structured plan for processing it.
            
            Query: "{query}"
            
            Consider the following aspects:
            1. Query Type (e.g., product_search, comparison, recommendation, feature_search)
            2. Whether personalization would be beneficial
            3. What criteria should be used for ranking results
            4. What type of response would be most helpful
            
            Return your analysis as a JSON object with the following structure:
            {{
                "query_type": str,  # Type of query (product_search, comparison, recommendation, feature_search)
                "needs_personalization": bool,  # Whether to apply personalization
                "ranking_criteria": List[str],  # Criteria for ranking results
                "response_type": str  # Type of response to generate (list, comparison, recommendation)
            }}
            
            Only return the JSON object, no other text.
            """
            
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                max_tokens=500,
                temperature=0.0,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Parse the response
            try:
                plan = json.loads(response.choices[0].message.content)
                logger.info(f"Generated plan for query '{query}': {json.dumps(plan)}")
                return plan
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing OpenAI response: {str(e)}")
                return self._generate_mock_plan(query)
                
        except Exception as e:
            logger.error(f"Error generating plan: {str(e)}")
            return self._generate_mock_plan(query)
            
    def _generate_mock_plan(self, query: str) -> Dict[str, Any]:
        """Generate a basic plan when OpenAI is not available"""
        query = query.lower()
        
        # Default plan for simple queries
        plan = {
            'query_type': 'product_search',
            'needs_personalization': False,
            'ranking_criteria': ['relevance'],
            'response_type': 'list'
        }
        
        # Adjust plan based on query keywords
        if any(word in query for word in ['recommend', 'suggest', 'best', 'top']):
            plan.update({
                'query_type': 'recommendation',
                'needs_personalization': True,
                'ranking_criteria': ['relevance', 'rating', 'popularity'],
                'response_type': 'recommendation'
            })
            
        return plan
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the planning task
        
        Args:
            input_data (Dict[str, Any]): Input data including query and context
            
        Returns:
            Dict[str, Any]: Generated plan
        """
        query = input_data.get('query')
        if not query:
            raise ValueError("Query is required for planning")
            
        try:
            # Analyze query and generate plan
            plan = await self.analyze_query(query)
            
            # Add any additional context from input data
            plan['context'] = {
                'user_id': input_data.get('user_id'),
                'filters': input_data.get('filters', {}),
                **input_data.get('context', {})
            }
            
            return plan
        except Exception as e:
            logger.error(f"Error executing planning task: {str(e)}")
            raise 