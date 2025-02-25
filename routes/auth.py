import logging
import config
import asyncio
import httpx
from fastapi import APIRouter, Request
from modules.misc import save_tokens

logger = logging.getLogger("uvicorn.error.auth")

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.get("/{scope}/login")
async def auth_callback(scope, request: Request):
    """Handles authentication callback from Twitch."""

    logger.info(f"Got auth request for scope: {scope}")

    params = request.query_params

    state = params.get("state")
    code = params.get("code")

    app = request.app
    twitch_api = app.state.twitch_api
    twitch_chat = app.state.twitch_chat


    if not code:
        return {"error": "Authorization failed. No code received."}

    logger.info(f"✅ Received OAuth code for scope: {scope}")

    payload = {
        "client_id": config.TWITCH_CLIENT_ID,
        "client_secret": config.TWITCH_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": f"http://localhost:8000/auth/{scope}/login",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(config.TWITCH_TOKEN_URL, data=payload)
        token_data = response.json()

    if "access_token" in token_data:
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        save_tokens(scope, access_token, refresh_token)

        logger.info(f"✅ Authentication successful for {scope}")

        if scope == "api":
            # Restart Twitch bot after successful authentication
            if twitch_api.is_running:
                await twitch_api.stop()
            asyncio.create_task(twitch_api.initialize(app))

        elif scope == "bot":
                if twitch_chat.is_running:
                    await twitch_chat.stop()
                asyncio.create_task(twitch_chat.start_chat(app))# Restart bot with new tokens

        return {"message": f"Authentication successful! {scope} is restarting."}

    else:
        logger.error(f"❌ Failed to exchange OAuth code: {token_data}")
        return {"error": "Failed to get access token", "details": token_data}
