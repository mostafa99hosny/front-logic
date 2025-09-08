# src/db.py
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Optional

from pymongo import MongoClient, errors

from .utils import log

_CLIENT: Optional[MongoClient] = None
_DB_NAME: Optional[str] = None
_COLL_NAME: Optional[str] = None


def _get_collection():
    """
    Return a live pymongo Collection or None if configuration/connection fails.
    """
    global _CLIENT, _DB_NAME, _COLL_NAME

    mongo_uri = "mongodb+srv://uzairrather3147:Uzair123@cluster0.h7vvr.mongodb.net/mekyas"
    _DB_NAME = "meqyas"
    _COLL_NAME = "Meqyas"

    if not mongo_uri:
        log("MONGO_URI not set; DB calls will be skipped.", "WARN")
        return None

    try:
        if _CLIENT is None:
            _CLIENT = MongoClient(mongo_uri, serverSelectionTimeoutMS=6000)
            # Force a quick ping to validate the connection early:
            _CLIENT.admin.command("ping")
    except Exception as e:
        log(f"Mongo connection failed: {e}", "WARN")
        return None

    try:
        db = _CLIENT[_DB_NAME]
        col = db[_COLL_NAME]
        return col
    except Exception as e:
        log(f"Mongo get collection failed: {e}", "WARN")
        return None


def save_event(doc: Dict[str, Any]) -> bool:
    """
    Inserts an event document into the configured collection.
    Returns True on success, False on any failure (including missing config).
    """
    col = _get_collection()
    if col is None:  # <- IMPORTANT: explicit None check (no truthiness!)
        return False

    try:
        # Add a default timestamp if caller forgot
        doc = dict(doc)
        doc.setdefault("ts", datetime.utcnow())
        col.insert_one(doc)
        log(f"DB: saved event to '{col.full_name}'.", "INFO")
        return True
    except errors.PyMongoError as e:
        log(f"Mongo insert failed: {e}", "WARN")
    except Exception as e:
        log(f"Unexpected error during save_event: {e}", "WARN")
    return False
