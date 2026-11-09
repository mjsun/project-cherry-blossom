from fastapi import FastAPI
from backend.api.router import api_router

app = FastAPI(title='Loan Q&A API')
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/home/")
def home():
    return "This is a bot for CMBS"



app.include_router(api_router, prefix='/api')