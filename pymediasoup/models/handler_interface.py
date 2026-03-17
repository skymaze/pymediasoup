from typing import Literal, List, Optional, Any

from pydantic.v1 import BaseModel, Field
from aiortc import (
    RTCIceServer,
    RTCRtpSender,
    RTCRtpReceiver,
    RTCDataChannel,
    MediaStreamTrack,
)
from .transport import IceCandidate, IceParameters, DtlsParameters
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
    iceServers: Optional[List[RTCIceServer]]
    iceTransportPolicy: Optional[Literal["all", "relay"]]
    additionalSettings: Optional[Any]
    proprietaryConstraints: Optional[Any]
    extendedRtpCapabilities: ExtendedRtpCapabilities

    class Config:
        arbitrary_types_allowed = True


class HandlerSendOptions(BaseModel):
    track: MediaStreamTrack
    encodings: List[RtpEncodingParameters] = Field(default_factory=list)
    codecOptions: Optional[ProducerCodecOptions]
    codec: Optional[RtpCodecCapability]
    streamId: Optional[str] = None
    headerExtensionOptions: Optional[dict] = None

    class Config:
        arbitrary_types_allowed = True


class HandlerSendResult(BaseModel):
    localId: str
    rtpParameters: RtpParameters
    rtpSender: Optional[RTCRtpSender]

    class Config:
        arbitrary_types_allowed = True


class HandlerReceiveOptions(BaseModel):
    trackId: str
    kind: MediaKind
    rtpParameters: RtpParameters
    streamId: Optional[str] = None


class HandlerReceiveResult(BaseModel):
    localId: str
    track: MediaStreamTrack
    rtpReceiver: Optional[RTCRtpReceiver]

    class Config:
        arbitrary_types_allowed = True


class HandlerSendDataChannelResult(BaseModel):
    dataChannel: RTCDataChannel
    sctpStreamParameters: SctpStreamParameters

    class Config:
        arbitrary_types_allowed = True


class HandlerReceiveDataChannelOptions(BaseModel):
    sctpStreamParameters: SctpStreamParameters
    label: Optional[str]
    protocol: Optional[str]


class HandlerReceiveDataChannelResult(BaseModel):
    dataChannel: RTCDataChannel

    class Config:
        arbitrary_types_allowed = True
