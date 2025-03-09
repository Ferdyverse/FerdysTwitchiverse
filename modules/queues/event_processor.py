import asyncio
import inspect
import logging
from twitchAPI.type import CustomRewardRedemptionStatus

from database.session import get_db
from database.crud.events import save_event
from modules.websocket_handler import broadcast_message
from modules.sequence_runner import execute_sequence
from modules.queues.function_registry import get_function
import config

logger = logging.getLogger("uvicorn.error.event_queue_processor")

worker_count = 0  # Track how many times this function is started

async def process_event_queue(app):
    """ Continuously processes events from the queue """

    global worker_count
    worker_count += 1
    logger.info(f"🚀 Starting Event Queue Processor #{worker_count}")

    twitch_api = app.state.twitch_api
    twitch_chat = app.state.twitch_chat
    obs = app.state.obs
    event_queue = app.state.event_queue

    try:
        while True:
            task = await event_queue.get()
            logger.info(f"📥 Processing event from queue: {task}")

            # Handle function execution
            if "function" in task:
                function_name = task["function"]
                parameters = task.get("data", {})

                if parameters == "None":
                    parameters = {}

                func = get_function(function_name)

                if callable(func):
                    try:
                        sig = inspect.signature(func)
                        param_types = [param.annotation for param in sig.parameters.values()]

                        if param_types and param_types[0] not in [inspect.Parameter.empty, dict]:
                            expected_type = param_types[0]
                            if isinstance(parameters, dict):
                                parameters = expected_type(**parameters)

                        if inspect.iscoroutinefunction(func):
                            await func(parameters) if len(param_types) == 1 else await func(**parameters)
                        else:
                            func(parameters) if len(param_types) == 1 else func(**parameters)

                        logger.info(f"✅ Executed function: {function_name} with parameters: {parameters}")

                    except TypeError as e:
                        logger.error(f"❌ Function execution failed: {e}")
                        async with get_db() as db:
                            await save_event("error", None, f"Failed function: {function_name}, Error: {e}", db)
                else:
                    logger.warning(f"⚠️ Function '{function_name}' not found or not callable!")
                    async with get_db() as db:
                        await save_event("error", None, f"Function not found: {function_name}", db)

            # Process heatmap clicks
            if "heat_click" in task:
                try:
                    click_event = task["heat_click"]

                    user = click_event.get("user_id")
                    x = click_event.get("x")
                    y = click_event.get("y")
                    clicked_object = click_event.get("object_id")

                    real_user = "Anonymous" if user.startswith("A") else "Unverified"

                    if not user.startswith("A") and not user.startswith("U"):
                        user_data = await twitch_api.get_user_info(user_id=user)
                        real_user = user_data.get("display_name", "Unknown")

                    logger.info(f"🖱️ Click detected! User: {real_user}, X: {x}, Y: {y}, Object: {clicked_object}")

                    if clicked_object == "hidden_star":
                        await broadcast_message({
                            "hidden": {
                                "action": "found",
                                "user": real_user,
                                "x": x,
                                "y": y
                            }
                        })
                        await execute_sequence("reset_star", event_queue)
                        await twitch_chat.send_message(f"{real_user} hat sich erbarmt und sauber gemacht!")

                        async with get_db() as db:
                            await save_event("heat_click", user, "Hat aufgeräumt!", db)

                except Exception as e:
                    logger.error(f"❌ Error processing heatmap click: {e}")

            event_queue.task_done()
    except Exception as e:
        logger.error(f"❌ Error in Event Queue Processor: {e}")
