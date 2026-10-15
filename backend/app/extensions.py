from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Stockage en mémoire : suffisant pour un seul processus (1 worker gunicorn).
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
