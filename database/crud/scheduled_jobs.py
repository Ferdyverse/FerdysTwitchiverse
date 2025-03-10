from modules.couchdb_client import couchdb_client
import uuid
import logging

logger = logging.getLogger("uvicorn.error.scheduled_jobs")

def get_scheduled_jobs():
    """Retrieve all active scheduled jobs from the correct CouchDB database."""
    try:
        db = couchdb_client.get_db("scheduled_jobs")

        # Fetch all documents where type == "scheduled_job" and active == True
        jobs = [db[doc] for doc in db if db[doc].get("type") == "scheduled_job" and db[doc].get("active")]

        return jobs
    except Exception as e:
        logger.error(f"❌ Failed to retrieve scheduled jobs: {e}")
        return []

def add_scheduled_job(job_type, interval_seconds, cron_expression, payload):
    """Add a new scheduled job with a unique event_id."""
    try:
        db = couchdb_client.get_db("scheduled_jobs")

        new_job = {
            "_id": str(uuid.uuid4()),  # Unique document ID
            "type": "scheduled_job",
            "event_id": str(uuid.uuid4()),  # Unique event identifier
            "job_type": job_type,
            "interval_seconds": interval_seconds,
            "cron_expression": cron_expression,
            "payload": payload,
            "active": True
        }

        db.save(new_job)
        return new_job["_id"]
    except Exception as e:
        logger.error(f"❌ Failed to add scheduled job: {e}")
        return None

def update_scheduled_job(job_id, job_type, interval_seconds, cron_expression, payload):
    """Update an existing scheduled job in CouchDB."""
    try:
        db = couchdb_client.get_db("scheduled_jobs")
        job = db.get(job_id)

        if not job:
            return False  # Job not found

        job["job_type"] = job_type
        job["interval_seconds"] = interval_seconds
        job["cron_expression"] = cron_expression
        job["payload"] = payload
        db.save(job)
        return True
    except Exception as e:
        logger.error(f"❌ Failed to update scheduled job: {e}")
        return False

def remove_scheduled_job(job_id):
    """Remove a scheduled job from CouchDB."""
    try:
        db = couchdb_client.get_db("scheduled_jobs")
        job = db.get(job_id)

        if job:
            db.delete(job)
            return True

        return False  # Job not found
    except Exception as e:
        logger.error(f"❌ Failed to remove scheduled job: {e}")
        return False

def get_scheduled_job_by_id(job_id):
    """Retrieve a single scheduled job by its ID."""
    try:
        db = couchdb_client.get_db("scheduled_jobs")
        job = db.get(job_id)

        return job if job else None
    except Exception as e:
        logger.error(f"❌ Failed to retrieve scheduled job: {e}")
        return None
