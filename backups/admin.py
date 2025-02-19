from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request, Body
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from modules.db_manager import get_db, get_admin_buttons, AdminButton, ChatMessage, save_viewer, get_recent_events
from modules.db_manager import get_scheduled_messages, add_scheduled_message, remove_scheduled_message, get_categories, update_pool_message, get_scheduled_message_pool, add_message_to_pool, delete_message_from_pool, update_scheduled_message
from modules.websocket_handler import broadcast_message
from modules.sequence_runner import get_sequence_names
from twitchAPI.type import CustomRewardRedemptionStatus
import logging
import json
import config
import html

router = APIRouter(prefix="/admin", tags=["Admin Panel"])

logger = logging.getLogger("uvicorn.error.admin")

templates = Jinja2Templates(directory="templates")

@router.get("/buttons", response_class=HTMLResponse)
async def get_buttons(request: Request):
    """Retrieve all admin panel buttons as an HTML template."""
    buttons = get_admin_buttons()

    # ✅ Ensure valid response even when no buttons exist
    return templates.TemplateResponse("includes/admin_buttons.html", {
        "request": request,
        "buttons": buttons if buttons else []
    })

@router.post("/buttons/add/", response_class=HTMLResponse)
async def add_admin_button(request: Request, db: Session = Depends(get_db)):
    """Add a new button and return updated button list."""

    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"❌ JSON Decode Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON format")

    if "label" not in body or "action" not in body or "data" not in body:
        raise HTTPException(status_code=400, detail="Missing required fields (label, action, data)")

    button_data = json.dumps(body["data"]) if isinstance(body["data"], dict) else "{}"

    prompt = body.get("prompt", False)

    new_button = AdminButton(
        label=body["label"],
        action=body["action"],
        data=button_data,
        prompt=prompt
    )

    db.add(new_button)
    db.commit()
    db.refresh(new_button)

    buttons = db.query(AdminButton).all()

    # Swap only the button list
    return templates.TemplateResponse("includes/admin_buttons.html", {"request": request, "buttons": buttons})

@router.get("/buttons/edit/{button_id}", response_class=HTMLResponse)
def edit_admin_button(button_id: int, request: Request, db: Session = Depends(get_db)):
    """Retrieve the edit form for a specific button."""
    button = db.query(AdminButton).filter(AdminButton.id == button_id).first()
    if not button:
        raise HTTPException(status_code=404, detail="Button not found")

    # Safely decode JSON, fallback to empty dict if invalid
    try:
        button_data = json.loads(button.data) if button.data and button.data.strip() else {}
    except json.JSONDecodeError:
        button_data = {}

    sequence_names = get_sequence_names()
    return templates.TemplateResponse("includes/admin_edit_button.html", {
        "request": request,
        "button": button,
        "sequence_names": sequence_names,
        "button_data": json.dumps(button_data, indent=2)  # Pretty JSON
    })

@router.put("/buttons/update/{button_id}")
async def update_admin_button(button_id: int, request: Request, db: Session = Depends(get_db)):
    """Update an existing admin button."""
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"❌ JSON Decode Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON format")

    if "label" not in body or "action" not in body or "data" not in body:
        raise HTTPException(status_code=400, detail="Missing required fields (label, action, data)")

    button = db.query(AdminButton).filter(AdminButton.id == button_id).first()
    if not button:
        raise HTTPException(status_code=404, detail="Button not found")

    try:
        button_data = json.dumps(body["data"]) if isinstance(body["data"], dict) else "{}"
    except json.JSONDecodeError:
        button_data = "{}"

    prompt = bool(body.get("prompt", False))  # ✅ Explizit in Boolean umwandeln

    button.label = body["label"]
    button.action = body["action"]
    button.data = button_data
    button.prompt = prompt  # ✅ Prompt speichern

    db.commit()
    db.refresh(button)

    return templates.TemplateResponse("includes/admin_buttons.html", {"request": request, "buttons": db.query(AdminButton).all()})

