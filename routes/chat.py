from starlette.routing import Router
from starlette.responses import JSONResponse


async def chat_handler(request):
    return JSONResponse({"status": "hello world"})


router = Router([
    ("/", chat_handler, ["GET"])
])