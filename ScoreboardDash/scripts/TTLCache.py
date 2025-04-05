import time


class SimpleTTLCache:
    def __init__(self, ttl_seconds):
        self.ttl = ttl_seconds
        self.store = {}

    def set(self, key, value):
        expiry = time.time() + self.ttl
        self.store[key] = (value, expiry)

    def get(self, key):
        value, expiry = self.store.get(key, (None, 0))
        if time.time() < expiry:
            return value
        else:
            self.store.pop(key, None)
            return None
