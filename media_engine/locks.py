import time
from contextlib import contextmanager
from django.core.cache import cache


@contextmanager
def cache_lock(key, timeout=120, wait_timeout=8):
    token = f'lock:{key}'
    acquired = False
    deadline = time.monotonic() + wait_timeout
    while time.monotonic() < deadline:
        if cache.add(token, '1', timeout=timeout):
            acquired = True
            break
        time.sleep(0.1)
    try:
        yield acquired
    finally:
        if acquired:
            cache.delete(token)
