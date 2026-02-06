"""Demo server for Playwright verification"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AppAdvice API Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEMO_APPS = [
    {
        "id": "1",
        "name": "ProCamera",
        "developer": "Cocologics",
        "category": "Photo & Video",
        "price": 0,
        "original_price": 14.99,
        "is_free": True,
        "rating": 4.8,
        "rating_count": 2847,
        "icon_url": "https://via.placeholder.com/120",
        "description": "Professional camera app with manual controls and RAW shooting.",
        "app_store_url": "#"
    },
    {
        "id": "2",
        "name": "Fantastical",
        "developer": "Flexibits",
        "category": "Productivity",
        "price": 0,
        "original_price": 4.99,
        "is_free": True,
        "rating": 4.9,
        "rating_count": 15234,
        "icon_url": "https://via.placeholder.com/120",
        "description": "Calendar and tasks app with natural language input.",
        "app_store_url": "#"
    },
    {
        "id": "3",
        "name": "Stardew Valley",
        "developer": "ConcernedApe",
        "category": "Games",
        "price": 2.99,
        "original_price": 4.99,
        "is_free": False,
        "rating": 4.7,
        "rating_count": 45231,
        "icon_url": "https://via.placeholder.com/120",
        "description": "Open-ended country life RPG with farming and adventure.",
        "app_store_url": "#"
    },
]

@app.get("/health")
def health():
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/api/v1/apps")
def list_apps(
    category: str = None,
    is_free: bool = None,
    page: int = 1,
    limit: int = 20
):
    apps = DEMO_APPS
    if category:
        apps = [a for a in apps if a["category"] == category]
    if is_free is not None:
        apps = [a for a in apps if a["is_free"] == is_free]
    return apps

@app.get("/api/v1/apps/deals")
def get_deals():
    return [a for a in DEMO_APPS if a["is_free"] or a["price"] < a["original_price"]]

@app.get("/api/v1/apps/categories/list")
def list_categories():
    return [
        {"name": "Productivity", "count": 245},
        {"name": "Photo & Video", "count": 189},
        {"name": "Games", "count": 523},
        {"name": "Graphics & Design", "count": 87},
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
