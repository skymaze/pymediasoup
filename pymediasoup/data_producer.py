import sys
if sys.version_info >= (3, 8):
    from typing import Optional, Any, Union, Literal
else:
    from typing import Optional, Any, Union
    from typing_extensions import Literal

import logging
from pyee import AsyncIOEventEmitter
from aiortc import RTCDataChannel
from pydantic import BaseModel
from .errors import InvalidStateError
from .emitter import EnhancedEventEmitter
from .sctp_parameters import SctpStreamParameters


class DataProducerOptions(BaseModel):
    ordered: Optional[bool]
    maxPacketLifeTime: Optional[int]
    maxRetransmits: Optional[int]
    priority: Optional[Literal['very-low','low','medium','high']]
    label: Optional[str]
    protocol: Optional[str]
    appData: Optional[dict] = {}

class DataProducer(EnhancedEventEmitter):
    def __init__(
        self,
        id: str,
        dataChannel: RTCDataChannel,
        sctpStreamParameters: SctpStreamParameters,
        appData: Optional[dict] = None,
        loop=None
    ):
        super(DataProducer, self).__init__(loop=loop)

        # Closed flag.
        self._closed: bool = False
        # Observer instance.
        self._observer: AsyncIOEventEmitter = AsyncIOEventEmitter()

        self._id = id
        self._dataChannel = dataChannel
        self._sctpStreamParameters = sctpStreamParameters
        self._appData = appData
        
        self._handleDataChannel()
    
    # DataProducer id.
    @property
    def id(self) -> str:
        return self._id

    # Whether the DataProducer is closed.
    @property
    def closed(self) -> bool:
        return self._closed
    
    # SCTP stream parameters.
    @property
    def sctpStreamParameters(self) -> SctpStreamParameters:
        return self._sctpStreamParameters
    
    # DataChannel readyState.
    @property
    def readyState(self) -> Literal["closed", "closing", "connecting", "open"]:
        return self._dataChannel.readyState
    
    # DataChannel label.
    @property
    def label(self) -> str:
        return self._dataChannel.label
    
    # DataChannel protocol.
    @property
    def protocol(self) -> str:
        return self._dataChannel.protocol
    
    # DataChannel bufferedAmount.
    @property
    def bufferedAmount(self) -> int:
        return self._dataChannel.bufferedAmount
    
    # DataChannel bufferedAmountLowThreshold.
    @property
    def bufferedAmountLowThreshold(self) -> int:
        return self._dataChannel.bufferedAmountLowThreshold
    
    # Set DataChannel bufferedAmountLowThreshold.
    @bufferedAmountLowThreshold.setter
    def bufferedAmountLowThreshold(self, bufferedAmountLowThreshold: int):
        self._dataChannel.bufferedAmountLowThreshold = bufferedAmountLowThreshold
    
    # App custom data.
    @property
    def appData(self) -> Any:
        return self._appData
    
    # Invalid setter.
    @appData.setter
    def appData(self, value):
        raise Exception('cannot override appData object')
    
    # Observer.
    @property
    def observer(self) -> AsyncIOEventEmitter:
        return self._observer
    
    # Closes the DataProducer.
    async def close(self):
        if self._closed:
            return
        
        logging.debug('DataProducer close()')

        self._closed = True

        self._dataChannel.close()

        await self.emit_for_results('@close')

        # Emit observer event.
        self._observer.emit('close')
    
    # Transport was closed.
    def transportClosed(self):
        if self._closed:
            return

        logging.debug('DataProducer transportClosed()')

        self._closed = True

        self._dataChannel.close()

        self.emit('transportclose')

        self._observer.emit('close')
    
    # Send a message.
    def send(self, data: Union[bytes, str]):
        logging.debug('DataProducer send()')

        if self._closed:
            raise InvalidStateError('closed')
        
        self._dataChannel.send(data)
    
    def _handleDataChannel(self):
        @self._dataChannel.on('open')
        def on_open():
            if self._closed:
                return
            
            logging.debug('DataProducer DataChannel "open" event')

            self.emit('open')

        # NOTE: aiortc.RTCDataChannel won't emit error event, here use pyee error event
        @self._dataChannel.on('error')
        def on_error(message):
            if self._closed:
                return

            logging.error(f'DataProducer DataChannel "error" event: {message}')
            
            self.emit('error', message)

        @self._dataChannel.on('close')
        def on_close():
            if self._closed:
                return
            logging.warning('DataProducer DataChannel "close" event')
            self._closed = True
            self.emit('@close')
            self._observer.emit('close')

        @self._dataChannel.on('message')
        def on_message(message):
            if self._closed:
                return
            logging.warning(f'DataProducer DataChannel "message" event in a DataProducer, message discarded: {message}')

        @self._dataChannel.on('bufferedamountlow')
        def on_bufferedamountlow():
            if self._closed:
                return
            self.emit('bufferedamountlow')