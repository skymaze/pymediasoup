from typing import Optional, Any
from aiortc import MediaStreamTrack
from pydantic import BaseModel

from .rtp_parameters import MediaKind, RtpParameters


class ConsumerOptions(BaseModel):
    id: Optional[str]
    producerId: Optional[str]
    kind: MediaKind
    rtpParameters: RtpParameters
    appData: Optional[Any]