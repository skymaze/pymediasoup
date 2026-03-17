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
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()

    async def getNativeRtpCapabilities(self) -> RtpCapabilities:
        raise NotImplementedError()

    async def getNativeSctpCapabilities(self) -> SctpCapabilities:
        raise NotImplementedError()

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
        raise NotImplementedError()

    async def updateIceServers(self, iceServers: List[RTCIceServer]):
        raise NotImplementedError()

    async def restartIce(self, iceParameters: IceParameters):
        raise NotImplementedError()

    async def getTransportStats(self) -> Any:
        raise NotImplementedError()

    async def send(
        self,
        track: MediaStreamTrack,
        encodings: Optional[List[RtpEncodingParameters]] = None,
        codecOptions: Optional[ProducerCodecOptions] = None,
        codec: Optional[RtpCodecCapability] = None,
        streamId: Optional[str] = None,
        headerExtensionOptions: Optional[dict] = None,
    ) -> HandlerSendResult:
        raise NotImplementedError()

    async def stopSending(self, localId: str):
        raise NotImplementedError()

    async def pauseSending(self, localId: str):
        raise NotImplementedError()

    async def resumeSending(self, localId: str):
        raise NotImplementedError()

    async def replaceTrack(
        self, localId: str, track: Optional[MediaStreamTrack] = None
    ):
        raise NotImplementedError()

    async def setMaxSpatialLayer(self, localId: str, spatialLayer: int):
        raise NotImplementedError()

    async def setRtpEncodingParameters(self, localId: str, params: Any):
        raise NotImplementedError()

    async def getSenderStats(self, localId: str) -> Any:
        raise NotImplementedError()

    async def sendDataChannel(
        self,
        streamId: Optional[int] = None,
        ordered: Optional[bool] = True,
        maxPacketLifeTime: Optional[int] = None,
        maxRetransmits: Optional[int] = None,
        label: Optional[str] = None,
        protocol: Optional[str] = None,
    ) -> HandlerSendDataChannelResult:
        raise NotImplementedError()

    async def receive(
        self,
        trackId: str,
        kind: MediaKind,
        rtpParameters: RtpParameters,
        streamId: Optional[str] = None,
    ) -> HandlerReceiveResult:
        raise NotImplementedError()

    async def stopReceiving(self, localId: str):
        raise NotImplementedError()

    async def pauseReceiving(self, localId: str):
        raise NotImplementedError()

    async def resumeReceiving(self, localId: str):
        raise NotImplementedError()

    async def getReceiverStats(self, localId: str):
        raise NotImplementedError()

    async def receiveDataChannel(
        self,
        sctpStreamParameters: SctpStreamParameters,
        label: Optional[str] = None,
        protocol: Optional[str] = None,
    ) -> HandlerReceiveDataChannelResult:
        raise NotImplementedError()
