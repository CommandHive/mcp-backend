from starlette.routing import Router
from starlette.responses import JSONResponse


async def servers_handler(request):
    return JSONResponse({"status": "hello world"})


router = Router([
    ("/", servers_handler, ["GET"])
])