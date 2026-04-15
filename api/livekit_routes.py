from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from livekit import api

from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

class TokenRequest(BaseModel):
    room_name: str
    participant_name: str

from config import settings

@router.post("/livekit-token")
async def get_livekit_token(req: TokenRequest):
    """
    Generate an access token for client to join a LiveKit room.
    """
    api_key = settings.livekit_api_key
    api_secret = settings.livekit_api_secret

    if not api_key or not api_secret:
        raise HTTPException(status_code=500, detail="LIVEKIT_API_KEY and LIVEKIT_API_SECRET are not set in environment.")

    # Use VideoGrants instead of VideoGrant for the current LiveKit Python SDK
    grant = api.VideoGrants(room_join=True, room=req.room_name)
    access_token = api.AccessToken(api_key, api_secret)
    access_token = access_token.with_identity(req.participant_name)
    access_token = access_token.with_name(req.participant_name)
    access_token = access_token.with_grants(grant)
    
    return {"token": access_token.to_jwt()}
