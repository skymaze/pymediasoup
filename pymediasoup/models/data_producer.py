from typing import Optional, Literal, Any
from pydantic import BaseModel


class DataProducerOptions(BaseModel):
    ordered: Optional[bool]
    maxPacketLifeTime: Optional[int]
    maxRetransmits: Optional[int]
    priority: Optional[Literal['very-low','low','medium','high']]
    label: Optional[str]
    protocol: Optional[str]
    appData: Optional[Any]
