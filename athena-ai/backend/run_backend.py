import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

config = uvicorn.Config("app.main:app", host="127.0.0.1", port=8000, reload=False)
server = uvicorn.Server(config)

if sys.platform == "win32":
    loop = asyncio.SelectorEventLoop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.serve())
else:
    asyncio.run(server.serve())
