import logging
from typing import Optional, Literal, List, Any, Callable, Dict
from enum import IntEnum
from pyee import AsyncIOEventEmitter
from pydantic import BaseModel
from aiortc import RTCIceServer, RTCIceTransportPolicy
from .errors import InvalidStateError
from .emitter import EnhancedEventEmitter
from .sctp_parameters import SctpParameters
from .handlers.handler_interface import HandlerInterface, HandlerRunOptions
from .consumer import Consumer, ConsumerOptions
from .producer import Producer, ProducerOptions
from .data_consumer import DataConsumerm, DataConsumerOptions
from .data_producer import DataProducer, DataProducerOptions

class IceParameters(BaseModel):
    # ICE username fragment.
    usernameFragment: str
    # ICE password.
    password: str
    # ICE Lite.
    iceLite: Optional[bool]

class IceCandidate(BaseModel):
    # Unique identifier that allows ICE to correlate candidates that appear on
    # multiple transports.
    foundation: str
    # The assigned priority of the candidate.
    priority: int
    # The IP address of the candidate.
    ip: str
    # The protocol of the candidate.
    protocol: Literal['udp', 'tcp']
    # The port for the candidate.
    port: int
    # The type of candidate..
    type: Literal['host', 'srflx', 'prflx', 'relay']
    # The type of TCP candidate.
    tcpType: Literal['active', 'passive', 'so']

# The hash function algorithm (as defined in the "Hash function Textual Names"
# registry initially specified in RFC 4572 Section 8) and its corresponding
# certificate fingerprint value (in lowercase hex string as expressed utilizing
# the syntax of "fingerprint" in RFC 4572 Section 5).
class DtlsFingerprint(BaseModel):
    algorithm: str
    value: str

DtlsRole = Literal['auto', 'client', 'server']

class DtlsParameters(BaseModel):
    # DTLS role. Default 'auto'.
    role: DtlsRole = 'auto'
    fingerprints: List[DtlsFingerprint]

ConnectionState = Literal['new', 'connecting', 'connected', 'failed', 'disconnected', 'closed']


class IpVersion(IntEnum):
    ipv4: 4
    ipv6: 6

class PlainRtpParameters(BaseModel):
    ip: str
    ipVersion: IpVersion
    port: int

class TransportOptions(BaseModel):
    id: str
    iceParameters: IceParameters
    iceCandidates: List[IceCandidate]
    dtlsParameters: DtlsParameters
    sctpParameters: Optional[SctpParameters]
    iceServers: List[RTCIceServer]
    iceTransportPolicy: RTCIceTransportPolicy
    additionalSettings: Optional[dict] = None
    proprietaryConstraints: Any = None
    appData: Any = None

class InternalTransportOptions(TransportOptions):
    direction: Literal['send', 'recv']
    handlerFactory: Callable[..., HandlerInterface]
    extendedRtpCapabilities: Any = None
    canProduceByKind: Dict[str, bool]

class Transport(EnhancedEventEmitter):
    # Id.
    id: str
    # Closed flag.
    _closed: bool = False
    # Direction.
    _direction =  Literal['send', 'recv']
    # Extended RTP capabilities.
    _extendedRtpCapabilities = Any
    # Whether we can produce audio/video based on computed extended RTP
    # capabilities.
    _canProduceByKind: Dict[str, bool]
    # App custom data.
    _appData: Any
    # Transport connection state.
    _connectionState = ConnectionState = 'new'
    # Producers indexed by id
    _producers: Dict[str, Producer] = {}
    # Consumers indexed by id.
    _consumers: Dict[str, Consumer] = {}
    # DataProducers indexed by id
    _dataProducers: Dict[str, DataProducer] = {}
    # DataConsumers indexed by id.
    _dataConsumers: Dict[str, DataConsumer] = {}
    # Whether the Consumer for RTP probation has been created.
    _probatorConsumerCreated: bool = False
    # Observer instance.
    _observer: AsyncIOEventEmitter = AsyncIOEventEmitter()

    def __init__(
        self,
        options: InternalTransportOptions,
        loop=None
    ):
        super(Transport, self).__init__(loop=loop)

        logging.debug(f'constructor() [id:{options.id}, direction:{options.direction}]')

        self._id: str = options.id
        self._direction: Literal['send', 'recv'] = options.direction
        self._extendedRtpCapabilities: Any = options.extendedRtpCapabilities,
        self._canProduceByKind: Dict[str, bool] = options.canProduceByKind
        self._maxSctpMessageSize = options.sctpParameters.maxMessageSize if options.sctpParameters else None

        if options.additionalSettings:
            del options.additionalSettings['iceServers']
            del options.additionalSettings['iceTransportPolicy']
            del options.additionalSettings['bundlePolicy']
            del options.additionalSettings['rtcpMuxPolicy']
            del options.additionalSettings['sdpSemantics']

        self._handler = options.handlerFactory()

        handlerRunOptions = HandlerRunOptions(**options.dict())

        self._handler.run(options=handlerRunOptions)

        self._appData = options.appData

        self._handleHandler()
    
    # Producer id.
    @property
    def id(self) -> str:
        return self._id
    
    # Whether the Producer is closed.
    @property
    def closed(self) -> bool:
        return self._closed
    
    # Transport direction.
    @property
    def direction(self) -> Literal['send', 'recv']:
        return self._direction
    
    # RTC handler instance.
    @property
    def handler(self) -> HandlerInterface:
        return self._handler
    
    # Connection state.
    @property
    def connectionState(self) -> ConnectionState:
        return self._connectionState
    
    # App custom data.
    @property
    def appData(self) -> Any:
        return self._appData
    
    # Invalid setter.
    @appData.setter
    def appData(self, value):
        raise Exception('cannot override appData object')

    # Observer.
    #
    # @emits close
    # @emits newproducer - (producer: Producer)
    # @emits newconsumer - (producer: Producer)
    # @emits newdataproducer - (dataProducer: DataProducer)
    # @emits newdataconsumer - (dataProducer: DataProducer)
    @property
    def observer(self) -> AsyncIOEventEmitter:
        return self._observer

    # Close the Transport.
    def close(self):
        if self._closed:
            return
        
        logging.debug('Transport close()')

        self._closed = True

        # Close the handler.
        self._handler.close()

        # Close all Process.
        for process_dict in [self._producers, self._consumers, self._dataProducers, self._dataConsumers]:
            for process in process_dict.values():
                process.transportClosed()
            process_dict.clear()
        
        self._observer.emit('close')
    
    # Get associated Transport (RTCPeerConnection) stats.
    #
    # @returns {RTCStatsReport}
    async def getStats(self):
        if self._closed:
            raise InvalidStateError('closed')

        return await self._handler.getTransportStats()

    # Restart ICE connection.
    async def restartIce(self, iceParameters: IceParameters):
        if self._closed:
            raise InvalidStateError('closed')
        
        return await self._handler.restartIce(iceParameters)
    
    # Update ICE servers.
    async def updateIceServers(self, iceServers: List[RTCIceServer]):
        if self._closed:
            raise InvalidStateError('closed')

        return await self._handler.updateIceServers(iceServers)
    
    # Create a Producer.
    async def produce(self, options: ProducerOptions) -> Producer:
        pass
        