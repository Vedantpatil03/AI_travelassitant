from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import os
import logging
import uuid
from openai import OpenAI

# =============================
# Setup & Environment
# =============================
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# MongoDB connection
mongo_url = os.getenv("MONGO_URL")
db_name = os.getenv("DB_NAME", "travel_db")

if not mongo_url:
    raise RuntimeError("MONGO_URL not set in .env file")

mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[db_name]

# OpenAI API setup
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(
    title="AI Travel Assistant API",
    description="Backend API for AI-powered travel assistant",
    version="1.0.0"
)
api_router = APIRouter(prefix="/api")

# =============================
# Models
# =============================

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    message: str
    sender: str  # 'user' or 'assistant'
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    budget: Optional[str] = None
    location: Optional[str] = None
    duration: Optional[str] = None
    travelers: Optional[int] = None

class ChatResponse(BaseModel):
    message: str
    session_id: str
    image_url: Optional[str] = None

class ImageRequest(BaseModel):
    prompt: str
    session_id: str

class ImageResponse(BaseModel):
    image_base64: str
    session_id: str

# =============================
# Routes
# =============================

@api_router.get("/")
async def root():
    return {"message": "AI Travel Assistant API is running!"}

# --- Status checks ---
@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(client_name=input.client_name)
    await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# --- Chat endpoint ---
@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    try:
        session_id = request.session_id or str(uuid.uuid4())

        # Save user message
        user_message_obj = ChatMessage(
            session_id=session_id,
            message=request.message,
            sender="user"
        )
        await db.chat_messages.insert_one(user_message_obj.dict())

        # Fetch last 5 messages for context
        history = await db.chat_messages.find(
            {"session_id": session_id}
        ).sort("timestamp", 1).to_list(length=5)

        messages = [{"role": msg["sender"], "content": msg["message"]} for msg in history]

        # Add system instructions
        messages.insert(0, {
            "role": "system",
            "content": "You are a helpful travel assistant. Always give unique, personalized plans."
        })

        # Add trip context
        if request.location or request.duration or request.budget or request.travelers:
            context = f"""
            Trip details:
            - Location: {request.location or 'not specified'}
            - Duration: {request.duration or 'not specified'}
            - Budget: {request.budget or 'not specified'}
            - Travelers: {request.travelers or 1}
            """
            messages.append({"role": "system", "content": context})

        # Call OpenAI
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        response = completion.choices[0].message.content

        # Save AI message
        ai_message_obj = ChatMessage(
            session_id=session_id,
            message=response,
            sender="assistant"
        )
        await db.chat_messages.insert_one(ai_message_obj.dict())

        return ChatResponse(
            message=response,
            session_id=session_id
        )

    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

# --- Image generation ---
@api_router.post("/generate-trip-image", response_model=ImageResponse)
async def generate_trip_image(request: ImageRequest):
    try:
       image_result = openai_client.images.generate(
    model="dall-e-3",
    prompt=request.prompt,
    size="1024x1024"  # or "auto"
        )
       image_base64 = image_result.data[0].b64_json


       return ImageResponse(
            image_base64=image_base64,
            session_id=request.session_id
        )

    except Exception as e:
        logger.error(f"Image generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

# --- Chat history ---
@api_router.get("/chat-history/{session_id}")
async def get_chat_history(session_id: str):
    try:
        messages = await db.chat_messages.find(
            {"session_id": session_id}
        ).sort("timestamp", 1).to_list(length=100)
        return [ChatMessage(**msg) for msg in messages]
    except Exception as e:
        logger.error(f"Chat history error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chat history")

# =============================
# Middleware & Logging
# =============================
app.include_router(api_router)

origins = os.getenv("CORS_ORIGINS", "*")
allowed_origins = ["*"] if origins == "*" else [o.strip() for o in origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    mongo_client.close()
