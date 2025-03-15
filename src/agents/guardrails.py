from crewai import Agent
from langchain.tools import Tool
from typing import Dict, Any, List
import re
from ..models.schemas import SearchResult, SearchResponse

class GuardrailsAgent:
    """
    Agent responsible for ensuring content compliance and safety.
    Validates and filters responses based on content policies and business rules.
    """
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialize the Guardrails Agent
        
        Args:
            settings (Dict[str, Any]): Application configuration settings
        """
        self.settings = settings
        self.initialize_filters()
        
    def initialize_filters(self):
        """Initialize content filters and rules"""
        # Offensive content patterns
        self.offensive_patterns = [
            r'\b(hate|offensive|discriminatory|racist|sexist)\b',
            # Add more patterns as needed
        ]
        
        # Sensitive content categories
        self.sensitive_categories = [
            'adult',
            'weapons',
            'drugs',
            # Add more categories as needed
        ]
        
        # Business rule violations
        self.business_rules = {
            'min_price': 0.01,
            'max_price': 1000000,
            'required_fields': ['name', 'price', 'description'],
            'banned_keywords': ['counterfeit', 'fake', 'replica']
        }
        
    def get_agent(self) -> Agent:
        """
        Create and return the CrewAI agent for guardrails
        
        Returns:
            Agent: The configured CrewAI agent
        """
        return Agent(
            role='Content Safety Specialist',
            goal='Ensure content compliance and safety in search results',
            backstory="""You are an expert in content moderation and compliance. 
            Your role is to validate and filter search results and responses to 
            ensure they meet safety standards and business rules.""",
            tools=[
                Tool(
                    name='validate_content',
                    func=self.validate_content,
                    description='Validate content against safety rules'
                ),
                Tool(
                    name='filter_results',
                    func=self.filter_results,
                    description='Filter results based on compliance rules'
                )
            ],
            verbose=self.settings.debug
        )
        
    async def validate_content(
        self,
        content: str,
        content_type: str = 'response'
    ) -> Dict[str, Any]:
        """
        Validate content against safety rules
        
        Args:
            content (str): Content to validate
            content_type (str): Type of content ('response' or 'product')
            
        Returns:
            Dict[str, Any]: Validation results
        """
        issues = []
        
        # Check for offensive content
        for pattern in self.offensive_patterns:
            if re.search(pattern, content.lower()):
                issues.append({
                    'type': 'offensive_content',
                    'pattern': pattern,
                    'severity': 'high'
                })
                
        # Check for sensitive content
        for category in self.sensitive_categories:
            if category in content.lower():
                issues.append({
                    'type': 'sensitive_content',
                    'category': category,
                    'severity': 'medium'
                })
                
        # Check business rule violations
        for keyword in self.business_rules['banned_keywords']:
            if keyword in content.lower():
                issues.append({
                    'type': 'business_rule_violation',
                    'rule': f'banned_keyword_{keyword}',
                    'severity': 'high'
                })
                
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'content_type': content_type
        }
        
    async def filter_results(
        self,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Filter results based on compliance rules
        
        Args:
            results (List[SearchResult]): Search results to filter
            
        Returns:
            List[SearchResult]: Filtered results
        """
        filtered_results = []
        
        for result in results:
            # Validate price range
            if not self._validate_price(result.product.price):
                continue
                
            # Check required fields
            if not self._validate_required_fields(result.product):
                continue
                
            # Validate product content
            validation = await self.validate_content(
                result.product.description,
                'product'
            )
            
            if validation['is_valid']:
                filtered_results.append(result)
                
        return filtered_results
        
    def _validate_price(self, price: float) -> bool:
        """
        Validate product price against business rules
        
        Args:
            price (float): Product price
            
        Returns:
            bool: Whether price is valid
        """
        return (
            self.business_rules['min_price'] <= price <= 
            self.business_rules['max_price']
        )
        
    def _validate_required_fields(self, product: Dict[str, Any]) -> bool:
        """
        Validate required product fields
        
        Args:
            product (Dict[str, Any]): Product data
            
        Returns:
            bool: Whether all required fields are present and valid
        """
        for field in self.business_rules['required_fields']:
            if not getattr(product, field, None):
                return False
        return True
        
    async def validate_response(
        self,
        response: SearchResponse
    ) -> SearchResponse:
        """
        Validate and potentially modify search response
        
        Args:
            response (SearchResponse): Search response to validate
            
        Returns:
            SearchResponse: Validated and potentially modified response
        """
        # Validate generated response
        response_validation = await self.validate_content(
            response.generated_response,
            'response'
        )
        
        if not response_validation['is_valid']:
            # Modify response to remove problematic content
            response.generated_response = await self._clean_response(
                response.generated_response,
                response_validation['issues']
            )
            
        # Filter results
        response.results = await self.filter_results(response.results)
        response.total_results = len(response.results)
        
        # Add compliance metadata if in debug mode
        if self.settings.debug:
            response.debug_info = {
                'compliance': {
                    'response_validation': response_validation,
                    'filtered_results_count': response.total_results
                }
            }
            
        return response
        
    async def _clean_response(
        self,
        response: str,
        issues: List[Dict[str, Any]]
    ) -> str:
        """
        Clean problematic content from response
        
        Args:
            response (str): Original response
            issues (List[Dict[str, Any]]): Identified issues
            
        Returns:
            str: Cleaned response
        """
        cleaned_response = response
        
        for issue in issues:
            if issue['type'] == 'offensive_content':
                # Replace offensive patterns with appropriate alternatives
                cleaned_response = re.sub(
                    issue['pattern'],
                    '[removed]',
                    cleaned_response,
                    flags=re.IGNORECASE
                )
            elif issue['type'] == 'sensitive_content':
                # Remove sentences containing sensitive content
                sentences = cleaned_response.split('.')
                cleaned_sentences = [
                    s for s in sentences
                    if issue['category'] not in s.lower()
                ]
                cleaned_response = '.'.join(cleaned_sentences)
                
        return cleaned_response
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the guardrails task
        
        Args:
            input_data (Dict[str, Any]): Input data including response to validate
            
        Returns:
            Dict[str, Any]: Validated and potentially modified response
        """
        response = SearchResponse(**input_data)
        
        # Apply validation and filtering
        validated_response = await self.validate_response(response)
        
        return validated_response.dict() 