import logging

logger = logging.getLogger("uvicorn.error.routes.events")


async def handle_event(event_type, event_data, add_clickable, remove_clickable):
    """Process overlay events"""
    logger.info(f"Processing event: {event_type}")
    if event_type == "click":
        await add_clickable(event_data)
    elif event_type == "remove_click":
        await remove_clickable(event_data)
    return True
