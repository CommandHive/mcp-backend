from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from routes.auth import router as auth_router
from routes.servers import router as servers_router
from routes.chat import router as chat_router
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
pprint(auth_router.routes)
routes = [
    Route("/", homepage),
    Mount("/auth", auth_router)
]

app = Starlette(
    routes=routes,
    middleware=middleware
)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)