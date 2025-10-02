import os
import time

from .definitions import *

# File: ./api/__init__.py
import uvicorn
from fastapi import FastAPI

# Import routers
from api.auth_api import router as auth_router
from api.data_api import router as data_router
from api.form_api import router as form_router

app = FastAPI(
    title="My Project API",
    description="Combined API (auth, data, form). OpenAPI (Swagger) available at /docs",
    version="1.0.0",
)

# Include routers from separate files
app.include_router(auth_router)
app.include_router(data_router)
app.include_router(form_router)


start_time = time.time()

def timeLine(point_number, description):
    """Log timeline point with exact time from start"""
    elapsed_time = time.time() - start_time
    print(f"[{elapsed_time:.3f}s] Timeline point {point_number}: {description}")

if __name__ == "__main__":
    timeLine(0, "Script started")
    # Run with: 
    ## ```python -m api```
    ## ```uvicorn api:app --reload --port 8000```
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)

