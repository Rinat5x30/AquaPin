"""Process pending jobs. Run from cron every minute: python manage.py run_jobs"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from fields.bot import TelegramClient, notify_job
from fields.jobs import claim_job, reap_stale, run_job


class Command(BaseCommand):
    help = "Claim and run pending field jobs (idempotent; safe to overlap)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--max", type=int, default=10, help="max jobs per run")

    def handle(self, *args: Any, **options: Any) -> None:
        reaped = reap_stale()
        client = TelegramClient()
        done = 0
        for _ in range(int(options["max"])):
            job = claim_job()
            if job is None:
                break
            job = run_job(job)
            self.stdout.write(f"job {job.pk} -> {job.status} {job.error_code}".strip())
            if job.status in {job.Status.DONE, job.Status.FAILED}:
                notify_job(job, client)
            done += 1
        self.stdout.write(f"reaped={reaped} processed={done}")
