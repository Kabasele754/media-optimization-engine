"""Fenced processing leases; no cache-backend private APIs or unsafe delete."""
from contextlib import contextmanager
from datetime import timedelta
import time
import uuid

from django.db import transaction
from django.utils import timezone

from .models import MediaProcessingLease


class LeaseLost(RuntimeError):
    pass


class ProcessingLease:
    def __init__(self, key, timeout=900, using='default'):
        if timeout <= 0:
            raise ValueError('Lease timeout must be positive')
        self.key = key
        self.owner = uuid.uuid4().hex
        self.timeout = timeout
        self.using = using
        self.acquired = False
        self._last_renewal = 0.0

    @property
    def rows(self):
        return MediaProcessingLease.objects.using(self.using)

    def __bool__(self):
        return self.acquired

    def acquire(self):
        now = timezone.now()
        row, created = self.rows.get_or_create(
            key=self.key, defaults={'owner': self.owner, 'expires_at': now + timedelta(seconds=self.timeout)}
        )
        self.acquired = created or bool(self.rows.filter(key=self.key, expires_at__lte=now).update(
            owner=self.owner, expires_at=now + timedelta(seconds=self.timeout)))
        self._last_renewal = time.monotonic()
        return self.acquired

    def checkpoint(self, force=False):
        if not self.acquired:
            raise LeaseLost('Processing lease not acquired')
        if not force and time.monotonic() - self._last_renewal < min(10, self.timeout / 4):
            return
        now = timezone.now()
        renewed = self.rows.filter(key=self.key, owner=self.owner, expires_at__gt=now).update(
            expires_at=now + timedelta(seconds=self.timeout))
        if not renewed:
            raise LeaseLost('Processing lease expired or changed owner')
        self._last_renewal = time.monotonic()

    @contextmanager
    def guard(self):
        # The row stays locked through publication: a stale worker cannot commit
        # after another worker has acquired the lease.
        with transaction.atomic(using=self.using):
            row = self.rows.select_for_update().filter(key=self.key).first()
            if row is None or row.owner != self.owner or row.expires_at <= timezone.now():
                raise LeaseLost('Processing lease expired or changed owner')
            yield

    def release(self):
        if self.acquired:
            self.rows.filter(key=self.key, owner=self.owner).delete()
            self.acquired = False


@contextmanager
def cache_lock(key, timeout=120, wait_timeout=8, using='default'):
    """Backward-compatible truthy context result, now with an ownership fence.

    Long-running callers must call checkpoint() between bounded work units and
    use guard() for metadata publication. A timeout is not silently renewed
    after ownership is lost. Nothing is stored as an image binary in Redis.
    """
    lease = ProcessingLease(key, timeout=timeout, using=using)
    deadline = time.monotonic() + wait_timeout
    while True:
        if lease.acquire() or time.monotonic() >= deadline:
            break
        time.sleep(0.1)
    try:
        yield lease
    finally:
        lease.release()