@router.delete("/buttons/remove/{button_id}", response_class=HTMLResponse)
async def remove_admin_button(button_id: int, request: Request, db: Session = Depends(get_db)):
    """Remove a button and return updated list."""

    button = db.query(AdminButton).filter(AdminButton.id == button_id).first()
    if not button:
        raise HTTPException(status_code=404, detail="Button not found")

    db.delete(button)
    db.commit()

    buttons = db.query(AdminButton).all()

    # Swap only the button list
    return templates.TemplateResponse("includes/admin_buttons.html", {"request": request, "buttons": buttons})

@router.put("/buttons/reorder")
def reorder_buttons(updated_buttons: list[dict], db: Session = Depends(get_db)):
    """Update the order of admin buttons."""
    try:
        for button_data in updated_buttons:
            button = db.query(AdminButton).filter(AdminButton.id == button_data["id"]).first()
            if button:
                button.position = button_data["position"]
        db.commit()
        return {"message": "Button order updated"}
    except Exception as e:
        return {"error": f"Failed to update button order: {e}"}

@router.post("/update-viewer/{user_id}")
async def update_viewer(user_id: int, request: Request):
    """Fetch latest user info and update the viewer database."""

    twitch_api = request.app.state.twitch_api

    try:
        user_info = await twitch_api.get_user_info(user_id=user_id)

        if not user_info:
            raise HTTPException(status_code=404, detail="User not found in Twitch API")

        # Update viewer in DB
        save_viewer(
            twitch_id=user_id,
            login=user_info["login"],
            display_name=user_info["display_name"],
            account_type=user_info["type"],
            broadcaster_type=user_info["broadcaster_type"],
            profile_image_url=user_info["profile_image_url"],
            account_age="",
            follower_date=None,
            subscriber_date=None,
            color=user_info.get("color"),
            badges=",".join(user_info.get("badges", []))
        )

        # Broadcast update
        await broadcast_message({"admin_alert": {"type": "viewer_update", "user_id": user_id, "message": "Viewer info updated"}})

        return {"status": "success", "message": "Viewer information updated"}

    except Exception as e:
        logger.error(f"❌ Failed to update viewer: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update viewer: {str(e)}")

