// Constants
const API_BASE_URL = '/api';
const DEBOUNCE_DELAY = 300;

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const suggestions = document.getElementById('suggestions');
const suggestionsList = document.getElementById('suggestionsList');
const loading = document.getElementById('loading');
const results = document.getElementById('results');
const aiResponse = document.getElementById('aiResponse');
const productResults = document.getElementById('productResults');
const error = document.getElementById('error');
const errorMessage = document.getElementById('errorMessage');

// State
let currentQuery = '';
let searchTimeout = null;

// Event Listeners
searchInput.addEventListener('input', handleSearchInput);
searchButton.addEventListener('click', handleSearch);
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleSearch();
    }
});

// Main search function
async function handleSearch() {
    const query = searchInput.value.trim();
    if (!query) return;
    
    currentQuery = query;
    showLoading();
    hideError();
    
    try {
        const response = await fetch(`${API_BASE_URL}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query,
                user_id: getUserId(),  // Get from localStorage or generate
                filters: {},  // Add filters if needed
                context: {}   // Add context if needed
            })
        });
        
        if (!response.ok) {
            throw new Error('Search request failed');
        }
        
        const data = await response.json();
        displayResults(data);
        
    } catch (err) {
        showError(err.message);
    } finally {
        hideLoading();
    }
}

// Handle search input with debouncing
function handleSearchInput(e) {
    const query = e.target.value.trim();
    
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }
    
    if (query.length < 2) {
        hideSuggestions();
        return;
    }
    
    searchTimeout = setTimeout(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query,
                    generate_suggestions: true
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to get suggestions');
            }
            
            const data = await response.json();
            displaySuggestions(data.suggestions || []);
            
        } catch (err) {
            console.error('Error fetching suggestions:', err);
        }
    }, DEBOUNCE_DELAY);
}

// Display Functions
function displayResults(data) {
    // Show results container
    results.classList.remove('hidden');
    results.classList.add('animate-fade-in');
    
    // Display AI response
    aiResponse.innerHTML = formatAIResponse(data.ai_response || 'No response available.');
    
    // Display product results
    productResults.innerHTML = (data.products || [])
        .map(product => createProductCard({ product }))
        .join('');
}

function displaySuggestions(suggestionsList) {
    if (!suggestionsList.length) {
        hideSuggestions();
        return;
    }
    
    suggestions.classList.remove('hidden');
    suggestionsList.innerHTML = suggestionsList
        .map(suggestion => createSuggestionTag(suggestion))
        .join('');
}

function createProductCard(result) {
    const { product, relevance_score, personalization_score, explanation } = result;
    
    // Base64 encoded placeholder image (light grey square with product icon)
    const placeholderImage = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iIzRBNTU2OCIvPjxwYXRoIGQ9Ik04NSA2NUgxMTVWMTM1SDg1VjY1WiIgZmlsbD0iI0EwQUVDMCIvPjwvc3ZnPg==';
    
    return `
        <div class="product-card p-4 rounded-lg shadow-md hover:shadow-lg transition-all">
            <div class="aspect-w-16 aspect-h-9 mb-4">
                <img src="${product.attributes?.image_url || placeholderImage}"
                     alt="${product.name}"
                     class="object-cover rounded-md w-full h-48"
                     onerror="this.onerror=null; this.src='${placeholderImage}';">
            </div>
            <h3 class="font-semibold text-lg mb-2 text-gray-100">${product.name}</h3>
            <p class="text-gray-400 text-sm mb-2">${product.description}</p>
            <div class="flex justify-between items-center mb-2">
                <span class="price-tag">${product.price.toFixed(2)}</span>
                <span class="text-sm text-gray-500">${product.category}</span>
            </div>
            ${explanation ? `
                <div class="mt-2 text-sm text-blue-400">
                    <svg class="inline w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 01-1 1H3a1 1 0 110-2h1a1 1 0 011 1zM8 16v-1h4v1a2 2 0 11-4 0zM12 14c.015-.34.208-.646.477-.859a4 4 0 10-4.954 0c.27.213.462.519.477.859h4z"/>
                    </svg>
                    ${explanation}
                </div>
            ` : ''}
        </div>
    `;
}

function createSuggestionTag(suggestion) {
    return `
        <button class="suggestion-tag" onclick="applySuggestion('${suggestion}')">
            ${suggestion}
        </button>
    `;
}

function formatAIResponse(response) {
    // Convert markdown-like formatting to HTML
    return response
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

// Utility Functions
function showLoading() {
    loading.classList.remove('hidden');
    results.classList.add('hidden');
}

function hideLoading() {
    loading.classList.add('hidden');
}

function showError(message) {
    error.classList.remove('hidden');
    errorMessage.textContent = message;
}

function hideError() {
    error.classList.add('hidden');
}

function hideSuggestions() {
    suggestions.classList.add('hidden');
}

function applySuggestion(suggestion) {
    searchInput.value = suggestion;
    handleSearch();
}

function getUserId() {
    let userId = localStorage.getItem('userId');
    if (!userId) {
        userId = 'user_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('userId', userId);
    }
    return userId;
}

// Dark mode detection
function updateTheme() {
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
}

// Initialize
updateTheme();
window.matchMedia('(prefers-color-scheme: dark)').addListener(updateTheme); 