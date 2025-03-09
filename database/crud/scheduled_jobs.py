from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.base import ScheduledJobs
import uuid

async def get_scheduled_jobs(db: AsyncSession):
    """Retrieve all active scheduled jobs asynchronously."""
    try:
        result = await db.execute(select(ScheduledJobs).filter(ScheduledJobs.active == True))
        return result.scalars().all()
    except Exception as e:
        print(f"❌ Error retrieving scheduled jobs: {e}")
        return []

async def add_scheduled_job(job_type, interval_seconds, cron_expression, payload, db: AsyncSession):
    """Add a new scheduled job with a unique event_id asynchronously."""
    try:
        new_job = ScheduledJobs(
            event_id=str(uuid.uuid4()),  # Generate a unique event_id
            job_type=job_type,
            interval_seconds=interval_seconds,
            cron_expression=cron_expression,
            payload=payload,
            active=True
        )

        db.add(new_job)
        await db.commit()
        await db.refresh(new_job)  # Ensures the new job is returned with its generated ID
        return new_job.job_id
    except Exception as e:
        print(f"❌ Error adding scheduled job: {e}")
        await db.rollback()
        return None

async def update_scheduled_job(job_id, job_type, interval_seconds, cron_expression, payload, db: AsyncSession):
    """Update an existing scheduled job asynchronously."""
    try:
        result = await db.execute(select(ScheduledJobs).filter(ScheduledJobs.job_id == job_id))
        job = result.scalars().first()

        if not job:
            return False

        job.job_type = job_type
        job.interval_seconds = interval_seconds
        job.cron_expression = cron_expression
        job.payload = payload

        await db.commit()
        return True
    except Exception as e:
        print(f"❌ Error updating scheduled job: {e}")
        await db.rollback()
        return False

async def remove_scheduled_job(job_id, db: AsyncSession):
    """Remove a scheduled job asynchronously."""
    try:
        result = await db.execute(select(ScheduledJobs).filter(ScheduledJobs.job_id == job_id))
        job = result.scalars().first()

        if job:
            await db.delete(job)
            await db.commit()
            return True
        return False
    except Exception as e:
        print(f"❌ Error removing scheduled job: {e}")
        await db.rollback()
        return False

async def get_scheduled_job_by_id(job_id: int, db: AsyncSession):
    """Retrieve a single scheduled job by its ID asynchronously."""
    try:
        result = await db.execute(select(ScheduledJobs).filter(ScheduledJobs.job_id == job_id))
        return result.scalars().first()
    except Exception as e:
        print(f"❌ Error retrieving scheduled job by ID: {e}")
        return None
