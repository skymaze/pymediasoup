import sys
if sys.version_info >= (3, 8):
    from typing import Optional, Dict, Callable, Literal, List, Any, Union
else:
    from typing import Optional, Dict, Callable, List, Any, Union
    from typing_extensions import Literal

import logging
from pyee import AsyncIOEventEmitter
from aiortc import RTCIceServer
from .handlers.handler_interface import HandlerInterface
from .ortc import ExtendedRtpCapabilities, getExtendedRtpCapabilities, canSend, getRecvRtpCapabilities
from .rtp_parameters import RtpCapabilities
from .sctp_parameters import SctpCapabilities, SctpParameters
from .errors import InvalidStateError
from .transport import InternalTransportOptions, Transport
from .models.transport import IceParameters, IceCandidate, DtlsParameters

class Device:
    def __init__(self, handlerFactory):
        self._observer: AsyncIOEventEmitter = AsyncIOEventEmitter()
        # RTC handler factory.
        self._handlerFactory: Callable[..., HandlerInterface] = handlerFactory
        # Loaded flag.
        self._loaded: bool = False

        # Extended RTP capabilities.
        self._extendedRtpCapabilities: Optional[ExtendedRtpCapabilities] = None
        # Local RTP capabilities for receiving media.
        self._recvRtpCapabilities: Optional[RtpCapabilities] = None
        # Whether we can produce audio/video based on computed extended RTP
        # capabilities.
        self._canProduceByKind: Dict[str, bool] = {
            'audio': False,
            'video': False
        }
        self._sctpCapabilities: Optional[SctpCapabilities] = None

    # The RTC handler name.
    @property
    def handlerName(self) -> str:
        if not self._loaded:
            raise InvalidStateError('not loaded')
        return self._handlerName
    
    # Whether the Device is loaded.
    @property
    def loaded(self) -> bool:
        return self._loaded
    
    # RTP capabilities of the Device for receiving media.
    # @raise {InvalidStateError} if not loaded.
    @property
    def rtpCapabilities(self) -> Optional[RtpCapabilities]:
        if not self._loaded:
            raise InvalidStateError('not loaded')
        return self._recvRtpCapabilities
    
    # SCTP capabilities of the Device.
    # @raise {InvalidStateError} if not loaded.
    @property
    def sctpCapabilities(self) -> Optional[SctpCapabilities]:
        if not self._loaded:
            raise InvalidStateError('not loaded')
        return self._sctpCapabilities
    
    # Observer.
    # @emits newtransport - (Transport)
    @property
    def observer(self):
        return self._observer
    
    # Initialize the Device.
    async def load(self, routerRtpCapabilities: Union[RtpCapabilities, dict]):
        logging.debug(f'Device load() [routerRtpCapabilities:{routerRtpCapabilities}]')
        if isinstance(routerRtpCapabilities, dict):
            routerRtpCapabilities:RtpCapabilities = RtpCapabilities(**routerRtpCapabilities)
        else:
            routerRtpCapabilities:RtpCapabilities = routerRtpCapabilities.copy(deep=True)
        # Temporal handler to get its capabilities.
        if self._loaded:
            logging.warning('already loaded')
            return
        handler: HandlerInterface = self._handlerFactory()
        nativeRtpCapabilities = await handler.getNativeRtpCapabilities()
        logging.debug(f'Device load() | got native RTP capabilities:{nativeRtpCapabilities}')
        # Get extended RTP capabilities.
        self._extendedRtpCapabilities = getExtendedRtpCapabilities(nativeRtpCapabilities, routerRtpCapabilities)
        logging.debug(f'Device load() | got extended RTP capabilities:{self._extendedRtpCapabilities}')
        # Check whether we can produce audio/video.
        self._canProduceByKind['audio'] = canSend('audio', self._extendedRtpCapabilities)
        self._canProduceByKind['video'] = canSend('video', self._extendedRtpCapabilities)
        # Generate our receiving RTP capabilities for receiving media.
        self._recvRtpCapabilities = getRecvRtpCapabilities(self._extendedRtpCapabilities)
        logging.debug(f'Device load() | got receiving RTP capabilities:{self._recvRtpCapabilities}')
        # Generate our SCTP capabilities.
        self._sctpCapabilities = await handler.getNativeSctpCapabilities()
        logging.debug(f'Device load() | got native SCTP capabilities:{self._sctpCapabilities}')
        logging.debug('Device load() succeeded')
        self._loaded = True
        self._handlerName = handler.name
        await handler.close()

    # Whether we can produce audio/video.
    # @raise {InvalidStateError} if not loaded.
    # @raise {TypeError} if wrong arguments.
    def canProduce(self, kind: Literal['video', 'audio']):
        if not self._loaded:
            raise InvalidStateError('not loaded')
        elif kind not in ['video', 'audio']:
            raise TypeError(f'invalid kind {kind}')
        return self._canProduceByKind[kind]
    
    # Creates a Transport for sending media.
    # @raise {InvalidStateError} if not loaded.
    # @raise {TypeError} if wrong arguments.
    def createSendTransport(
        self,
        id: str,
        iceParameters: IceParameters,
        iceCandidates: List[IceCandidate],
        dtlsParameters: DtlsParameters,
        sctpParameters: Optional[SctpParameters],
        iceServers: Optional[List[RTCIceServer]] = None,
        iceTransportPolicy: Optional[Literal['all', 'relay']] = None,
        additionalSettings: Optional[dict] = None,
        proprietaryConstraints: Any = None,
        appData: Optional[dict] = {}
    ) -> Transport:
        logging.debug('createSendTransport()')
        return self._createTransport(
            direction='send',
            id=id,
            iceParameters=iceParameters,
            iceCandidates=iceCandidates,
            dtlsParameters=dtlsParameters,
            sctpParameters=sctpParameters,
            iceServers=iceServers,
            iceTransportPolicy=iceTransportPolicy,
            additionalSettings=additionalSettings,
            proprietaryConstraints=proprietaryConstraints,
            appData=appData
        )
    
    # Creates a Transport for receiving media.
    # @raise {InvalidStateError} if not loaded.
    # @raise {TypeError} if wrong arguments.
    def createRecvTransport(
        self,
        id: str,
        iceParameters: Union[IceParameters, dict],
        iceCandidates: List[Union[IceCandidate, dict]],
        dtlsParameters: Union[DtlsParameters, dict],
        sctpParameters: Optional[Union[SctpParameters, dict]] = None,
        iceServers: Optional[List[RTCIceServer]] = None,
        iceTransportPolicy: Optional[Literal['all', 'relay']] = None,
        additionalSettings: Optional[dict] = None,
        proprietaryConstraints: Any = None,
        appData: Optional[dict] = {}
    ) -> Transport:
        logging.debug('createRecvTransport()')
        if isinstance(iceParameters, dict):
            iceParameters: IceParameters = IceParameters(**iceParameters)
        
        iceCandidates = [IceCandidate(**c) if isinstance(c, dict) else c for c in iceCandidates]
        
        if isinstance(dtlsParameters, dict):
            dtlsParameters: DtlsParameters = DtlsParameters(**dtlsParameters)
        
        if isinstance(sctpParameters, dict):
            sctpParameters: SctpParameters = SctpParameters(**sctpParameters)
        
        return self._createTransport(
            direction='recv',
            id=id,
            iceParameters=iceParameters,
            iceCandidates=iceCandidates,
            dtlsParameters=dtlsParameters,
            sctpParameters=sctpParameters,
            iceServers=iceServers,
            iceTransportPolicy=iceTransportPolicy,
            additionalSettings=additionalSettings,
            proprietaryConstraints=proprietaryConstraints,
            appData=appData
        )
    
    def _createTransport(
        self,
        direction: Literal['send', 'recv'],
        id: str,
        iceParameters: IceParameters,
        iceCandidates: List[IceCandidate],
        dtlsParameters: DtlsParameters,
        sctpParameters: Optional[SctpParameters],
        iceServers: Optional[List[RTCIceServer]] = None,
        iceTransportPolicy: Optional[Literal['all', 'relay']] = None,
        additionalSettings: Optional[dict] = None,
        proprietaryConstraints: Any = None,
        appData: Optional[dict] = {}
    ) -> Transport:
        if not self._loaded:
            raise InvalidStateError('not loaded')
        transport = Transport(options=InternalTransportOptions(
            direction=direction,
            handlerFactory=self._handlerFactory,
            extendedRtpCapabilities=self._extendedRtpCapabilities,
            canProduceByKind=self._canProduceByKind,
            id=id,
            iceParameters=iceParameters,
            iceCandidates=iceCandidates,
            dtlsParameters=dtlsParameters,
            sctpParameters=sctpParameters,
            iceServers=iceServers,
            iceTransportPolicy=iceTransportPolicy,
            additionalSettings=additionalSettings,
            proprietaryConstraints=proprietaryConstraints,
            appData=appData
        ))
    
        return transport
