from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import api as license_api
from . import database


app = FastAPI(title="License Service")

# serve static web UI
app.mount("/static", StaticFiles(directory="src/license/static"), name="static")


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ChannelCreate(BaseModel):
    name: str
    max_devices: Optional[int] = 1000
    license_duration_days: Optional[int] = 30
    description: Optional[str] = None


class ChannelEdit(BaseModel):
    name: Optional[str] = None
    max_devices: Optional[int] = None
    license_duration_days: Optional[int] = None
    description: Optional[str] = None


class LicenseStatusUpdate(BaseModel):
    new_status: str


@app.get("/", include_in_schema=False)
def index():
    return FileResponse("src/license/static/index.html")


@app.get("/api/devices")
def api_list_devices(include_expired: bool = Query(False), db=Depends(get_db)):
    res = license_api.get_all_device_licenses(db, include_expired=include_expired)
    return JSONResponse(content=res)


@app.post("/api/channels")
def api_add_channel(payload: ChannelCreate, db=Depends(get_db)):
    res = license_api.add_channel(
        db,
        name=payload.name,
        max_devices=payload.max_devices,
        license_duration_days=payload.license_duration_days,
        description=payload.description,
    )
    if not res.get("success", False):
        raise HTTPException(status_code=400, detail=res.get("message", "add failed"))
    return JSONResponse(content=res)


@app.delete("/api/channels")
def api_delete_channel(channel_id: Optional[int] = None, channel_name: Optional[str] = None, db=Depends(get_db)):
    res = license_api.delete_channel(db, channel_id=channel_id, channel_name=channel_name)
    if not res.get("success", False):
        raise HTTPException(status_code=400, detail=res.get("message", "delete failed"))
    return JSONResponse(content=res)


@app.put("/api/channels/{channel_id}")
def api_edit_channel(channel_id: int, payload: ChannelEdit, db=Depends(get_db)):
    res = license_api.edit_channel(
        db,
        channel_id=channel_id,
        name=payload.name,
        max_devices=payload.max_devices,
        license_duration_days=payload.license_duration_days,
        description=payload.description,
    )
    if not res.get("success", False):
        raise HTTPException(status_code=400, detail=res.get("message", "edit failed"))
    return JSONResponse(content=res)


@app.patch("/api/licenses/{license_id}/status")
def api_edit_license_status(license_id: int, payload: LicenseStatusUpdate, db=Depends(get_db)):
    res = license_api.edit_license_status(db, license_id=license_id, new_status=payload.new_status)
    if not res.get("success", False):
        raise HTTPException(status_code=400, detail=res.get("message", "update failed"))
    return JSONResponse(content=res)


@app.post("/api/init_db", include_in_schema=False)
def api_init_db():
    # helper for local dev to create tables
    database.init_db()
    return {"success": True}
