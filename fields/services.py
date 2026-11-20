"""Use cases shared by web views and the Telegram bot (views stay thin)."""

from __future__ import annotations

import datetime as dt
import shutil

from django.conf import settings
from django.utils import timezone

from aquapin_core.crops import get_crop
from aquapin_core.errors import AquaPinError, GeometryError
from aquapin_core.geometry import validate_point

from .models import Field, Job

MAX_SEASON_DAYS = 400


def default_planting_date(today: dt.date) -> dt.date:
    """Most recent 1 November (winter wheat sowing, assumption) not after today."""
    this_year = dt.date(today.year, 11, 1)
    return this_year if today >= this_year else dt.date(today.year - 1, 11, 1)


def create_field_job(
    *,
    owner_key: str,
    lat: float,
    lon: float,
    radius_m: float,
    crop_id: str,
    planting: dt.date,
    today: dt.date,
    analysis_date: dt.date | None = None,
) -> tuple[Field, Job]:
    """Validate, create (or reuse) the field, and queue a job once per field and day.

    `analysis_date` (past) turns the job into a season replay up to that date.
    """
    validate_point(lat, lon, radius_m)
    get_crop(crop_id)  # raises CropParamsError for unknown crops
    if analysis_date is not None and analysis_date > today:
        raise AquaPinError("analysis date is in the future")
    end = analysis_date or today
    if planting > end:
        raise AquaPinError("planting date is after the analysis date")
    if (end - planting).days > MAX_SEASON_DAYS:
        raise GeometryError("season is too long (planting date too far in the past)")
    field = Field.objects.filter(
        owner_key=owner_key,
        lat=round(lat, 5),
        lon=round(lon, 5),
        radius_m=radius_m,
        crop_id=crop_id,
        planting_date=planting,
        analysis_date=analysis_date,
    ).first()
    if field is None:
        field = Field.objects.create(
            owner_key=owner_key,
            lat=round(lat, 5),
            lon=round(lon, 5),
            radius_m=radius_m,
            crop_id=crop_id,
            planting_date=planting,
            analysis_date=analysis_date,
            consent_at=timezone.now(),
        )
    job, _ = Job.objects.get_or_create(
        idempotency_key=f"{field.id}:{today.isoformat()}",
        defaults={"field": field},
    )
    return field, job


def delete_field(field: Field) -> None:
    folder = settings.LIVE_DATA_ROOT / str(field.id)
    shutil.rmtree(folder, ignore_errors=True)
    field.delete()


def delete_owner_data(owner_key: str) -> int:
    count = 0
    for field in Field.objects.filter(owner_key=owner_key):
        delete_field(field)
        count += 1
    return count
