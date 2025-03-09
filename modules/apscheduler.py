from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.future import select
from database.session import AsyncSessionLocal
from database.base import ScheduledJobs
from modules.scheduled_jobs import process_scheduled_job_sync
import asyncio
import logging

logger = logging.getLogger("uvicorn.error.apscheduler")

# Initialize scheduler
scheduler = BackgroundScheduler()

async def fetch_scheduled_jobs():
    """Fetch scheduled jobs from the database asynchronously."""
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(ScheduledJobs).filter(ScheduledJobs.active == True))
            return result.scalars().all()
        except Exception as e:
            logger.error(f"❌ Error fetching scheduled jobs: {e}")
            return []

async def load_scheduled_jobs(app):
    """Loads and schedules all enabled jobs from the database asynchronously."""
    jobs = await fetch_scheduled_jobs()

    for job in jobs:
        logger.info(f"Found job: {job}")

        if job.job_type in ["interval", "twitch_message", "sequence"]:
            scheduler.add_job(
                process_scheduled_job_sync,
                IntervalTrigger(seconds=job.interval_seconds),
                id=f"job_{job.job_id}",
                replace_existing=True,
                args=[job.job_id, app]
            )

        elif job.job_type == "date":
            scheduler.add_job(
                process_scheduled_job_sync,
                "date",
                run_date=job.run_at,
                id=f"job_{job.job_id}",
                replace_existing=True,
                args=[job.job_id, app]
            )

        elif job.job_type == "cron":
            cron_parts = job.cron_expression.split()
            scheduler.add_job(
                process_scheduled_job_sync,
                "cron",
                minute=cron_parts[0],
                hour=cron_parts[1],
                day=cron_parts[2],
                month=cron_parts[3],
                day_of_week=cron_parts[4],
                id=f"job_{job.job_id}",
                replace_existing=True,
                args=[job.job_id, app]
            )

        logger.info(f"✅ Loaded {job.job_type} job: {job.job_id}")

def start_scheduler(app):
    asyncio.create_task(load_scheduled_jobs(app))  # ✅ Starte als Background Task
    scheduler.start()
    logger.info("✅ APScheduler started.")

# Shutdown scheduler
def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("🛑 APScheduler stopped")
