from crewai import Agent
from langchain.tools import Tool
from typing import Dict, Any, List
import numpy as np
from ..models.schemas import SearchResult

class RankingAgent:
    """
    Agent responsible for ranking and prioritizing search results based on multiple factors.
    Combines relevance scores, business rules, and user signals to determine final ranking.
    """
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialize the Ranking Agent
        
        Args:
            settings (Dict[str, Any]): Application configuration settings
        """
        self.settings = settings
        
    def get_agent(self) -> Agent:
        """
        Create and return the CrewAI agent for ranking
        
        Returns:
            Agent: The configured CrewAI agent
        """
        return Agent(
            role='Search Ranking Specialist',
            goal='Optimize and rank search results for maximum relevance and business value',
            backstory="""You are an expert in search ranking algorithms and optimization. 
            Your role is to analyze and rank search results considering multiple factors 
            including relevance, personalization, business rules, and user behavior.""",
            tools=[
                Tool(
                    name='rank_results',
                    func=self.rank_results,
                    description='Rank search results based on multiple factors'
                ),
                Tool(
                    name='apply_business_rules',
                    func=self.apply_business_rules,
                    description='Apply business rules to search rankings'
                )
            ],
            verbose=self.settings.debug
        )
        
    async def rank_results(
        self,
        results: List[Dict[str, Any]],
        query_type: str,
        user_data: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank search results based on multiple factors
        
        Args:
            results (List[Dict[str, Any]]): Search results to rank
            query_type (str): Type of query (e.g., 'product_search', 'comparison')
            user_data (Dict[str, Any], optional): User data for personalized ranking
            
        Returns:
            List[Dict[str, Any]]: Ranked search results
        """
        # Calculate ranking scores
        for result in results:
            ranking_score = self._calculate_ranking_score(
                result,
                query_type,
                user_data
            )
            result['ranking_score'] = ranking_score
            
        # Sort results by ranking score
        ranked_results = sorted(
            results,
            key=lambda x: x.get('ranking_score', 0),
            reverse=True
        )
        
        return ranked_results
        
    async def apply_business_rules(
        self,
        results: List[Dict[str, Any]],
        rules: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply business rules to search rankings
        
        Args:
            results (List[Dict[str, Any]]): Search results to modify
            rules (Dict[str, Any]): Business rules to apply
            
        Returns:
            List[Dict[str, Any]]: Modified search results
        """
        for result in results:
            ranking_score = result.get('ranking_score', 0)
            
            # Apply promotion rules
            if self._should_promote(result, rules):
                ranking_score *= rules.get('promotion_boost', 1.2)
                
            # Apply demotion rules
            if self._should_demote(result, rules):
                ranking_score *= rules.get('demotion_factor', 0.8)
                
            # Apply category boosting
            product = result.get('product', {})
            if product.get('category') in rules.get('boosted_categories', []):
                ranking_score *= rules.get('category_boost', 1.1)
                
            # Update the ranking score
            result['ranking_score'] = ranking_score
            
        # Re-sort results
        return sorted(results, key=lambda x: x.get('ranking_score', 0), reverse=True)
        
    def _calculate_ranking_score(
        self,
        result: Dict[str, Any],
        query_type: str,
        user_data: Dict[str, Any] = None
    ) -> float:
        """
        Calculate ranking score for a search result
        
        Args:
            result (Dict[str, Any]): Search result dictionary
            query_type (str): Type of query
            user_data (Dict[str, Any], optional): User data for personalization
            
        Returns:
            float: Ranking score
        """
        weights = self._get_weights(query_type)
        
        # Base score components - handle None values safely
        relevance_score = (result.get('relevance_score') or 0.0) * weights['relevance']
        personalization_score = (result.get('personalization_score') or 0.0) * weights['personalization']
        
        # Business metrics
        popularity_score = self._calculate_popularity_score(result) * weights['popularity']
        conversion_score = self._calculate_conversion_score(result) * weights['conversion']
        
        # Combine scores
        final_score = (
            relevance_score +
            personalization_score +
            popularity_score +
            conversion_score
        )
        
        # Apply recency boost if needed
        if self._is_recent_product(result):
            final_score *= 1.1
            
        return final_score
        
    def _get_weights(self, query_type: str) -> Dict[str, float]:
        """
        Get scoring weights based on query type
        
        Args:
            query_type (str): Type of query
            
        Returns:
            Dict[str, float]: Weights for different ranking factors
        """
        weights = {
            'product_search': {
                'relevance': 0.4,
                'personalization': 0.3,
                'popularity': 0.2,
                'conversion': 0.1
            },
            'comparison': {
                'relevance': 0.3,
                'personalization': 0.2,
                'popularity': 0.25,
                'conversion': 0.25
            },
            'recommendation': {
                'relevance': 0.3,
                'personalization': 0.4,
                'popularity': 0.2,
                'conversion': 0.1
            }
        }
        
        return weights.get(query_type, weights['product_search'])
        
    def _calculate_popularity_score(self, result: Dict[str, Any]) -> float:
        """
        Calculate popularity score based on views, ratings, etc.
        
        Args:
            result (Dict[str, Any]): Search result dictionary
            
        Returns:
            float: Popularity score
        """
        # Get values with safe defaults
        product = result.get('product', {})
        attributes = product.get('attributes', {})
        views = attributes.get('views', 0)
        rating = attributes.get('rating', 0.0)
        return min((views / 1000) * (rating / 5), 1.0)
        
    def _calculate_conversion_score(self, result: Dict[str, Any]) -> float:
        """
        Calculate conversion score based on sales data
        
        Args:
            result (Dict[str, Any]): Search result dictionary
            
        Returns:
            float: Conversion score
        """
        # Get values with safe defaults
        product = result.get('product', {})
        attributes = product.get('attributes', {})
        conversions = attributes.get('conversions', 0)
        views = max(attributes.get('views', 1), 1)  # Avoid division by zero
        return min(conversions / views, 1.0)
        
    def _is_recent_product(self, result: Dict[str, Any]) -> bool:
        """
        Check if product is recently added
        
        Args:
            result (Dict[str, Any]): Search result dictionary
            
        Returns:
            bool: Whether product is recent
        """
        product = result.get('product', {})
        attributes = product.get('attributes', {})
        days_since_added = attributes.get('days_since_added', 100)
        return days_since_added < 30
        
    def _should_promote(self, result: Dict[str, Any], rules: Dict[str, Any]) -> bool:
        """
        Check if result should be promoted based on business rules
        
        Args:
            result (Dict[str, Any]): Search result dictionary
            rules (Dict[str, Any]): Business rules
            
        Returns:
            bool: Whether to promote the result
        """
        product = result.get('product', {})
        
        # Check promotion criteria
        if product.get('id') in rules.get('promoted_products', []):
            return True
            
        if product.get('category') in rules.get('promoted_categories', []):
            return True
            
        if product.get('attributes', {}).get('margin', 0) >= rules.get('min_margin_for_promotion', 0):
            return True
            
        return False
        
    def _should_demote(self, result: SearchResult, rules: Dict[str, Any]) -> bool:
        """
        Check if result should be demoted based on business rules
        
        Args:
            result (SearchResult): Search result
            rules (Dict[str, Any]): Business rules
            
        Returns:
            bool: Whether to demote the result
        """
        product = result.product
        
        # Check demotion criteria
        if product.id in rules.get('demoted_products', []):
            return True
            
        if product.attributes.get('stock_level', 0) < rules.get('min_stock_level', 0):
            return True
            
        if product.attributes.get('margin', 0) < rules.get('min_margin', 0):
            return True
            
        return False
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the ranking task
        
        Args:
            input_data (Dict[str, Any]): Input data including results and ranking parameters
            
        Returns:
            Dict[str, Any]: Ranked results and metadata
        """
        results = input_data.get('results', [])
        query_type = input_data.get('query_type', 'product_search')
        user_data = input_data.get('user_data')
        business_rules = input_data.get('business_rules', {})
        
        # Rank results
        ranked_results = await self.rank_results(results, query_type, user_data)
        
        # Apply business rules
        if business_rules:
            ranked_results = await self.apply_business_rules(ranked_results, business_rules)
            
        return {
            'results': ranked_results,
            'ranking_applied': True,
            'ranking_factors': self._get_weights(query_type)
        } 