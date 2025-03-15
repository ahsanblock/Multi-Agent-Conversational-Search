from crewai import Agent
from langchain.tools import Tool
from typing import Dict, Any, List
from ..models.schemas import UserProfile, SearchResult, Product

class PersonalizationAgent:
    """
    Agent responsible for personalizing search results based on user preferences and history.
    Adjusts rankings and filters based on user profile data.
    """
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialize the Personalization Agent
        
        Args:
            settings (Dict[str, Any]): Application configuration settings
        """
        self.settings = settings
        
    def get_agent(self) -> Agent:
        """
        Create and return the CrewAI agent for personalization
        
        Returns:
            Agent: The configured CrewAI agent
        """
        return Agent(
            role='Personalization Specialist',
            goal='Personalize search results based on user preferences and history',
            backstory="""You are an expert in user behavior analysis and personalization. 
            Your role is to analyze user preferences and history to provide tailored 
            search results that match their interests and needs.""",
            tools=[
                Tool(
                    name='get_user_profile',
                    func=self.get_user_profile,
                    description='Retrieve user profile and preferences'
                ),
                Tool(
                    name='personalize_results',
                    func=self.personalize_results,
                    description='Adjust search results based on user preferences'
                )
            ],
            verbose=self.settings.debug
        )
        
    async def get_user_profile(self, user_id: str) -> UserProfile:
        """
        Retrieve user profile and preferences
        
        Args:
            user_id (str): The user's identifier
            
        Returns:
            UserProfile: The user's profile data
        """
        # This is a placeholder - in practice, you'd fetch this from your user database
        return UserProfile(
            user_id=user_id,
            preferences={
                'favorite_categories': ['electronics', 'books'],
                'price_range': {'min': 0, 'max': 1000},
                'brands': ['apple', 'samsung', 'sony'],
                'size_preferences': {'clothing': 'M', 'shoes': '42'},
                'color_preferences': ['blue', 'black', 'white']
            },
            search_history=[
                {
                    'query': 'bluetooth headphones',
                    'timestamp': '2024-03-20T10:00:00Z',
                    'clicked_products': ['product123', 'product456']
                }
            ]
        )
        
    async def personalize_results(
        self,
        results: List[SearchResult],
        user_profile: UserProfile
    ) -> List[SearchResult]:
        """
        Adjust search results based on user preferences
        
        Args:
            results (List[SearchResult]): Original search results
            user_profile (UserProfile): User's profile and preferences
            
        Returns:
            List[SearchResult]: Personalized search results
        """
        personalized_results = []
        
        for result in results:
            # Calculate personalization score
            personalization_score = self._calculate_personalization_score(
                result.product,
                user_profile
            )
            
            # Create a new SearchResult with personalization score
            personalized_result = SearchResult(
                product=result.product,
                relevance_score=result.relevance_score,
                personalization_score=personalization_score,
                explanation=result.explanation
            )
            
            # Add explanation if score is significant
            if personalization_score > 0.7:
                personalized_result.explanation = self._generate_personalization_explanation(
                    result.product,
                    user_profile
                )
                
            personalized_results.append(personalized_result)
            
        # Sort by combined relevance and personalization score
        personalized_results.sort(
            key=lambda x: (x.relevance_score + (x.personalization_score or 0)) / 2,
            reverse=True
        )
        
        return personalized_results
        
    def _calculate_personalization_score(
        self,
        product: Product,
        user_profile: UserProfile
    ) -> float:
        """
        Calculate personalization score for a product based on user preferences
        
        Args:
            product (Product): Product data
            user_profile (UserProfile): User's profile
            
        Returns:
            float: Personalization score between 0 and 1
        """
        score = 0.0
        weights = {
            'category': 0.3,
            'brand': 0.2,
            'price': 0.2,
            'color': 0.15,
            'size': 0.15
        }
        
        # Category match
        if product.category in user_profile.preferences.get('favorite_categories', []):
            score += weights['category']
            
        # Brand match
        if product.attributes.get('brand') in user_profile.preferences.get('brands', []):
            score += weights['brand']
            
        # Price range match
        price_range = user_profile.preferences.get('price_range', {})
        if price_range:
            if price_range['min'] <= product.price <= price_range['max']:
                score += weights['price']
                
        # Color preference match
        if product.attributes.get('color') in user_profile.preferences.get('color_preferences', []):
            score += weights['color']
            
        # Size preference match
        size_prefs = user_profile.preferences.get('size_preferences', {})
        if product.category in size_prefs:
            if product.attributes.get('size') == size_prefs[product.category]:
                score += weights['size']
                
        return min(score, 1.0)
        
    def _generate_personalization_explanation(
        self,
        product: Product,
        user_profile: UserProfile
    ) -> str:
        """
        Generate explanation for why a product was personalized
        
        Args:
            product (Product): Product data
            user_profile (UserProfile): User's profile
            
        Returns:
            str: Personalization explanation
        """
        reasons = []
        
        if product.category in user_profile.preferences.get('favorite_categories', []):
            reasons.append(f"Matches your interest in {product.category}")
            
        if product.attributes.get('brand') in user_profile.preferences.get('brands', []):
            reasons.append(f"From {product.attributes.get('brand')}, one of your preferred brands")
            
        if product.attributes.get('color') in user_profile.preferences.get('color_preferences', []):
            reasons.append(f"Available in {product.attributes.get('color')}, a color you like")
            
        if reasons:
            return "Recommended because: " + "; ".join(reasons)
        return ""
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the personalization task
        
        Args:
            input_data (Dict[str, Any]): Input data including results and user ID
            
        Returns:
            Dict[str, Any]: Personalized results
        """
        user_id = input_data.get('user_id')
        results = input_data.get('results', [])
        
        if not user_id:
            return {'results': results}  # Return unpersonalized results
            
        # Get user profile
        user_profile = await self.get_user_profile(user_id)
        
        # Convert dictionary results to SearchResult objects if needed
        search_results = []
        for result in results:
            if isinstance(result, dict):
                # Convert dictionary to SearchResult
                product_data = result.get('product', {})
                search_results.append(SearchResult(
                    product=Product(
                        id=str(product_data.get('id', '')),
                        name=str(product_data.get('name', '')),
                        description=str(product_data.get('description', '')),
                        price=float(product_data.get('price', 0.0)),
                        category=str(product_data.get('category', '')),
                        attributes=product_data.get('attributes', {})
                    ),
                    relevance_score=float(result.get('relevance_score', 0.5)),
                    personalization_score=result.get('personalization_score'),
                    explanation=result.get('explanation')
                ))
            else:
                search_results.append(result)
        
        # Personalize results
        personalized_results = await self.personalize_results(search_results, user_profile)
        
        # Convert back to dictionaries for response
        serialized_results = []
        for result in personalized_results:
            serialized_results.append({
                'product': {
                    'id': result.product.id,
                    'name': result.product.name,
                    'description': result.product.description,
                    'price': float(result.product.price),
                    'category': result.product.category,
                    'attributes': result.product.attributes
                },
                'relevance_score': result.relevance_score,
                'personalization_score': result.personalization_score,
                'explanation': result.explanation
            })
        
        return {
            'results': serialized_results,
            'user_profile': user_profile,
            'personalization_applied': True
        } 