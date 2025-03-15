document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const productResults = document.getElementById('productResults');
    const error = document.getElementById('error');
    const errorMessage = document.getElementById('errorMessage');

    console.log('Script loaded and DOM ready'); // Debug log

    // Add click handlers for example searches
    const examples = document.querySelectorAll('.example-search');
    console.log(`Found ${examples.length} example searches`); // Debug log

    examples.forEach((example, index) => {
        console.log(`Setting up click handler for example ${index + 1}`); // Debug log
        example.addEventListener('click', function(e) {
            console.log(`Example ${index + 1} clicked`); // Debug log
            const searchText = this.querySelector('.text-gray-600').textContent;
            console.log('Search text:', searchText); // Debug log
            
            const cleanQuery = searchText.replace(/['"]/g, '');
            console.log('Clean query:', cleanQuery); // Debug log
            
            searchInput.value = cleanQuery;
            performSearch(cleanQuery);
        });
    });

    // Search function
    async function performSearch(query) {
        console.log('Performing search with query:', query); // Debug log
        
        if (!query.trim()) {
            console.log('Empty query, skipping search'); // Debug log
            return;
        }
        
        try {
            loading.classList.remove('hidden');
            results.classList.add('hidden');
            error.classList.add('hidden');

            console.log('Making API request...'); // Debug log
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query })
            });

            if (!response.ok) {
                console.error('API request failed:', response.status, response.statusText); // Debug log
                throw new Error(`Search request failed: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('API response:', data); // Debug log
            
            // Display product results
            if (data.products && data.products.length > 0) {
                console.log(`Displaying ${data.products.length} products`); // Debug log
                console.log('Product data received:', data.products); // Debug log

                productResults.innerHTML = data.products.map(product => `
                    <div class="product-card p-4 border rounded-lg hover:shadow-lg transition-shadow">
                        <div class="flex justify-between items-start mb-3">
                            <h3 class="font-semibold text-lg text-gray-900">${product.name || 'Unnamed Product'}</h3>
                            <span class="text-lg font-bold text-blue-600">
                                ${typeof product.price === 'number' ? `$${product.price.toFixed(2)}` : 'Price not available'}
                            </span>
                        </div>

                        <div class="mt-2">
                            <p class="text-sm text-gray-600">${product.description || 'No description available'}</p>
                        </div>

                        <div class="mt-3 flex items-center">
                            ${typeof product.rating === 'number' ? `
                                <span class="flex items-center text-yellow-500">
                                    ${'★'.repeat(Math.round(product.rating))}${'☆'.repeat(5 - Math.round(product.rating))}
                                    <span class="ml-1 text-gray-600">(${product.rating.toFixed(1)})</span>
                                </span>
                            ` : ''}
                            ${product.reviews_count ? `
                                <span class="ml-2 text-gray-500">${product.reviews_count} reviews</span>
                            ` : ''}
                        </div>
                    </div>
                `).join('');
            } else {
                console.log('No products in response'); // Debug log
                productResults.innerHTML = '<p class="text-gray-500">No products found.</p>';
            }

            results.classList.remove('hidden');
        } catch (err) {
            console.error('Search error:', err); // Debug log
            error.classList.remove('hidden');
            errorMessage.textContent = err.message;
        } finally {
            loading.classList.add('hidden');
        }
    }

    // Search button click handler
    searchButton.addEventListener('click', () => {
        console.log('Search button clicked'); // Debug log
        const query = searchInput.value.trim();
        performSearch(query);
    });

    // Enter key handler
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            console.log('Enter key pressed'); // Debug log
            const query = searchInput.value.trim();
            performSearch(query);
        }
    });

    console.log('All event handlers set up'); // Debug log
}); 