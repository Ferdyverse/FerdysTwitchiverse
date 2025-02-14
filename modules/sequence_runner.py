import asyncio
import yaml
import re
import random
import logging
import json
from modules.websocket_handler import broadcast_message
from modules.state_manager import check_condition, set_condition
from modules.event_handlers import handle_icon
from modules.schemas import IconSchema

logger = logging.getLogger("uvicorn.error.sequence_runner")

# Load sequences from YAML
def load_sequences():
    try:
        with open("sequences.yaml", "r") as file:
            return yaml.safe_load(file).get("sequences", {})
    except Exception as e:
        logger.error(f"❌ Failed to load sequences: {e}")
        return {}

# Store sequences in memory
ACTION_SEQUENCES = load_sequences()

def get_sequence_names():
    return list(ACTION_SEQUENCES.keys())

def resolve_random_values(data):
    """
    Parses strings for `{random(min, max)}` and replaces with a random number.
    """
    if isinstance(data, dict):
        return {key: resolve_random_values(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [resolve_random_values(item) for item in data]
    elif isinstance(data, str):
        matches = re.findall(r"{random\((\d+),\s*(\d+)\)}", data)
        for match in matches:
            min_val, max_val = map(int, match)
            random_value = random.randint(min_val, max_val)
            data = data.replace(f"{{random({min_val}, {max_val})}}", str(random_value))
        return data
    return data

async def execute_sequence(action: str, event_queue: asyncio.Queue):
    """Execute a predefined sequence of actions from YAML using the event queue."""
    if action not in ACTION_SEQUENCES:
        logger.warning(f"⚠️ Sequence '{action}' not found.")
        return

    steps = ACTION_SEQUENCES[action]

    for step in steps:
        success = await execute_sequence_step(step, event_queue)

        if not success:
            logger.error(f"❌ Sequence '{action}' stopped due to an error in step: {step}")
            await broadcast_message({"admin_alert": {"type": "error", "message": f"Sequence '{action}' failed"}})
            break

    await broadcast_message({"admin_alert": {"type": "button_click", "message": f"Sequence '{action}' executed"}})

async def execute_sequence_step(step, event_queue: asyncio.Queue):
    """ Execute a single sequence step using the event queue, returning success status. """
    step_type = step.get("type")
    step_data = resolve_random_values(step.get("data", {}))

    try:
        # Handle delays
        if step_type == "sleep":
            delay_time = step_data if isinstance(step_data, (int, float)) else 1
            logger.info(f"⏳ Waiting {delay_time} seconds...")
            await asyncio.sleep(delay_time)
            return True

        # Handle if-else conditions
        if step_type == "if":
            condition_name = step_data.get("condition")
            then_steps = step_data.get("then", [])
            else_steps = step_data.get("else", [])

            if check_condition(condition_name):
                logger.info(f"✅ Condition '{condition_name}' is TRUE, executing THEN block.")
                for then_step in then_steps:
                    success = await execute_sequence_step(then_step, event_queue)
                    if not success:
                        return False  # Stop if a step fails
            else:  # ❌ Condition failed
                logger.info(f"❌ Condition '{condition_name}' is FALSE, executing ELSE block.")
                for else_step in else_steps:
                    success = await execute_sequence_step(else_step, event_queue)
                    if not success:
                        return False  # Stop if a step fails
            return True  # Continue sequence execution

        # Handle function calls via event queue (Fail sequence if function fails)
        if step_type == "call_function":
            function_name = step_data.get("name")
            parameters = step_data.get("parameters", {})

            # Send function execution request to the event queue
            task = {"function": function_name, "data": parameters}
            await event_queue.put(task)
            logger.info(f"🔄 Queued function '{function_name}' with parameters: {parameters}")

            # Check if function succeeds
            success = await wait_for_task_success(task, event_queue)
            if not success:
                logger.error(f"❌ Function '{function_name}' failed, stopping sequence.")
                return False
            return True

        # Handle setting conditions
        if step_type == "set_condition":
            condition_name = step_data.get("name")
            condition_value = step_data.get("value", True)
            set_condition(condition_name, condition_value)
            logger.info(f"🔄 Set condition '{condition_name}' to {condition_value}")
            return True

        if step_type == "show_icon":
            icon = {"icon": {"id": step_data.get("name"), "action": step_data.get("action"), "name": step_data.get("icon")}}
            logger.error(icon)
            await broadcast_message(icon)
            logger.info(f"Show icon: {icon}")
            return True

        # Handle overlay events
        await broadcast_message({"overlay_event": {"action": step_type, "data": step_data}})
        logger.info(f"✅ Executed overlay action: {step_type} with data: {step_data}")
        return True  # ✅ Step successful

    except Exception as e:
        logger.error(f"❌ Error executing step '{step_type}': {e}")
        return False  # ❌ Stop execution if an error occurs


async def wait_for_task_success(task, event_queue: asyncio.Queue):
    """ Wait for a task to complete and return whether it succeeded. """
    return True

async def reload_sequences():
    """ Reload sequences from YAML file. """
    global ACTION_SEQUENCES
    ACTION_SEQUENCES = load_sequences()
    logger.info("🔄 Sequences reloaded successfully.")
