from contextlib import asynccontextmanager
import sqlite3
from typing import Optional

import aiosqlite
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


DB_PATH = "businesses.db"


# ---------- Business model ----------
class BusinessIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    owner: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=80)
    revenue: float = Field(ge=0)


class Business(BusinessIn):
    id: int


def row_to_business(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "owner": row["owner"],
        "category": row["category"],
        "revenue": row["revenue"],
    }


# ---------- Stateless API storage: persistent SQLite ----------
def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                owner TEXT NOT NULL,
                category TEXT NOT NULL,
                revenue REAL NOT NULL CHECK(revenue >= 0)
            )
        """)


def sync_create(data: BusinessIn):
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cursor = db.execute(
            "INSERT INTO businesses (name, owner, category, revenue) VALUES (?, ?, ?, ?)",
            (data.name, data.owner, data.category, data.revenue),
        )
        row = db.execute(
            "SELECT * FROM businesses WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return row_to_business(row)


def sync_list():
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM businesses ORDER BY id").fetchall()
        return [row_to_business(row) for row in rows]


def sync_get(business_id: int):
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            "SELECT * FROM businesses WHERE id = ?", (business_id,)
        ).fetchone()
        return row_to_business(row) if row else None


def sync_update(business_id: int, data: BusinessIn):
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cursor = db.execute(
            """UPDATE businesses
               SET name = ?, owner = ?, category = ?, revenue = ?
               WHERE id = ?""",
            (data.name, data.owner, data.category, data.revenue, business_id),
        )
        if cursor.rowcount == 0:
            return None
        row = db.execute(
            "SELECT * FROM businesses WHERE id = ?", (business_id,)
        ).fetchone()
        return row_to_business(row)


def sync_delete(business_id: int):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("DELETE FROM businesses WHERE id = ?", (business_id,))
        return cursor.rowcount > 0


# ---------- Async SQLite helpers ----------
async def async_create(data: BusinessIn):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "INSERT INTO businesses (name, owner, category, revenue) VALUES (?, ?, ?, ?)",
            (data.name, data.owner, data.category, data.revenue),
        )
        await db.commit()
        async with db.execute(
            "SELECT * FROM businesses WHERE id = ?", (cursor.lastrowid,)
        ) as cur:
            row = await cur.fetchone()
        return row_to_business(row)


async def async_list():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM businesses ORDER BY id") as cur:
            rows = await cur.fetchall()
        return [row_to_business(row) for row in rows]


async def async_get(business_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM businesses WHERE id = ?", (business_id,)
        ) as cur:
            row = await cur.fetchone()
        return row_to_business(row) if row else None


async def async_update(business_id: int, data: BusinessIn):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """UPDATE businesses
               SET name = ?, owner = ?, category = ?, revenue = ?
               WHERE id = ?""",
            (data.name, data.owner, data.category, data.revenue, business_id),
        )
        await db.commit()
        if cursor.rowcount == 0:
            return None
        async with db.execute(
            "SELECT * FROM businesses WHERE id = ?", (business_id,)
        ) as cur:
            row = await cur.fetchone()
        return row_to_business(row)


async def async_delete(business_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM businesses WHERE id = ?", (business_id,))
        await db.commit()
        return cursor.rowcount > 0


# ---------- Stateful API storage: in-memory dictionary ----------
stateful_businesses: dict[int, dict] = {}
next_stateful_id = 1


def state_create(data: BusinessIn):
    global next_stateful_id
    business_id = next_stateful_id
    next_stateful_id += 1
    item = {"id": business_id, **data.model_dump()}
    stateful_businesses[business_id] = item
    return item


def state_list():
    return list(stateful_businesses.values())


def state_get(business_id: int):
    return stateful_businesses.get(business_id)


def state_update(business_id: int, data: BusinessIn):
    if business_id not in stateful_businesses:
        return None
    item = {"id": business_id, **data.model_dump()}
    stateful_businesses[business_id] = item
    return item


def state_delete(business_id: int):
    return stateful_businesses.pop(business_id, None) is not None


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Business CRUD API",
    description=(
        "Demonstration of stateless request handling with SQLite and stateful "
        "in-memory storage. Each storage mode has sync and async endpoints."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def home():
    return {
        "message": "Business API is running",
        "docs": "/docs",
        "groups": [
            "/stateless/sync/businesses",
            "/stateless/async/businesses",
            "/stateful/sync/businesses",
            "/stateful/async/businesses",
        ],
    }


# ============================================================
# STATELESS + SYNCHRONOUS CRUD
# Base path: /stateless/sync/businesses
# ============================================================
@app.post("/stateless/sync/businesses", response_model=Business, tags=["Stateless - Sync"])
def stateless_sync_create(data: BusinessIn):
    return sync_create(data)


@app.get("/stateless/sync/businesses", response_model=list[Business], tags=["Stateless - Sync"])
def stateless_sync_list():
    return sync_list()


@app.get("/stateless/sync/businesses/{business_id}", response_model=Business, tags=["Stateless - Sync"])
def stateless_sync_get(business_id: int):
    item = sync_get(business_id)
    if item is None:
        raise HTTPException(404, "Business not found")
    return item


@app.put("/stateless/sync/businesses/{business_id}", response_model=Business, tags=["Stateless - Sync"])
def stateless_sync_update(business_id: int, data: BusinessIn):
    item = sync_update(business_id, data)
    if item is None:
        raise HTTPException(404, "Business not found")
    return item


@app.delete("/stateless/sync/businesses/{business_id}", tags=["Stateless - Sync"])
def stateless_sync_delete(business_id: int):
    if not sync_delete(business_id):
        raise HTTPException(404, "Business not found")
    return {"message": "Business deleted", "id": business_id}


# ============================================================
# STATELESS + ASYNCHRONOUS CRUD
# Base path: /stateless/async/businesses
# ============================================================
@app.post("/stateless/async/businesses", response_model=Business, tags=["Stateless - Async"])
async def stateless_async_create(data: BusinessIn):
    return await async_create(data)


@app.get("/stateless/async/businesses", response_model=list[Business], tags=["Stateless - Async"])
async def stateless_async_list():
    return await async_list()


@app.get("/stateless/async/businesses/{business_id}", response_model=Business, tags=["Stateless - Async"])
async def stateless_async_get(business_id: int):
    item = await async_get(business_id)
    if item is None:
        raise HTTPException(404, "Business not found")
    return item


@app.put("/stateless/async/businesses/{business_id}", response_model=Business, tags=["Stateless - Async"])
async def stateless_async_update(business_id: int, data: BusinessIn):
    item = await async_update(business_id, data)
    if item is None:
        raise HTTPException(404, "Business not found")
    return item


@app.delete("/stateless/async/businesses/{business_id}", tags=["Stateless - Async"])
async def stateless_async_delete(business_id: int):
    if not await async_delete(business_id):
        raise HTTPException(404, "Business not found")
    return {"message": "Business deleted", "id": business_id}


# ============================================================
# STATEFUL + SYNCHRONOUS CRUD
# Base path: /stateful/sync/businesses
# ============================================================
@app.post("/stateful/sync/businesses", response_model=Business, tags=["Stateful - Sync"])
def stateful_sync_create(data: BusinessIn):
    return state_create(data)


@app.get("/stateful/sync/businesses", response_model=list[Business], tags=["Stateful - Sync"])
def stateful_sync_list():
    return state_list()


@app.get("/stateful/sync/businesses/{business_id}", response_model=Business, tags=["Stateful - Sync"])
def stateful_sync_get(business_id: int):
    item = state_get(business_id)
    if item is None:
        raise HTTPException(404, "Business not found")
    return item


@app.put("/stateful/sync/businesses/{business_id}", response_model=Business, tags=["Stateful - Sync"])
def stateful_sync_update(business_id: int, data: BusinessIn):
    item = state_update(business_id, data)
    if item is None:
        raise HTTPException(404, "Business not found")
    return item


@app.delete("/stateful/sync/businesses/{business_id}", tags=["Stateful - Sync"])
def stateful_sync_delete(business_id: int):
    if not state_delete(business_id):
        raise HTTPException(404, "Business not found")
    return {"message": "Business deleted", "id": business_id}


# ============================================================
# STATEFUL + ASYNCHRONOUS CRUD
# Base path: /stateful/async/businesses
# ============================================================
@app.post("/stateful/async/businesses", response_model=Business, tags=["Stateful - Async"])
async def stateful_async_create(data: BusinessIn):
    return state_create(data)


@app.get("/stateful/async/businesses", response_model=list[Business], tags=["Stateful - Async"])
async def stateful_async_list():
    return state_list()


@app.get("/stateful/async/businesses/{business_id}", response_model=Business, tags=["Stateful - Async"])
async def stateful_async_get(business_id: int):
    item = state_get(business_id)
    if item is None:
        raise HTTPException(404, "Business not found")
    return item


@app.put("/stateful/async/businesses/{business_id}", response_model=Business, tags=["Stateful - Async"])
async def stateful_async_update(business_id: int, data: BusinessIn):
    item = state_update(business_id, data)
    if item is None:
        raise HTTPException(404, "Business not found")
    return item


@app.delete("/stateful/async/businesses/{business_id}", tags=["Stateful - Async"])
async def stateful_async_delete(business_id: int):
    if not state_delete(business_id):
        raise HTTPException(404, "Business not found")
    return {"message": "Business deleted", "id": business_id}
