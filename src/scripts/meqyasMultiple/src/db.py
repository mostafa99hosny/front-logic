from typing import Any, Dict, List
from pymongo import MongoClient, UpdateOne
from .config import settings

_client: MongoClient | None = None

def get_client() -> MongoClient:
    global _client
    if _client is None:
        if not settings.MONGO_URI:
            raise RuntimeError("MONGO_URI is empty. Set it in .env.")
        _client = MongoClient(settings.MONGO_URI)
    return _client

def get_collection():
    client = get_client()
    db = client[settings.DB_NAME]
    return db[settings.COLLECTION_NAME]

def save_filter_snapshot(snapshot: Dict[str, Any]) -> str:
    col = get_collection()
    result = col.insert_one(snapshot)
    return str(result.inserted_id)

def upsert_records(records: List[Dict[str, Any]]) -> int:
    """
    Upsert records by a natural key (code > reference > trx_title).
    Returns number of upserts (len of batch).
    """
    if not records:
        return 0
    col = get_collection()
    ops = []
    for r in records:
        key = r.get("code") or r.get("reference") or r.get("trx_title")
        if not key:
            continue
        ops.append(
            UpdateOne(
                {"_key": key},
                {"$set": {**r, "_key": key, "updated_at": r.get("scraped_at")}},
                upsert=True,
            )
        )
    if not ops:
        return 0
    res = col.bulk_write(ops, ordered=False)
    # res.upserted_count works in many cases; fall back to len(records)
    return getattr(res, "upserted_count", len(records))
