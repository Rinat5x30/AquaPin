"""Persistent state: fields, jobs, results and the Telegram bot session."""

from __future__ import annotations

import uuid

from django.db import models


class Field(models.Model):
    """A circular field. The primary key is a UUID, never a guessable integer."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_key = models.CharField(max_length=80, db_index=True)  # "web:<session>" or "tg:<chat_id>"
    lat = models.FloatField()
    lon = models.FloatField()
    radius_m = models.FloatField()
    crop_id = models.CharField(max_length=40)
    planting_date = models.DateField()
    analysis_date = models.DateField(null=True, blank=True)  # None = up to today (live)
    consent_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Field {self.id} ({self.lat:.4f}, {self.lon:.4f})"


class Job(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        DONE = "done"
        FAILED = "failed"

    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name="jobs")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    idempotency_key = models.CharField(max_length=120, unique=True)  # "<field uuid>:<date>"
    error_code = models.CharField(max_length=60, blank=True)
    error_text = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "created_at"])]


class Result(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name="results")
    computed_on = models.DateField()
    payload = models.JSONField()
    pipeline_version = models.CharField(max_length=60)
    params_hash = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["field", "computed_on"])]


class TelegramUpdate(models.Model):
    """Seen update ids: Telegram may deliver the same update twice."""

    update_id = models.BigIntegerField(unique=True)
    received_at = models.DateTimeField(auto_now_add=True)


class BotSession(models.Model):
    class State(models.TextChoices):
        IDLE = "idle"
        AWAIT_CONSENT = "await_consent"
        AWAIT_DATE = "await_date"

    chat_id = models.BigIntegerField(unique=True)
    state = models.CharField(max_length=20, choices=State.choices, default=State.IDLE)
    lang = models.CharField(max_length=2, default="en")
    pending_lat = models.FloatField(null=True, blank=True)
    pending_lon = models.FloatField(null=True, blank=True)
    consent_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
