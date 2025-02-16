from pydantic import BaseModel
from typing import Optional

class Users(BaseModel):
    name: str 
    email: str
    gender: str
    address: Optional[str]
    city: Optional[str] 
    nation: Optional[str] 
    zip: Optional[str]
    latitude: Optional[float] 
    longitude: Optional[float]