from typing import List, Optional, Any
from aiortc import MediaStreamTrack
from pydantic import BaseModel

from .rtp_parameters import RtpCodecCapability, RtpEncodingParameters


# https://mediasoup.org/documentation/v3/mediasoup-client/api/#ProducerCodecOptions
class ProducerCodecOptions(BaseModel):
    opusStereo: Optional[bool]
    opusFec: Optional[bool]
    opusDtx: Optional[bool]
    opusMaxPlaybackRate: Optional[int]
    opusPtime: Optional[int]
    videoGoogleStartBitrate: Optional[int]
    videoGoogleMaxBitrate: Optional[int]
    videoGoogleMinBitrate: Optional[int]

class ProducerOptions(BaseModel):
    track: Optional[MediaStreamTrack]
    encodings: Optional[List[RtpEncodingParameters]]
    codecOptions: Optional[ProducerCodecOptions]
    codec: Optional[RtpCodecCapability]
    stopTracks: Optional[bool]
    disableTrackOnPause: Optional[bool]
    zeroRtpOnPause: Optional[bool]
    appData: Optional[Any]