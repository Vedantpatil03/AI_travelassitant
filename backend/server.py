from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import base64
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
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
    session_id: str
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

# Initialize OpenAI services
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Helper function to create travel planning system message
def get_travel_system_message():
    return """You are an expert AI Travel Assistant specializing in creating personalized travel itineraries. 

Your role:
- Create detailed, practical travel plans based on user preferences
- Provide budget-conscious recommendations
- Suggest specific activities, accommodations, and dining options
- Consider travel logistics and timing
- Give insider tips for each destination
- Be enthusiastic and inspiring while remaining practical

Always ask clarifying questions if you need more information about:
- Budget range
- Travel dates/duration
- Group size
- Travel style (luxury, budget, adventure, cultural, etc.)
- Specific interests or requirements

Format your responses with clear sections and bullet points for easy reading."""

# Basic routes
@api_router.get("/")
async def root():
    return {"message": "AI Travel Assistant API is running!"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Chat endpoints
@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    try:
        # Store user message in database
        user_message_obj = ChatMessage(
            session_id=request.session_id,
            message=request.message,
            sender="user"
        )
        await db.chat_messages.insert_one(user_message_obj.dict())
        
        # Get chat history for context
        chat_history = await db.chat_messages.find(
            {"session_id": request.session_id}
        ).sort("timestamp", 1).to_list(length=50)
        
        # Initialize chat with OpenAI GPT-5
        chat = LlmChat(
            api_key=OPENAI_API_KEY,
            session_id=request.session_id,
            system_message=get_travel_system_message()
        ).with_model("openai", "gpt-5")
        
        # Enhance message with travel context
        enhanced_message = request.message
        if request.budget or request.location or request.duration or request.travelers:
            context_parts = []
            if request.budget:
                context_parts.append(f"Budget: {request.budget}")
            if request.location:
                context_parts.append(f"Destination: {request.location}")
            if request.duration:
                context_parts.append(f"Duration: {request.duration}")
            if request.travelers:
                context_parts.append(f"Number of travelers: {request.travelers}")
            
            enhanced_message = f"{request.message}\n\nTravel Context: {', '.join(context_parts)}"
        
        # Send message to AI
        user_message = UserMessage(text=enhanced_message)
        response = await chat.send_message(user_message)
        
        # Store AI response in database
        ai_message_obj = ChatMessage(
            session_id=request.session_id,
            message=response,
            sender="assistant"
        )
        await db.chat_messages.insert_one(ai_message_obj.dict())
        
        return ChatResponse(
            message=response,
            session_id=request.session_id
        )
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@api_router.post("/generate-trip-image", response_model=ImageResponse)
async def generate_trip_image(request: ImageRequest):
    try:
        # Initialize image generator
        image_gen = OpenAIImageGeneration(api_key=OPENAI_API_KEY)
        
        # Generate travel-themed image
        travel_prompt = f"Beautiful travel destination illustration: {request.prompt}. Modern, vibrant, inspiring travel photography style."
        
        images = await image_gen.generate_images(
            prompt=travel_prompt,
            model="gpt-image-1",
            number_of_images=1
        )
        
        if images and len(images) > 0:
            image_base64 = base64.b64encode(images[0]).decode('utf-8')
            return ImageResponse(
                image_base64=image_base64,
                session_id=request.session_id
            )
        else:
            raise HTTPException(status_code=500, detail="No image was generated")
            
    except Exception as e:
        logger.error(f"Image generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

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

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()