from fastapi import APIRouter, HTTPException, Request, Body
from fastapi.responses import HTMLResponse
from database.crud.scheduled_messages import (
    get_scheduled_message_pool,
    add_message_to_pool,
    delete_message_from_pool,
    update_pool_message
)
from database.crud.scheduled_jobs import (
    get_scheduled_jobs,
    add_scheduled_job,
    update_scheduled_job,
    remove_scheduled_job,
    get_scheduled_job_by_id
)
from modules.apscheduler import load_scheduled_jobs
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/scheduled", tags=["Scheduled Jobs"])


@router.get("/jobs", response_class=HTMLResponse)
def scheduled_jobs(request: Request):
    """Retrieve all scheduled jobs from CouchDB and return HTML."""
    jobs = get_scheduled_jobs()
    return templates.TemplateResponse("includes/admin_scheduled_jobs.html", {
        "request": request,
        "jobs": jobs
    })


@router.post("/jobs/add", response_model=dict)
async def create_or_update_scheduled_job(
    request: Request,
    data: dict = Body(...)
):
    """HTMX endpoint to add or update a scheduled job."""
    job_id = data.get("id")
    job_type = data.get("job_type")  # "twitch_message", "overlay_event", "interval", "cron"
    interval_seconds = data.get("interval_seconds")
    cron_expression = data.get("cron_expression")
    payload = data.get("payload", {})  # Stores additional data (e.g., Twitch message text)

    if not job_type or (job_type == "interval" and not interval_seconds) or (job_type == "cron" and not cron_expression):
        raise HTTPException(status_code=400, detail="Missing required fields for job scheduling.")

    if job_id:
        success = update_scheduled_job(job_id, job_type, interval_seconds, cron_expression, payload)
    else:
        success = add_scheduled_job(job_type, interval_seconds, cron_expression, payload)

    # Reload jobs in APScheduler to apply changes
    await load_scheduled_jobs(request.app)

    return {"success": success}


@router.get("/jobs/edit/{job_id}")
def get_scheduled_job(job_id: str):
    """Returns job details as JSON to populate the modal."""
    job = get_scheduled_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.post("/jobs/edit/{job_id}")
def edit_scheduled_job(
    request: Request,
    job_id: str,
    data: dict = Body(...)
):
    """Edit a scheduled job."""
    job_type = data.get("job_type")
    interval_seconds = data.get("interval_seconds")
    cron_expression = data.get("cron_expression")
    payload = data.get("payload", {})

    if not job_type or (job_type == "interval" and not interval_seconds) or (job_type == "cron" and not cron_expression):
        raise HTTPException(status_code=400, detail="Missing required fields for job scheduling.")

    success = update_scheduled_job(job_id, job_type, interval_seconds, cron_expression, payload)

    # Reload jobs in APScheduler to apply changes
    load_scheduled_jobs(request.app)

    return {"success": success}


@router.delete("/jobs/{job_id}")
def delete_scheduled_job(request: Request, job_id: str):
    """Delete a scheduled job."""
    remove_scheduled_job(job_id)

    # Reload jobs in APScheduler to remove the deleted job
    load_scheduled_jobs(request.app)

    return {"success": True}


# GET Message Pool List
@router.get("/messages/pool", response_class=HTMLResponse)
def scheduled_message_pool(request: Request):
    """Retrieve all scheduled messages from CouchDB."""
    messages = get_scheduled_message_pool()
    return templates.TemplateResponse("includes/admin_message_pool.html", {
        "request": request,
        "messages": messages
    })


@router.post("/pool/add")
def create_pool_message(data: dict = Body(...)):
    """Add a message to the scheduled message pool."""
    category = data.get("category")
    message = data.get("message")

    if not message:
        return {"error": "Message is required."}

    add_message_to_pool(category, message)
    return {"success": True}


@router.post("/pool/edit/{message_id}")
def edit_pool_message(
    message_id: str,
    data: dict = Body(...)
):
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


@router.delete("/pool/{message_id}")
def remove_pool_message(message_id: str):
    """Remove a message from the scheduled message pool."""
    delete_message_from_pool(message_id)
    return {"success": True}