@router.delete("/delete-message/{message_id}", response_class=HTMLResponse)
async def delete_chat_message(message_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete a chat message from Twitch and the local database."""

    twitch_api = request.app.state.twitch_api  # Access `twitch_api` from `app.state`

    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    user_id = message.viewer_id  # Get Twitch user ID

    try:
        # Delete the message from Twitch chat
        await twitch_api.twitch.delete_chat_message(config.TWITCH_CHANNEL_ID, user_id, message_id)
        logger.info(f"🗑️ Deleted message {message_id} from Twitch chat.")
    except Exception as e:
        logger.warning(f"⚠️ Failed to delete Twitch chat message: {str(e)}")

    # Delete from local DB
    db.delete(message)
    db.commit()

    # Refresh the chat UI
    await broadcast_message({"admin_alert": {"type": "chat_update", "message": "Message deleted"}})

    return await get_chat_messages(db)

@router.post("/create-reward/")
async def create_channel_point_reward(request: Request):
    try:
        twitch_api = request.app.state.twitch_api
        data = await request.json()
        title = data.get("title")
        cost = data.get("cost")
        prompt = data.get("prompt", "")
        require_input = data.get("require_input", False)

        if not title or not cost:
            return {"status": "error", "message": "⚠️ Title and cost are required."}

        await twitch_api.twitch.create_custom_reward(
            broadcaster_id=config.TWITCH_CHANNEL_ID,
            title=title,
            cost=cost,
            prompt=prompt,
            is_enabled=True,
            is_user_input_required=require_input
        )

        logger.info(f"✅ Created new reward: {title} (Cost: {cost}, Requires Input: {require_input})")
        return {"status": "success", "message": f"✅ Reward '{title}' created!"}

    except Exception as e:
        logger.error(f"❌ Failed to create reward: {e}")
        return {"status": "error", "message": "❌ Failed to create reward. Check logs."}

async def get_all_custom_rewards(twitch_api):
    """Fetch all custom rewards from Twitch."""
    try:
        rewards = await twitch_api.twitch.get_custom_reward(broadcaster_id=config.TWITCH_CHANNEL_ID, only_manageable_rewards=True)
        return rewards
    except Exception as e:
        logger.error(f"Failed to fetch custom rewards: {e}")
        return []

async def get_pending_redemptions(twitch_api, rewards):
    """Fetch pending redemptions for each reward."""
    try:
        redemptions = []
        for reward in rewards:
            redemptions_generator = twitch_api.twitch.get_custom_reward_redemption(
                broadcaster_id=config.TWITCH_CHANNEL_ID,
                reward_id=reward.id,
                status=CustomRewardRedemptionStatus.UNFULFILLED
            )

            async for redemption in redemptions_generator:
                redemptions.append(redemption)

        return redemptions
    except Exception as e:
        logger.error(f"Failed to fetch pending redemptions: {e}")
        return []

@router.get("/rewards/", response_class=HTMLResponse)
async def get_rewards(request: Request):
    """Fetch and display the existing custom rewards."""
    try:
        twitch_api = request.app.state.twitch_api
        rewards = await twitch_api.twitch.get_custom_reward(broadcaster_id=config.TWITCH_CHANNEL_ID)

        if not rewards:
            return "<p class='text-gray-400'>No rewards available.</p>"

        reward_html = "".join(
            f"""
            <div class='bg-gray-800 p-3 rounded-md shadow-md flex justify-between items-center'>
                <div>
                    <p class='text-lg font-bold'>{reward.title}</p>
                    <p class='text-sm text-gray-400'>Cost: {reward.cost} | Requires Input: {"Yes" if reward.is_user_input_required else "No"}</p>
                    <p class='text-sm text-gray-500'>{reward.prompt}</p>
                </div>
                <button class='bg-red-500 px-3 py-1 rounded text-white'
                    onclick="deleteReward('{reward.id}')">🗑️ Delete</button>
            </div>
            """ for reward in rewards
        )

        return reward_html
    except Exception as e:
        logger.error(f"❌ Failed to fetch rewards: {e}")
        return "<p class='text-red-500'>Error fetching rewards.</p>"

@router.get("/pending-rewards", response_class=HTMLResponse)
async def get_pending_rewards(request: Request):
    """Retrieve all unfulfilled Twitch channel point redemptions."""
    twitch_api = request.app.state.twitch_api

    if not twitch_api:
        return "<p class='text-red-500 text-sm'>Twitch API not initialized!</p>"

    try:
        rewards = await get_all_custom_rewards(twitch_api)
        if not rewards:
            return "<p class='text-gray-500 text-sm'>No custom rewards found.</p>"

        redemptions = await get_pending_redemptions(twitch_api, rewards)
        if not redemptions:
            return "<p class='text-gray-500 text-sm'>No pending redemptions.</p>"

        html_output = "<div class='space-y-2'>"
        for redemption in redemptions:
            redeemed_at = redemption.redeemed_at.strftime('%d.%m.%Y %H:%M') if redemption.redeemed_at else "Unknown"

            html_output += f"""
            <div class='p-3 bg-gray-800 border border-gray-700 rounded-md shadow-sm'>
                <!-- First Line: Reward Name (Bold) -->
                <div class='font-semibold text-white'>{redemption.reward.title}</div>

                <!-- Second Line: Date (Small) -->
                <div class='text-xs text-gray-400'>{redeemed_at}</div>

                <!-- Third Line: User Input -->
                <div class='mt-2 text-gray-300 text-sm'>{html.escape(redemption.user_input)}</div>

                <!-- Fourth Line: Username (Yellow, Small) -->
                <div class='mt-1 text-xs text-yellow-400 font-semibold'>{redemption.user_name}</div>

                <!-- Buttons -->
                <div class='mt-2 flex space-x-2'>
                    <button class='bg-green-500 hover:bg-green-400 text-white px-2 py-1 text-xs rounded'
                            onclick="fulfillRedemption('{redemption.reward.id}', '{redemption.id}')">✔ Fulfill</button>
                    <button class='bg-red-500 hover:bg-red-400 text-white px-2 py-1 text-xs rounded'
                            onclick="cancelRedemption('{redemption.reward.id}', '{redemption.id}')">✖ Refund</button>
                </div>
            </div>
            """
        html_output += "</div>"

        return HTMLResponse(content=html_output)

    except Exception as e:
        logger.error(f"Error fetching pending redemptions: {e}")
        return "<p class='text-red-500 text-sm'>Error fetching pending redemptions.</p>"

@router.post("/fulfill-redemption")
async def fulfill_redemption(request: Request, reward_id: str = Body(...), redeem_id: str = Body(...)):
    """Mark a redemption as FULFILLED."""
    twitch_api = request.app.state.twitch_api

    try:
        await twitch_api.twitch.update_redemption_status(
            broadcaster_id=config.TWITCH_CHANNEL_ID,
            reward_id=reward_id,
            redemption_ids=[redeem_id],
            status=CustomRewardRedemptionStatus.FULFILLED
        )
        return {"status": "success", "message": "Redemption fulfilled"}
    except Exception as e:
        logger.error(f"❌ Failed to fulfill redemption: {e}")
        return {"status": "error", "message": "Failed to fulfill redemption"}

@router.post("/cancel-redemption")
async def cancel_redemption(request: Request, reward_id: str = Body(...), redeem_id: str = Body(...)):
    """Cancel a redemption."""
    twitch_api = request.app.state.twitch_api

    try:
        await twitch_api.twitch.update_redemption_status(
            broadcaster_id=config.TWITCH_CHANNEL_ID,
            reward_id=reward_id,
            redemption_ids=[redeem_id],
            status=CustomRewardRedemptionStatus.CANCELED
        )
        return {"status": "success", "message": "Redemption refunded"}
    except Exception as e:
        logger.error(f"❌ Failed to refund redemption: {e}")
        return {"status": "error", "message": "Failed to refund redemption"}

@router.delete("/delete-reward/{reward_id}")
async def delete_channel_point_reward(request: Request, reward_id: str):
    try:
        twitch_api = request.app.state.twitch_api
        logger.info(await twitch_api.twitch.delete_custom_reward(
            broadcaster_id=config.TWITCH_CHANNEL_ID,
            reward_id=reward_id
        ))

        logger.info(f"🗑️ Deleted reward {reward_id}")
        return {"status": "success", "message": "🗑️ Reward deleted."}

    except Exception as e:
        logger.error(f"❌ Failed to delete reward: {e}")
        return {"status": "error", "message": "❌ Failed to delete reward."}

@router.get("/events/", response_class=HTMLResponse)
async def get_events():
    """
    Retrieve the last 50 stored events and return them as an HTML snippet.
    """
    events = get_recent_events()

    if not events:
        return "<p class='text-center text-gray-400'>No events yet...</p>"

    event_html = ""

    for event in reversed(events):
        event_type = event.event_type.replace("_", " ").capitalize()
        username = event.username if event.username else "Unknown"
        timestamp = event.timestamp.strftime('%d.%m.%Y %H:%M:%S')

        if "admin_action" in event.event_type:
            color_class = "border-blue-500 bg-blue-900/20"
        elif "button_click" in event.event_type:
            color_class = "border-yellow-500 bg-yellow-900/20"
        elif "function_call" in event.event_type:
            color_class = "border-green-500 bg-green-900/20"
        elif "error" in event.event_type:
            color_class = "border-red-500 bg-red-900/20"
        elif "channel_point" in event.event_type:
            color_class = "border-lime-500 bg-lime-900/20"
        else:
            color_class = "border-gray-500 bg-gray-800"

        # **EXACT format as you requested**
        event_html += f"""
            <div class="p-3 mb-2 rounded-md shadow-md border-l-4 {color_class}">
                <!-- First Line: Action (Bold) -->
                <div class="font-semibold text-white">{event_type}</div>

                <!-- Second Line: Date (Small) -->
                <div class="text-xs text-gray-400">{timestamp}</div>

                <!-- Third Line: Details -->
                <div class="mt-2 text-gray-300 text-sm">{event.message}</div>

                <!-- Fourth Line: Username (Yellow, Small) -->
                <div class="mt-1 text-xs text-yellow-400 font-semibold">{username}</div>
            </div>
        """

    return HTMLResponse(content=event_html)

@router.get("/viewer-count", response_class=HTMLResponse)
async def get_viewer_count(request: Request):
    """Retrieve the current Twitch viewer count and return it as an HTML snippet."""
    twitch_api = request.app.state.twitch_api  # Ensure Twitch API is initialized

    if not twitch_api:
        return "<span class='text-red-500'>N/A</span>"

    try:
        stream_info = await twitch_api.get_stream_info()

        if not stream_info:
            return "<p class='text-red-500 font-bold'>🔴 Offline</p>"

        viewer_count = stream_info.viewer_count
        return f"<p class='text-green-400 font-bold'>{viewer_count}</p>"

    except Exception as e:
        print(f"❌ Error fetching viewer count: {e}")
        return "<span class='text-red-500'>N/A</span>"

# 📅 GET Scheduled Messages List
@router.get("/scheduled-messages", response_class=HTMLResponse)
async def scheduled_messages(request: Request):
    messages = get_scheduled_messages()
    return templates.TemplateResponse("includes/admin_scheduled_messages.html", {
        "request": request,
        "messages": messages
    })

# Add Scheduled Message
@router.post("/scheduled-messages/add", response_model=dict)
async def create_or_update_scheduled_message(data: dict = Body(...)):
    """HTMX endpoint to add or update a scheduled message."""

    message_id = data.get("id")  # Check if it's an existing message
    message = data.get("message", "")
    interval = data.get("interval")
    category = data.get("category") if data.get("category") else None

    if not interval or (not message and not category):
        return {"error": "You must provide either a message or a category, and an interval."}

    if message_id:
        # ✅ If an ID exists, update the existing message
        success = update_scheduled_message(message_id, message, interval, category)
        return {"success": success}

    # ✅ Otherwise, it's a new message
    add_scheduled_message(message=message, category=category, interval=interval)
    return {"success": True}


# ✏️ Edit Scheduled Message
@router.post("/scheduled-messages/edit/{message_id}")
async def edit_scheduled_message(message_id: int, data: dict = Body(...)):
    """Edit a scheduled message."""
    new_message = data.get("message", "").strip()
    new_interval = data.get("interval")
    new_category = data.get("category") if data.get("category") else None

    if not new_interval or (not new_message and not new_category):  # Require Message OR Category
        return {"error": "You must provide either a message or a category, and an interval."}

    success = update_scheduled_message(message_id, new_message, new_interval, new_category)
    return {"success": success}


# 🗑️ Delete Scheduled Message
@router.delete("/scheduled-messages/{message_id}")
async def delete_scheduled_message(message_id: int):
    remove_scheduled_message(message_id)
    return {"success": True}

# 🎲 GET Message Pool List
@router.get("/schedule-message-pool", response_class=HTMLResponse)
async def scheduled_message_pool(request: Request):
    messages = get_scheduled_message_pool()
    return templates.TemplateResponse("includes/admin_message_pool.html", {
        "request": request,
        "messages": messages
    })

# ✅ Add Message to Pool
@router.post("/schedule-pool/add")
async def create_pool_message(data: dict = Body(...)):
    category = data.get("category")
    message = data.get("message")

    if not message:
        return {"error": "Message is required."}

    add_message_to_pool(category, message)
    return {"success": True}

# ✏️ Edit Message in Pool
@router.post("/schedule-pool/edit/{message_id}")
async def edit_pool_message(message_id: int, data: dict = Body(...)):
    """Update a message in the scheduled message pool."""
    new_category = data.get("category")
    new_message = data.get("message")

    if not new_message:
        return {"error": "Message cannot be empty."}

    success = update_pool_message(message_id, new_category, new_message)

    if success:
        return {"success": True}
    else:
        return {"error": "Failed to update message or category."}

# 🗑️ Delete Message from Pool
@router.delete("/schedule-pool/{message_id}")
async def remove_pool_message(message_id: int):
    delete_message_from_pool(message_id)
    return {"success": True}
