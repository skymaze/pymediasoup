from typing import Callable, Literal, List, Optional, Any
from pydantic import BaseModel
from aiortc import RTCIceServer, MediaStreamTrack
from ..emitter import EnhancedEventEmitter
from ..models.transport import IceParameters
from ..models.handler_interface import HandlerRunOptions, HandlerReceiveOptions, HandlerSendOptions, HandlerSendResult, HandlerReceiveResult, SctpStreamParameters, HandlerSendDataChannelResult, HandlerReceiveDataChannelOptions, HandlerReceiveDataChannelResult
from ..rtp_parameters import RtpCapabilities
from ..sctp_parameters import SctpCapabilities, SctpStreamParameters


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

    def run(self, options: HandlerRunOptions):
        pass

    async def updateIceServers(self, iceServers: List[RTCIceServer]):
        pass

    async def restartIce(self, iceParameters: IceParameters):
        pass

    async def getTransportStats(self) -> Any:
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

    async def getSenderStats(self, localId: str) -> Any:
        pass

    async def sendDataChannel(self, options: SctpStreamParameters) -> HandlerSendDataChannelResult:
        pass

    async def receive(self, options: HandlerReceiveOptions) -> HandlerReceiveResult:
        pass

    async def stopReceiving(self, localId: str):
        pass

    async def getReceiverStats(self, localId: str):
        pass

    async def receiveDataChannel(self, options: HandlerReceiveDataChannelOptions) -> HandlerReceiveDataChannelResult:
        pass