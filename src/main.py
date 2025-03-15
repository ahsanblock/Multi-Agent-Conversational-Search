from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, Any, List
import logging.config
import json
import asyncio
from crewai import Agent, Task, Crew, Process
import time

from .config import settings
from .models.schemas import SearchQuery, SearchResponse, Product
from .agents.planner import PlannerAgent
from .agents.retrieval import RetrievalAgent
from .agents.personalization import PersonalizationAgent
from .agents.ranking import RankingAgent
from .agents.response_generator import ResponseGeneratorAgent
from .agents.guardrails import GuardrailsAgent

# Configure logging
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'colored': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'colored',
            'level': 'INFO'
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO'
    },
    'loggers': {
        'src': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        }
    }
})

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Conversational Search System",
    description="Multi-agent conversational search system using CrewAI and LangChain",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="ui/static"), name="static")

class QueryOrchestrator:
    """
    Orchestrates the multi-agent system for processing search queries.
    Coordinates between different agents to plan, retrieve, personalize,
    rank, and generate responses.
    """
    
    def __init__(self):
        """Initialize basic attributes"""
        self.planner = None
        self.retrieval = None
        self.personalization = None
        self.ranking = None
        self.response_generator = None
        self.guardrails = None
    
    @classmethod
    async def create(cls):
        """Factory method to create and initialize the orchestrator"""
        self = cls()
        try:
            logger.info("🚀 Initializing QueryOrchestrator...")
            self.planner = PlannerAgent(settings=settings)
            self.retrieval = await RetrievalAgent.create(agent_settings=settings)
            self.personalization = PersonalizationAgent(settings=settings)
            self.ranking = RankingAgent(settings=settings)
            self.response_generator = ResponseGeneratorAgent(settings=settings)
            self.guardrails = GuardrailsAgent(settings=settings)
            logger.info("✅ QueryOrchestrator initialized successfully")
            return self
        except Exception as e:
            logger.error(f"❌ Error initializing QueryOrchestrator: {str(e)}")
            raise
            
    async def process_query(self, query: SearchQuery) -> SearchResponse:
        """
        Process a search query through the multi-agent system
        
        Args:
            query (SearchQuery): The search query to process
            
        Returns:
            SearchResponse: The search results and AI response
        """
        try:
            start_time = time.time()
            logger.info(f"📝 Processing query: '{query.query}'")
            
            # Step 1: Plan the query execution
            plan = await self._execute_planning(query)
            logger.info(f"📋 Query plan generated: {json.dumps(plan, indent=2)}")
            
            # Step 2: Execute retrieval based on plan
            retrieval_results = await self._execute_retrieval(query, plan)
            logger.info(f"🔍 Retrieved {len(retrieval_results)} results")
            
            # Step 3: Personalize results if needed
            if plan.get('needs_personalization', False):
                logger.info("👤 Applying personalization...")
                try:
                    retrieval_results = await self._execute_personalization(
                        query, retrieval_results
                    )
                except Exception as e:
                    logger.error(f"Error in personalization phase: {str(e)}")
            
            # Step 4: Rank results based on plan criteria
            try:
                ranked_results = await self._execute_ranking(
                    query, retrieval_results, plan
                )
                logger.info(f"📊 Ranked {len(ranked_results)} results")
            except Exception as e:
                logger.error(f"Error in ranking phase: {str(e)}")
                ranked_results = retrieval_results
            
            # Step 5: Generate response
            try:
                response = await self._execute_response_generation(
                    query, ranked_results, plan
                )
            except Exception as e:
                logger.error(f"Error in response generation phase: {str(e)}")
                response = {"generated_response": "I found some products that match your search, but I'm having trouble generating a detailed response."}
            
            # Calculate processing time
            processing_time = time.time() - start_time
            logger.info(f"⏱️ Query processed in {processing_time:.2f} seconds")
            
            # Prepare the products list from ranked results
            products = []
            for result in ranked_results:
                if isinstance(result, dict) and 'product' in result:
                    products.append(result['product'])
            
            return SearchResponse(
                query=query.query,
                products=products,
                ai_response=response.get('generated_response', 'No results found.'),
                total_results=len(products),
                processing_time=processing_time,
                filters_applied=query.filters or {},
                suggestions=response.get('suggestions', [])
            )
            
        except Exception as e:
            logger.error(f"❌ Error processing query: {str(e)}", exc_info=True)
            return self._generate_fallback_response(query)
            
    async def _execute_planning(self, query: SearchQuery) -> Dict[str, Any]:
        """Execute the planning phase"""
        try:
            plan = await self.planner.execute({
                'query': query.query,
                'user_id': query.user_id,
                'filters': query.filters,
                'context': query.context
            })
            return plan
        except Exception as e:
            logger.error(f"Error in planning phase: {str(e)}")
            return {
                'query_type': 'product_search',
                'needs_personalization': False,
                'ranking_criteria': ['relevance'],
                'response_type': 'list'
            }
            
    async def _execute_retrieval(
        self,
        query: SearchQuery,
        plan: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute the retrieval phase"""
        try:
            results = await self.retrieval.execute({
                'query': query.query,
                'user_id': query.user_id,
                'filters': query.filters,
                'context': {**query.context, **plan}
            })
            
            # Ensure results are in the correct format
            retrieved_results = results.get('results', [])
            if retrieved_results:
                # Log the first result for debugging
                logger.debug(f"First result structure: {json.dumps(retrieved_results[0], indent=2)}")
            return retrieved_results
        except Exception as e:
            logger.error(f"Error in retrieval phase: {str(e)}")
            return []
            
    async def _execute_personalization(
        self,
        query: SearchQuery,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute the personalization phase"""
        try:
            logger.debug(f"🔍 Personalization input: {json.dumps(results, indent=2)}")  # Log input
            personalized = await self.personalization.execute({
                'results': results,
                'user_id': query.user_id,
                'context': query.context
            })
            return personalized.get('results', results)
        except Exception as e:
            logger.error(f"Error in personalization phase: {str(e)}")
            return results
            
    async def _execute_ranking(
        self,
        query: SearchQuery,
        results: List[Dict[str, Any]],
        plan: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute the ranking phase"""
        try:
            logger.debug(f"🔍 Ranking input: {json.dumps(results, indent=2)}")  # Log input
            ranked = await self.ranking.execute({
                'results': results,
                'criteria': plan.get('ranking_criteria', ['relevance']),
                'query_type': plan.get('query_type', 'product_search'),
                'context': query.context
            })
            return ranked.get('results', results)
        except Exception as e:
            logger.error(f"Error in ranking phase: {str(e)}")
            return results
            
    async def _execute_response_generation(
        self,
        query: SearchQuery,
        results: List[Dict[str, Any]],
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the response generation phase"""
        try:
            # Ensure results is a list
            results_list = results if isinstance(results, list) else results.get('results', [])
            
            response = await self.response_generator.execute({
                'results': results_list,
                'query': query.query,
                'query_type': plan.get('query_type', 'product_search'),
                'response_type': plan.get('response_type', 'list'),
                'user_data': {'user_id': query.user_id, **query.context}
            })
            
            # Ensure response has required fields
            if not response:
                response = {
                    'generated_response': 'I found some products that might interest you.',
                    'suggestions': [],
                    'messages': [{
                        'role': 'assistant',
                        'content': 'I found some products that might interest you.'
                    }]
                }
            elif 'messages' not in response:
                response['messages'] = [{
                    'role': 'assistant',
                    'content': response.get('generated_response', 'I found some products that might interest you.')
                }]
                
            return response
            
        except Exception as e:
            logger.error(f"Error in response generation phase: {str(e)}")
            return {
                'generated_response': 'I found some products that might interest you.',
                'suggestions': [],
                'messages': [{
                    'role': 'assistant',
                    'content': 'I found some products that might interest you.'
                }]
            }
            
    def _generate_fallback_response(self, query: SearchQuery) -> SearchResponse:
        """Generate a fallback response when errors occur"""
        return SearchResponse(
            query=query.query,
            products=[
                Product(
                    id="mock_1",
                    name="Mock Wireless Headphones",
                    description="High-quality wireless headphones with noise cancellation",
                    price=199.99,
                    category="Electronics",
                    attributes={
                        "brand": "MockBrand",
                        "color": "Black",
                        "wireless": True
                    }
                )
            ],
            ai_response="I found a product that might interest you.",
            total_results=1,
            processing_time=0.0,
            filters_applied={}
        )

# Initialize orchestrator
orchestrator = None

@app.on_event("startup")
async def startup_event():
    """Initialize the orchestrator on startup"""
    global orchestrator
    orchestrator = await QueryOrchestrator.create()

@app.get("/")
async def read_root():
    return FileResponse("ui/index.html")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/api/search")
async def search(query: SearchQuery) -> SearchResponse:
    """
    Process a search query
    
    Args:
        query (SearchQuery): The search query
        
    Returns:
        SearchResponse: The search results and AI response
    """
    try:
        if not orchestrator:
            raise HTTPException(
                status_code=503,
                detail="Service is starting up, please try again in a moment"
            )
        return await orchestrator.process_query(query)
    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your search"
        ) 