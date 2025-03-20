from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from modules.scheduled_jobs import process_scheduled_job_sync
from database.crud.scheduled_jobs import get_scheduled_jobs
import logging

logger = logging.getLogger("uvicorn.error.apscheduler")

# Initialize scheduler
scheduler = BackgroundScheduler()


async def load_scheduled_jobs(app):
    """Loads and schedules all enabled jobs from CouchDB using CRUD functions."""
    jobs = get_scheduled_jobs()  # Fetch scheduled jobs from the database

    if not jobs:
        logger.info("ℹ️ No active scheduled jobs found.")
        return

    for job in jobs:
        if not job.get("active"):
            continue  # Skip inactive jobs

        job_id = job["_id"]
        logger.info(f"🛠️ Found job: {job}")

        try:
            if job["job_type"] in ["interval", "twitch_message", "sequence"]:
                scheduler.add_job(
                    process_scheduled_job_sync,
                    IntervalTrigger(seconds=job["interval_seconds"]),
                    id=f"job_{job_id}",
                    replace_existing=True,
                    args=[job_id, app],
                )

            elif job["job_type"] == "date":
                scheduler.add_job(
                    process_scheduled_job_sync,
                    "date",
                    run_date=job["run_at"],
                    id=f"job_{job_id}",
                    replace_existing=True,
                    args=[job_id, app],
                )

            elif job["job_type"] == "cron":
                cron_parts = job["cron_expression"].split()  # Example: "0 12 * * *"
                scheduler.add_job(
                    process_scheduled_job_sync,
                    "cron",
                    minute=cron_parts[0],
                    hour=cron_parts[1],
                    day=cron_parts[2],
                    month=cron_parts[3],
                    day_of_week=cron_parts[4],
                    id=f"job_{job_id}",
                    replace_existing=True,
                    args=[job_id, app],
                )

            logger.info(f"✅ Scheduled {job['job_type']} job: {job_id}")

        except Exception as e:
            logger.error(f"❌ Error scheduling job {job_id}: {e}")


# Start scheduler
def start_scheduler(app):
    """Starts the scheduler and loads jobs asynchronously."""
    scheduler.start()
    logger.info("✅ APScheduler started.")
    app.add_event_handler("startup", lambda: load_scheduled_jobs(app))


# Shutdown scheduler
def shutdown_scheduler():
    """Stops the scheduler cleanly."""
    scheduler.shutdown()
    logger.info("🛑 APScheduler stopped")
