from sqlalchemy.orm import Session
from database.base import ScheduledJobs
import uuid

def get_scheduled_jobs(db: Session):
    """Retrieve all scheduled jobs."""
    return db.query(ScheduledJobs).filter(ScheduledJobs.active == True).all()

def add_scheduled_job(job_type, interval_seconds, cron_expression, payload, db: Session):
    """Add a new scheduled job with a unique event_id."""
    new_job = ScheduledJobs(
        event_id=str(uuid.uuid4()),  # Generate a unique event_id
        job_type=job_type,
        interval_seconds=interval_seconds,
        cron_expression=cron_expression,
        payload=payload,
        active=True
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)  # Ensures the new job is returned with its generated ID
    return new_job.job_id

def update_scheduled_job(job_id, job_type, interval_seconds, cron_expression, payload, db: Session):
    """Update an existing scheduled job."""
    job = db.query(ScheduledJobs).filter(ScheduledJobs.job_id == job_id).first()
    if not job:
        return False

    job.job_type = job_type
    job.interval_seconds = interval_seconds
    job.cron_expression = cron_expression
    job.payload = payload
    db.commit()
    return True

def remove_scheduled_job(job_id, db: Session):
    """Remove a scheduled job."""
    job = db.query(ScheduledJobs).filter(ScheduledJobs.job_id == job_id).first()
    if job:
        db.delete(job)
        db.commit()
        return True
    return False

def get_scheduled_job_by_id(job_id: int, db: Session):
    """Retrieve a single scheduled job by its ID."""
    return db.query(ScheduledJobs).filter(ScheduledJobs.job_id == job_id).first()
