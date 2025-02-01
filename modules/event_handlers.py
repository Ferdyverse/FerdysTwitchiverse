import random
import math
import logging
from modules.db_manager import save_data, save_planet
from modules.schemas import AlertSchema, GoalSchema, IconSchema, HtmlSchema, ClickableObject

logger = logging.getLogger("uvicorn.error")

# ✅ Dictionary to map event names to handler functions
EVENT_MAPPING = {
    "alert": (AlertSchema, "handle_alert"),
    "goal": (GoalSchema, "handle_goal"),
    "message": (str, "handle_message"),  # Simple string
    "icon": (IconSchema, "handle_icon"),
    "html": (HtmlSchema, "handle_html"),
    "clickable": (ClickableObject, "handle_clickable"),
}

# ✅ Main function to handle all event types dynamically
async def handle_event(event_type, event_data, add_clickable_object=None, remove_clickable_object=None):
    """
    Dynamically calls the appropriate event handler based on the event_type.
    Converts raw event data into its corresponding Pydantic model.
    """
    event_schema, handler_name = EVENT_MAPPING.get(event_type, (None, None))

    if not event_schema or not handler_name:
        logger.warning(f"⚠️ Unknown event type received: {event_type}")
        return

    try:
        # ✅ Convert event_data into a validated Pydantic model
        event_model = event_schema.model_validate(event_data) if event_schema != str else event_data

        handler = globals().get(handler_name)  # Get function dynamically
        if handler:
            if event_type == "clickable":
                await handler(event_model, add_clickable_object, remove_clickable_object)
            else:
                await handler(event_model)
        else:
            logger.warning(f"⚠️ No handler function found for {event_type}")

    except Exception as e:
        logger.error(f"❌ Error processing event {event_type}: {e}")

async def handle_alert(alert):
    """Handles Twitch alerts like follows, subs, and raids."""
    if alert.type == "follower":
        save_data("last_follower", alert.user)
        logger.info(f"📌 Saved last follower: {alert.user}")

    elif alert.type == "subscriber":
        save_data("last_subscriber", alert.user)
        logger.info(f"📌 Saved last subscriber: {alert.user}")

    elif alert.type == "raid":
        user = alert.user
        size = alert.size or 0
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(200, 700)
        save_planet(user, size, angle, distance)
        logger.info(f"🪐 Planet created for Raider {user}: Size={size}")

async def handle_goal(goal):
    """Handles goal updates."""
    save_data("goal_text", goal.text)
    save_data("goal_current", goal.current)
    save_data("goal_target", goal.target)
    logger.info(f"🎯 Goal updated: {goal.text} ({goal.current}/{goal.target})")

async def handle_message(message):
    """Handles custom overlay messages."""
    save_data("last_message", message)
    logger.info(f"💬 Message received: {message}")

async def handle_icon(icon):
    """Handles icon add/remove events."""
    if icon.action == "add":
        logger.info(f"➕ Adding icon: {icon.name}")
    elif icon.action == "remove":
        logger.info(f"❌ Removing icon: {icon.name}")

async def handle_html(html):
    """Handles overlay HTML updates."""
    save_data("html_content", html.content)
    save_data("html_lifetime", html.lifetime)
    logger.info(f"🖼️ HTML content received: {html.content} (Lifetime: {html.lifetime}ms)")

async def handle_clickable(clickable, add_clickable_object, remove_clickable_object):
    """Handles adding and removing clickable objects."""
    if clickable.action == "add":
        logger.info(f"✅ Adding clickable object: {clickable.object_id}")
        await add_clickable_object(clickable)
    elif clickable.action == "remove":
        logger.info(f"❌ Removing clickable object: {clickable.object_id}")
        await remove_clickable_object(clickable.object_id)
