"""
Firebase Admin SDK client — singleton.

Provides server-side access to Firestore for Shadow Mode:
  - Venice API key slot usage counters  (venice_state/global)
  - Per-user Shadow session state       (venice_sessions/{user_id})

The actual Firebase service account JSON is NEVER stored in source control.
Its path on the server is read from the FIREBASE_CREDENTIALS_PATH environment
variable (set in .env or as a deployment secret).

Do not use this module to store conversation history — that lives in MongoDB.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_firestore_client = None


def get_firestore():
    """
    Returns the Firestore async client, initialising the Firebase Admin SDK on
    first call.  Subsequent calls return the cached client.

    Raises RuntimeError if FIREBASE_CREDENTIALS_PATH is not set or the file
    cannot be read — this is intentional: the bot should fail loudly rather
    than silently operating without Shadow Mode persistence.
    """
    global _firestore_client

    if _firestore_client is not None:
        return _firestore_client

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore_async
        from app.core.config import settings

        cred_path = settings.firebase_credentials_path
        if not cred_path:
            raise RuntimeError(
                "FIREBASE_CREDENTIALS_PATH is not set in the environment. "
                "Generate a service account key from the Firebase Console "
                "(Project Settings → Service Accounts) and set the path."
            )

        cred = credentials.Certificate(cred_path)

        # Avoid re-initialising if another module already did so
        try:
            app = firebase_admin.get_app()
        except ValueError:
            app = firebase_admin.initialize_app(cred)

        _firestore_client = firestore_async.client(app=app)
        logger.info("Firebase Admin SDK initialised successfully.")
        return _firestore_client

    except Exception as exc:
        logger.error(f"Failed to initialise Firebase Admin SDK: {exc}")
        raise
