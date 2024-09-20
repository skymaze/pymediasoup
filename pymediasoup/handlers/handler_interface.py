from typing import Literal, List, Optional, Any

from aiortc import RTCIceServer, MediaStreamTrack
from ..ortc import ExtendedRtpCapabilities
from ..emitter import EnhancedEventEmitter
from ..models.transport import IceCandidate, IceParameters, DtlsParameters
from ..models.handler_interface import (
    HandlerSendResult,
    HandlerReceiveResult,
    HandlerSendDataChannelResult,
    HandlerReceiveDataChannelResult,
)
from ..rtp_parameters import (
    RtpParameters,
    RtpCapabilities,
    RtpCodecCapability,
    MediaKind,
    RtpEncodingParameters,
)
from ..sctp_parameters import SctpCapabilities, SctpStreamParameters, SctpParameters
from ..producer import ProducerCodecOptions


class HandlerInterface(EnhancedEventEmitter):
    # @emits @connect - (
    #     { dtlsParameters: DtlsParameters },
    #     callback: Function,
    #     errback: Function
    #   )
    # @emits @connectionstatechange - (connectionState: ConnectionState)
    def __init__(self, loop=None):
        super(HandlerInterface, self).__init__(loop=loop)

    @property
    def name(self) -> str:
        pass

    def close(self):
        pass

    async def getNativeRtpCapabilities(self) -> RtpCapabilities:
        pass

    async def getNativeSctpCapabilities(self) -> SctpCapabilities:
        pass

    def run(
        self,
        direction: Literal["send", "recv"],
        iceParameters: IceParameters,
        iceCandidates: List[IceCandidate],
        dtlsParameters: DtlsParameters,
        extendedRtpCapabilities: ExtendedRtpCapabilities,
        sctpParameters: Optional[SctpParameters] = None,
        iceServers: Optional[List[RTCIceServer]] = None,
        iceTransportPolicy: Optional[Literal["all", "relay"]] = None,
        additionalSettings: Optional[Any] = None,
        proprietaryConstraints: Optional[Any] = None,
    ):
        pass

    async def updateIceServers(self, iceServers: List[RTCIceServer]):
        pass

    async def restartIce(self, iceParameters: IceParameters):
        pass

    async def getTransportStats(self) -> Any:
        pass

    async def send(
        self,
        track: MediaStreamTrack,
        encodings: List[RtpEncodingParameters] = [],
        codecOptions: Optional[ProducerCodecOptions] = None,
        codec: Optional[RtpCodecCapability] = None,
    ) -> HandlerSendResult:
        pass

    async def stopSending(self, localId: str):
        pass

    async def replaceTrack(
        self, localId: str, track: Optional[MediaStreamTrack] = None
    ):
        pass

    async def setMaxSpatialLayer(self, localId: str, spatialLayer: int):
        pass

    async def setRtpEncodingParameters(self, localId: str, params: Any):
        pass

    async def getSenderStats(self, localId: str) -> Any:
        pass

    async def sendDataChannel(
        self,
        streamId: Optional[int] = None,
        ordered: Optional[bool] = True,
        maxPacketLifeTime: Optional[int] = None,
        maxRetransmits: Optional[int] = None,
        label: Optional[str] = None,
        protocol: Optional[str] = None,
    ) -> HandlerSendDataChannelResult:
        pass

    async def receive(
        self, trackId: str, kind: MediaKind, rtpParameters: RtpParameters
    ) -> HandlerReceiveResult:
        pass

    async def stopReceiving(self, localId: str):
        pass

    async def getReceiverStats(self, localId: str):
        pass

    async def receiveDataChannel(
        self,
        sctpStreamParameters: SctpStreamParameters,
        label: Optional[str] = None,
        protocol: Optional[str] = None,
    ) -> HandlerReceiveDataChannelResult:
        pass
