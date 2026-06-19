from pydantic import BaseModel, Field
from typing import Literal, Optional
class ScoreRequest(BaseModel):
    lat: float=Field(ge=-90, le=90); lon: float=Field(ge=-180, le=180)
class ZoneSummary(BaseModel):
    gh7:str; lat:float; lon:float; impact:float; rank:int; tier3_share:float; heavy_share:float
class ScoreResult(BaseModel):
    gh7:str; impact:float; rank:Optional[int]=None; tier3_share:float; heavy_share:float
    source:Literal["grid","model","nearest"]; degraded:bool; nearest:list[ZoneSummary]
class Health(BaseModel):
    status:str; version:str; artifacts_version:Optional[str]; model_loaded:bool
    mappls:Literal["live","cached","down"]
class Waypoint(BaseModel):
    lat: float=Field(ge=-90, le=90); lng: float=Field(ge=-180, le=180)
class ImpedanceRequest(BaseModel):
    waypoints: list[Waypoint]=Field(min_length=2)
    min_impact: float=80.0
class ErrorBody(BaseModel):
    code:str; message:str; request_id:str
class ErrorEnvelope(BaseModel):
    error:ErrorBody
