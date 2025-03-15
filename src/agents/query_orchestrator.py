from crewai import Agent, Task, Crew, Process
from langchain.tools import Tool
from typing import Dict, Any, List
import asyncio
import time

from ..models.schemas import SearchQuery, SearchResponse, AgentTask
from .planner import PlannerAgent
from .retrieval import RetrievalAgent
from .personalization import PersonalizationAgent
from .ranking import RankingAgent
from .response_generator import ResponseGeneratorAgent
from .guardrails import GuardrailsAgent

class QueryOrchestrator:
    """
    Orchestrates the multi-agent system for processing search queries.
    Coordinates between different specialized agents to produce the final response.
    """
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialize the Query Orchestrator with configuration settings
        
        Args:
            settings (Dict[str, Any]): Application configuration settings
        """
        self.settings = settings
        self.initialize_agents()
        
    def initialize_agents(self):
        """Initialize all agent instances"""
        self.planner = PlannerAgent(self.settings)
        self.retrieval = RetrievalAgent(self.settings)
        self.personalization = PersonalizationAgent(self.settings)
        self.ranking = RankingAgent(self.settings)
        self.response_generator = ResponseGeneratorAgent(self.settings)
        self.guardrails = GuardrailsAgent(self.settings)
        
    async def process_query(self, query: SearchQuery) -> SearchResponse:
        """
        Process a search query through the multi-agent system
        
        Args:
            query (SearchQuery): The search query to process
            
        Returns:
            SearchResponse: The processed search results and generated response
        """
        start_time = time.time()
        
        # Create CrewAI crew for this query
        crew = Crew(
            agents=[
                self.planner.get_agent(),
                self.retrieval.get_agent(),
                self.personalization.get_agent(),
                self.ranking.get_agent(),
                self.response_generator.get_agent(),
                self.guardrails.get_agent()
            ],
            tasks=[
                Task(
                    description=f"Process search query: {query.query}",
                    agent=self.planner.get_agent()
                )
            ],
            process=Process.sequential  # or Process.hierarchical based on needs
        )
        
        # Execute the crew's tasks
        result = await crew.kickoff()
        
        # Process results and create response
        processing_time = time.time() - start_time
        
        # Validate response through guardrails
        validated_response = await self.guardrails.validate_response(result)
        
        return SearchResponse(
            query=query.query,
            results=validated_response.results,
            total_results=len(validated_response.results),
            processing_time=processing_time,
            generated_response=validated_response.generated_response,
            filters_applied=query.filters or {},
            suggestions=validated_response.suggestions,
            debug_info=validated_response.debug_info if self.settings.debug else None
        )
    
    async def _execute_agent_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute a single agent task
        
        Args:
            task (AgentTask): The task to execute
            
        Returns:
            Dict[str, Any]: The task results
        """
        try:
            agent = getattr(self, task.agent_name.lower())
            result = await agent.execute(task.input_data)
            return {
                "status": "completed",
                "output": result
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            } 