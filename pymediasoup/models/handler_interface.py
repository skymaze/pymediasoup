import sys

if sys.version_info >= (3, 8):
    from typing import Callable, Literal, List, Optional, Any
else:
    from typing import Callable, List, Optional, Any
    from typing_extensions import Literal

from pydantic import BaseModel
from .transport import IceCandidate, IceParameters, DtlsParameters, IceServer
from ..ortc import ExtendedRtpCapabilities
from ..sctp_parameters import SctpParameters, SctpStreamParameters
from ..producer import ProducerCodecOptions
from ..rtp_parameters import (
    RtpCodecCapability,
    RtpParameters,
    MediaKind,
    RtpEncodingParameters,
)


class HandlerRunOptions(BaseModel):
    direction: Literal["send", "recv"]
    iceParameters: IceParameters
    iceCandidates: List[IceCandidate]
    dtlsParameters: DtlsParameters
    sctpParameters: Optional[SctpParameters]
    iceServers: Optional[IceServer]
    iceTransportPolicy: Optional[Literal["all", "relay"]]
    additionalSettings: Optional[Any]
    proprietaryConstraints: Optional[Any]
    extendedRtpCapabilities: ExtendedRtpCapabilities

    class Config:
        arbitrary_types_allowed = True


class HandlerSendOptions(BaseModel):
    track: Any
    encodings: List[RtpEncodingParameters] = []
    codecOptions: Optional[ProducerCodecOptions]
    codec: Optional[RtpCodecCapability]

    class Config:
        arbitrary_types_allowed = True


class HandlerSendResult(BaseModel):
    localId: str
    rtpParameters: RtpParameters

    class Config:
        arbitrary_types_allowed = True


class HandlerReceiveOptions(BaseModel):
    trackId: str
    kind: MediaKind
    rtpParameters: RtpParameters


class HandlerReceiveResult(BaseModel):
    localId: str
    track: Any
    rtpReceiver: Optional[Any]

    class Config:
        arbitrary_types_allowed = True


class HandlerSendDataChannelResult(BaseModel):
    dataChannel: Any
    sctpStreamParameters: SctpStreamParameters

    class Config:
        arbitrary_types_allowed = True


class HandlerReceiveDataChannelOptions(BaseModel):
    sctpStreamParameters: SctpStreamParameters
    label: Optional[str]
    protocol: Optional[str]


class HandlerReceiveDataChannelResult(BaseModel):
    dataChannel: Any

    class Config:
        arbitrary_types_allowed = True
