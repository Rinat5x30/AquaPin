"""DB-backed job queue: pending -> running -> done | failed, with timeout and retries."""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from aquapin_core.errors import AquaPinError
from aquapin_core.replay import build_viewer

from .models import Job, Result

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 3  # first run + 2 retries
RUNNING_TIMEOUT_S = 600

Builder = Callable[..., tuple[dict[str, Any], Any]]


def claim_job() -> Job | None:
    """Atomically take the oldest pending job (row lock where the database supports it)."""
    with transaction.atomic():
        qs = Job.objects.filter(status=Job.Status.PENDING).order_by("created_at")
        if connection.features.has_select_for_update_skip_locked:
            qs = qs.select_for_update(skip_locked=True)
        job = qs.select_related("field").first()
        if job is None:
            return None
        job.status = Job.Status.RUNNING
        job.attempts += 1
        job.started_at = timezone.now()
        job.save(update_fields=["status", "attempts", "started_at"])
        return job


def reap_stale(now: dt.datetime | None = None) -> int:
    """Running jobs past the timeout go back to pending (or fail after the last attempt)."""
    now = now or timezone.now()
    cutoff = now - dt.timedelta(seconds=RUNNING_TIMEOUT_S)
    count = 0
    for job in Job.objects.filter(status=Job.Status.RUNNING, started_at__lt=cutoff):
        if job.attempts >= MAX_ATTEMPTS:
            job.status, job.error_code = Job.Status.FAILED, "Timeout"
            job.finished_at = now
        else:
            job.status = Job.Status.PENDING
        job.save(update_fields=["status", "error_code", "finished_at"])
        count += 1
    return count


def run_job(job: Job, builder: Builder = build_viewer, today: dt.date | None = None) -> Job:
    today = job.field.analysis_date or today or dt.date.today()  # replay jobs end on their date
    field = job.field
    folder = settings.LIVE_DATA_ROOT / str(field.id)
    try:
        data, res = builder(
            folder=folder,
            lat=field.lat,
            lon=field.lon,
            radius_m=field.radius_m,
            crop_id=field.crop_id,
            planting=field.planting_date,
            today=today,
        )
    except AquaPinError as exc:
        log.warning(
            "job %s failed (attempt %s): %s: %s", job.pk, job.attempts, type(exc).__name__, exc
        )
        job.error_code = type(exc).__name__
        job.error_text = str(exc)[:300]
        retry = job.attempts < MAX_ATTEMPTS and job.error_code not in {
            "GeometryError",
            "CropParamsError",
        }
        job.status = Job.Status.PENDING if retry else Job.Status.FAILED
        job.finished_at = None if retry else timezone.now()
        job.save(update_fields=["status", "error_code", "error_text", "finished_at"])
        return job
    Result.objects.create(
        field=field,
        computed_on=today,
        payload=data,
        pipeline_version=res.advice.pipeline_version,
        params_hash=res.advice.params_hash,
    )
    job.status, job.error_code, job.error_text = Job.Status.DONE, "", ""
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "error_code", "error_text", "finished_at"])
    return job
