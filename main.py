from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from routes.auth import router as auth_router
from routes.servers import router as servers_router
from routes.chat import router as chat_router
from routes.test import router as test_router, lifespan
import uvicorn
from pprint import pprint


async def homepage(request):
    return JSONResponse({"message": "MCP Platform Backend API"})



middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
]
pprint(servers_router.routes)
routes = [
    Route("/", homepage),
    Mount("/auth", auth_router),
    Mount("/test", test_router),
    Mount("/servers", servers_router),
    Mount("/chat", chat_router)
]

app = Starlette(
    routes=routes,
    middleware=middleware,
    lifespan=lifespan
)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)