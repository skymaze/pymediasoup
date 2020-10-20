from typing import Callable, Literal, List, Optional, Any
from aiortc import RTCIceServer, RTCIceTransportPolicy, RTCRtpSender, MediaStreamTrack, RTCRtpReceiver, RTCDataChannel
from ..emitter import EnhancedEventEmitter
from ..transport import IceCandidate, IceParameters, DtlsParameters
from ..rtp_parameters import RtpCapabilities, RtpCodecCapability, RtpParameters, RtpEncodingParameters, MediaKind
from ..sctp_parameters import SctpCapabilities, SctpParameters, SctpStreamParameters
from ..producer import ProducerCodecOptions


HandlerFactory: Callable[..., HandlerInterface] = lambda: HandlerInterface()

class HandlerRunOptions(BaseModel):
    direction: Literal['send', 'recv']
    iceParameters: IceParameters
    iceCandidates: List[IceCandidate]
    dtlsParameters: DtlsParameters
    sctpParameters: Optional[SctpParameters]
    iceServers: Optional[RTCIceServer]
    iceTransportPolicy: Optional[RTCIceTransportPolicy]
    additionalSettings: Optional[Any]
    proprietaryConstraints: Optional[Any]
    extendedRtpCapabilities: Any

class HandlerSendResult(BaseModel):
    localId: str
    rtpParameters: RtpParameters
    rtpSender: Optional[RTCRtpSender]

class HandlerReceiveOptions(BaseModel):
    trackId: str
    kind: MediaKind
    rtpParameters: RtpParameters

class HandlerReceiveResult(BaseModel):
    localId: str
    track: MediaStreamTrack
    rtpReceiver: Optional[RTCRtpReceiver]

HandlerSendDataChannelOptions = SctpStreamParameters

class HandlerSendDataChannelResult(BaseModel):
    dataChannel: RTCDataChannel
    sctpStreamParameters: SctpStreamParameters

class HandlerReceiveDataChannelOptions(BaseModel):
    sctpStreamParameters: SctpStreamParameters
    label: Optional[str]
    protocol: Optional[str]

class HandlerReceiveDataChannelResult(BaseModel):
    dataChannel: RTCDataChannel

class HandlerInterface(EnhancedEventEmitter):
    # @emits @connect - (
	#     { dtlsParameters: DtlsParameters },
	#     callback: Function,
	#     errback: Function
	#   )
	# @emits @connectionstatechange - (connectionState: ConnectionState)
    def __init__(self):
        super(HandlerInterface, self).__init__()

    @property
    def name(self) -> str:
        pass
    
    def close(self):
        pass

    async def getNativeRtpCapabilities(self) -> RtpCapabilities:
        pass

    async def getNativeSctpCapabilities(self) -> SctpCapabilities:
        pass

    def run(self, oprtions: HandlerRunOptions):
        pass

    async def updateIceServers(self, iceServers: List[RTCIceServer]):
        pass

    async def restartIce(self, iceParameters: IceParameters):
        pass

    async def getTransportStats(self) -> RTCStatsReport:
        pass
    
    async def send(self, options: HandlerSendOptions) -> HandlerSendResult:
        pass
    
    async def stopSending(self, localId: str):
        pass

    async def replaceTrack(self, localId: str, track: Optional[MediaStreamTrack] = None):
        pass

    async def setMaxSpatialLayer(self, localId: str, spatialLayer: int):
        pass

    async def setRtpEncodingParameters(self, localId: str, params: Any):
        pass

    async def getSenderStats(self, localId: str) -> RTCStatsReport:
        pass

    async def sendDataChannel(self, options: HandlerSendDataChannelOptions) -> HandlerSendDataChannelResult:
        pass

    async def receive(self, options: HandlerReceiveOptions) -> HandlerReceiveResult:
        pass

    async def stopReceiving(self, localId: str):
        pass

    async def getReceiverStats(self, localId: str):
        pass

    async def receiveDataChannel(self, options: HandlerReceiveDataChannelOptions) -> HandlerReceiveDataChannelResult:
        pass