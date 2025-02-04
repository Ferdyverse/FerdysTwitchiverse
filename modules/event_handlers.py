import random
import math
import logging
from modules.db_manager import save_data, save_planet
from modules.schemas import AlertSchema, GoalSchema, IconSchema, HtmlSchema, ClickableObject

logger = logging.getLogger("uvicorn.error.events")

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
    Returns True if successful, False if an error occurs.
    """
    logger.debug(f"🔍 Handling event: {event_type} with data: {event_data}")

    event_info = EVENT_MAPPING.get(event_type)
    if not event_info:
        logger.error(f"❌ No handler found for event type: {event_type}")
        return False

    schema, handler_name = event_info  # Unpack Schema and Handler Name

    handler = globals().get(handler_name)  # Get function dynamically
    if not handler:
        logger.error(f"❌ Handler function '{handler_name}' not found in globals()")
        return False

    try:
        # ✅ Validate event data against the schema
        validated_data = schema(**event_data)

        # ✅ Call the handler with validated data
        if event_type == "clickable":
            result = await handler(validated_data, add_clickable_object, remove_clickable_object)
        else:
            result = await handler(validated_data)

        logger.debug(f"🔍 {event_type} handler returned: {result}")  # Log handler return value

        if not isinstance(result, dict):  # Ensure it's a dictionary
            logger.error(f"❌ {event_type} handler returned invalid data: {result}")
            return False

        if result.get("status") != "success":
            logger.error(f"❌ Event processing failed: {result.get('message', 'Unknown error')}")
            return False  # Indicate failure

        return True  # ✅ Indicate success
    except Exception as e:
        logger.error(f"❌ Error in event handler for {event_type}: {e}")
        return False

async def handle_alert(alert):
    """Handles Twitch alerts like follows, subs, and raids."""
    try:
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

        return {"status": "success", "message": "Alert processed"}
    except Exception as e:
        logger.error(f"❌ Error processing alert: {e}")
        return {"status": "error", "message": str(e)}

async def handle_goal(goal):
    """Handles goal updates."""
    try:
        save_data("goal_text", goal.text)
        save_data("goal_current", goal.current)
        save_data("goal_target", goal.target)
        logger.info(f"🎯 Goal updated: {goal.text} ({goal.current}/{goal.target})")

        return {"status": "success", "message": "Goal updated successfully"}
    except Exception as e:
        logger.error(f"❌ Error processing goal: {e}")
        return {"status": "error", "message": str(e)}

async def handle_message(message):
    """Handles custom overlay messages."""
    try:
        save_data("last_message", message)
        logger.info(f"💬 Message received: {message}")

        return {"status": "success", "message": "Message processed successfully"}
    except Exception as e:
        logger.error(f"❌ Error processing message: {e}")
        return {"status": "error", "message": str(e)}

async def handle_icon(icon):
    """Handles adding and removing icons in the overlay."""
    try:
        if icon.action == "add":
            logger.info(f"➕ Adding icon: {icon.name}")
        elif icon.action == "remove":
            logger.info(f"❌ Removing icon: {icon.name}")

        return {"status": "success", "message": "Icon updated"}
    except Exception as e:
        logger.error(f"❌ Error processing icon: {e}")
        return {"status": "error", "message": str(e)}

async def handle_html(html):
    """Handles overlay HTML updates."""
    try:
        save_data("html_content", html.content)
        save_data("html_lifetime", html.lifetime)
        logger.info(f"🖼️ HTML content received: {html.content} (Lifetime: {html.lifetime}ms)")
        return {"status": "success", "message": "HTML saved"}
    except Exception as e:
        logger.error(f"❌ Error processing icon: {e}")
        return {"status": "error", "message": str(e)}

async def handle_clickable(clickable, add_clickable_object, remove_clickable_object):
    """Handles adding and removing clickable objects."""
    try:
        if clickable.action == "add":
            logger.info(f"✅ Adding clickable object: {clickable.object_id}")
            result = await add_clickable_object(clickable)
        elif clickable.action == "remove":
            logger.info(f"❌ Removing clickable object: {clickable.object_id}")
            result = await remove_clickable_object(clickable.object_id)

        if result["status"] == "error":
            logger.error(f"❌ Error processing event clickable: {result['message']}")
            return {"status": "error", "message": result["message"]}

        return {"status": "success", "message": "Clickable object updated"}
    except Exception as e:
        logger.error(f"❌ Error in handle_clickable: {e}")
        return {"status": "error", "message": str(e)}
