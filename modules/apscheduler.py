from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from database.session import get_db
from database.base import ScheduledJobs
from modules.scheduled_jobs import process_scheduled_job_sync
import logging

logger = logging.getLogger("uvicorn.error.apscheduler")

# Initialize scheduler
scheduler = BackgroundScheduler()

# Load scheduled jobs from the database
def load_scheduled_jobs(app):
    """Loads and schedules all enabled jobs from the database."""
    db: Session = next(get_db())
    jobs = db.query(ScheduledJobs).filter(ScheduledJobs.active == True).all()
    db.close()

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
            cron_parts = job.cron_expression.split()  # Example: "0 12 * * *"
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

# Start scheduler
def start_scheduler(app):
    load_scheduled_jobs(app)
    scheduler.start()
    logger.info("✅ APScheduler started.")

# Shutdown scheduler
def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("🛑 APScheduler stopped")
