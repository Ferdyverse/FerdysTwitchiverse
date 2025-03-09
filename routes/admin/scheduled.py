from fastapi import APIRouter, Depends, HTTPException, Request, Body
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db
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
async def scheduled_jobs(request: Request, db: AsyncSession = Depends(get_db)):
    async with db as session:
        jobs = await get_scheduled_jobs(session)

    return templates.TemplateResponse("includes/admin_scheduled_jobs.html", {
        "request": request,
        "jobs": jobs
    })

@router.post("/jobs/add", response_model=dict)
async def create_or_update_scheduled_job(
    request: Request,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """HTMX endpoint to add or update a scheduled job."""
    job_id = data.get("id")
    job_type = data.get("job_type")  # "twitch_message", "overlay_event", "interval", "cron"
    interval_seconds = data.get("interval_seconds")
    cron_expression = data.get("cron_expression")
    payload = data.get("payload", {})  # Stores additional data (e.g., Twitch message text)

    if not job_type or (job_type == "interval" and not interval_seconds) or (job_type == "cron" and not cron_expression):
        raise HTTPException(status_code=400, detail="Missing required fields for job scheduling.")

    async with db as session:
        if job_id:
            success = await update_scheduled_job(job_id, job_type, interval_seconds, cron_expression, payload, session)
        else:
            success = await add_scheduled_job(job_type, interval_seconds, cron_expression, payload, session)

    load_scheduled_jobs(request.app)  # Reload APScheduler jobs

    return {"success": success}

@router.get("/jobs/edit/{job_id}")
async def get_scheduled_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Returns job details as JSON to populate the modal."""
    async with db as session:
        job = await get_scheduled_job_by_id(job_id, session)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.job_id,
        "job_type": job.job_type,
        "interval_seconds": job.interval_seconds,
        "cron_expression": job.cron_expression,
        "payload": job.payload
    }

@router.delete("/jobs/{job_id}")
async def delete_scheduled_job(request: Request, job_id: int, db: AsyncSession = Depends(get_db)):
    async with db as session:
        await remove_scheduled_job(job_id, session)

    load_scheduled_jobs(request.app)

    return {"success": True}

@router.get("/messages/pool", response_class=HTMLResponse)
async def scheduled_message_pool(request: Request, db: AsyncSession = Depends(get_db)):
    async with db as session:
        messages = await get_scheduled_message_pool(session)

    return templates.TemplateResponse("includes/admin_message_pool.html", {
        "request": request,
        "messages": messages
    })

@router.post("/pool/add")
async def create_pool_message(data: dict = Body(...), db: AsyncSession = Depends(get_db)):
    category = data.get("category")
    message = data.get("message")

    if not message:
        return {"error": "Message is required."}

    async with db as session:
        await add_message_to_pool(category, message, session)

    return {"success": True}

@router.delete("/pool/{message_id}")
async def remove_pool_message(message_id: int, db: AsyncSession = Depends(get_db)):
    async with db as session:
        await delete_message_from_pool(message_id, session)

    return {"success": True}
