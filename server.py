from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"] ,
    allow_headers=["*"]
)

@app.get('/api/ping')
def ping():
    return {"message": "pong"}

# TODO: Add endpoints mirroring Streamlit functionality
