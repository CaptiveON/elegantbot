from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, chat
from app.models import Base, engine

Base.metadata.create_all(bind = engine)

app = FastAPI(
    title = "Simple Chat API",
    description= "A simple chat api",
    version="0.0.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins= ["http://localhost:3000"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Simple Chat api"}