"""Mock product data for testing"""

MOCK_PRODUCTS = [
    {
        "id": "phone_1",
        "name": "UltraPhone Pro Max",
        "description": "High-end smartphone with exceptional camera quality and performance",
        "price": 899.99,
        "category": "Smartphones",
        "attributes": {
            "brand": "UltraPhone",
            "color": "Midnight Blue",
            "storage": "256GB",
            "camera": "108MP",
            "battery": "5000mAh",
            "screen": "6.7 inch AMOLED",
            "camera_score": 95,
            "performance_score": 92,
            "battery_score": 88
        }
    },
    {
        "id": "phone_2",
        "name": "BudgetKing 5G",
        "description": "Best value smartphone with great features at an affordable price",
        "price": 399.99,
        "category": "Smartphones",
        "attributes": {
            "brand": "BudgetKing",
            "color": "Forest Green",
            "storage": "128GB",
            "camera": "64MP",
            "battery": "4500mAh",
            "screen": "6.5 inch LCD",
            "camera_score": 82,
            "performance_score": 78,
            "battery_score": 85
        }
    },
    {
        "id": "laptop_1",
        "name": "GameMaster X",
        "description": "Ultimate gaming laptop with RTX 4080 and 32GB RAM",
        "price": 2499.99,
        "category": "Laptops",
        "attributes": {
            "brand": "GameMaster",
            "color": "Black",
            "cpu": "Intel i9-13900H",
            "gpu": "RTX 4080",
            "ram": "32GB",
            "storage": "2TB SSD",
            "screen": "17.3 inch 240Hz",
            "gaming_score": 98,
            "performance_score": 95,
            "battery_score": 75
        }
    },
    {
        "id": "laptop_2",
        "name": "WorkPro Ultra",
        "description": "Professional laptop for content creators and developers",
        "price": 1799.99,
        "category": "Laptops",
        "attributes": {
            "brand": "WorkPro",
            "color": "Silver",
            "cpu": "AMD Ryzen 9",
            "gpu": "RTX 4060",
            "ram": "64GB",
            "storage": "1TB SSD",
            "screen": "15.6 inch 4K",
            "content_creation_score": 94,
            "performance_score": 90,
            "battery_score": 85
        }
    }
]

def get_mock_products():
    """Return the list of mock products"""
    return MOCK_PRODUCTS

def get_mock_product_by_id(product_id: str):
    """Get a mock product by its ID"""
    return next((p for p in MOCK_PRODUCTS if p["id"] == product_id), None) 