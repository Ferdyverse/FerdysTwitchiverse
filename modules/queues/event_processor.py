import asyncio
import inspect
import logging
from twitchAPI.type import CustomRewardRedemptionStatus

from database.crud.events import save_event
from modules.websocket_handler import broadcast_message
from modules.sequence_runner import execute_sequence
from modules.queues.function_registry import get_function
import config

logger = logging.getLogger("uvicorn.error.event_queue_processor")

worker_count = 0  # Track how many times this function is started


async def process_event_queue(app):
    """Continuously processes events from the queue"""

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
                        param_types = [
                            param.annotation for param in sig.parameters.values()
                        ]

                        if param_types and param_types[0] not in [
                            inspect.Parameter.empty,
                            dict,
                        ]:
                            expected_type = param_types[0]
                            if isinstance(parameters, dict):
                                parameters = expected_type(**parameters)

                        if inspect.iscoroutinefunction(func):
                            (
                                await func(parameters)
                                if len(param_types) == 1
                                else await func(**parameters)
                            )
                        else:
                            (
                                func(parameters)
                                if len(param_types) == 1
                                else func(**parameters)
                            )

                        logger.info(
                            f"✅ Executed function: {function_name} with parameters: {parameters}"
                        )

                    except TypeError as e:
                        logger.error(f"❌ Function execution failed: {e}")
                        save_event(
                            "error",
                            None,
                            f"Failed function: {function_name}, Error: {e}",
                        )
                else:
                    logger.warning(
                        f"⚠️ Function '{function_name}' not found or not callable!"
                    )
                    save_event("error", None, f"Function not found: {function_name}")

            # Process Twitch message printing
            if "command" in task:
                command = task["command"]
                user = task["user"]
                user_id = task["user_id"]

                try:
                    user_data = await twitch_api.get_user_info(user_id=user_id)

                    if command == "print":
                        message = task.get("message", "")
                        logger.info(f"🖨️ Printing requested by {user}: {message}")

                        print_request = {
                            "print_elements": [
                                {"type": "headline_1", "text": "Chatogram"},
                                {
                                    "type": "image",
                                    "url": user_data.get("profile_image_url", ""),
                                },
                                {"type": "headline_2", "text": user},
                                {"type": "message", "text": message},
                            ],
                            "print_as_image": True,
                        }

                        # Fetch cam errors
                        try:
                            cam_result = await obs.find_scene_item(
                                config.OBS_PRINTER_CAM
                            )
                            for item in cam_result:
                                await obs.set_source_visibility(
                                    item["scene"], item["id"], True
                                )
                        except Exception as e:
                            logger.error("Could not activate Printer cam")

                        response = await broadcast_message(print_request)
                        logger.info(f"🖨️ Print status: {response}")

                        await twitch_api.twitch.update_redemption_status(
                            config.TWITCH_CHANNEL_ID,
                            task["reward_id"],
                            task["redeem_id"],
                            CustomRewardRedemptionStatus.FULFILLED,
                        )

                except Exception as e:
                    logger.error(f"❌ Error in printing from Twitch command: {e}")
                    await twitch_api.twitch.update_redemption_status(
                        config.TWITCH_CHANNEL_ID,
                        task["reward_id"],
                        task["redeem_id"],
                        CustomRewardRedemptionStatus.CANCELED,
                    )
                finally:
                    await asyncio.sleep(2)
                    try:
                        for item in cam_result:
                            await obs.set_source_visibility(
                                item["scene"], item["id"], False
                            )
                    except Exception as e:
                        logger.error("Could not deactivate Printer cam")

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

                    logger.info(
                        f"🖱️ Click detected! User: {real_user}, X: {x}, Y: {y}, Object: {clicked_object}"
                    )

                    if clicked_object == "hidden_star":
                        await broadcast_message(
                            {
                                "hidden": {
                                    "action": "found",
                                    "user": real_user,
                                    "x": x,
                                    "y": y,
                                }
                            }
                        )
                        await execute_sequence("reset_star", event_queue)
                        await twitch_chat.send_message(
                            f"{real_user} hat sich erbarmt und sauber gemacht!"
                        )
                        save_event("heat_click", user, "Hat aufgeräumt!")

                except Exception as e:
                    logger.error(f"❌ Error processing heatmap click: {e}")

            # Create Twitch Channel Point Redemptions
            if "create_redemption" in task:
                try:
                    redemption = task["create_redemption"]

                    await twitch_api.twitch.create_custom_reward(
                        broadcaster_id=config.TWITCH_CHANNEL_ID,
                        title=redemption.get("title"),
                        cost=redemption.get("cost"),
                        is_enabled=True,
                    )

                    logger.info(
                        f"✅ Created Twitch reward: {redemption.get('title')} for {redemption.get('cost')} points"
                    )

                except Exception as e:
                    logger.error(f"❌ Failed to create Twitch reward: {e}")

            event_queue.task_done()
    except Exception as e:
        logger.error(f"❌ Error in Event Queue Processor: {e}")
