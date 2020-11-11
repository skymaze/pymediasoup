import sys
if sys.version_info >= (3, 8):
    from typing import Optional, Any, Literal
else:
    from typing import Optional, Any
    from typing_extensions import Literal

import logging
from pydantic import BaseModel
from pyee import AsyncIOEventEmitter
from aiortc import RTCDataChannel
from .emitter import EnhancedEventEmitter
from .sctp_parameters import SctpStreamParameters


class DataConsumerOptions(BaseModel):
    id: str
    dataProducerId: str
    sctpStreamParameters: SctpStreamParameters
    label: Optional[str]
    protocol: Optional[str]
    appData: Optional[dict] = {}

class DataConsumer(EnhancedEventEmitter):
    def __init__(
        self,
        id: str,
        dataProducerId: str,
        dataChannel: RTCDataChannel,
        sctpStreamParameters: SctpStreamParameters,
        appData: Optional[dict] = {},
        loop=None
    ):
        super(DataConsumer, self).__init__(loop=loop)

        # Closed flag.
        self._closed: bool = False
        # Observer instance.
        self._observer: AsyncIOEventEmitter = AsyncIOEventEmitter()

        self._id = id
        self._dataProducerId = dataProducerId
        self._dataChannel = dataChannel
        self._sctpStreamParameters = sctpStreamParameters
        self._appData = appData

        self._handleDataChannel()
    
    # DataConsumer id.
    @property
    def id(self) -> str:
        return self._id
    
    # Associated DataProducer id.
    @property
    def dataProducerId(self) -> str:
        return self._dataProducerId
    
    # Whether the DataConsumer is closed.
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

    # DataChannel binaryType.
    @property
    def binaryType(self) -> str:
        return self._dataChannel.binaryType
    
    @binaryType.setter
    def binaryType(self, binaryType: str):
        self._dataChannel.binaryType = binaryType
    
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
    
    # Closes the DataConsumer.
    async def close(self):
        if self._closed:
            return
        
        logging.debug('DataConsumer close()')

        self._closed = True

        self._dataChannel.close()

        await self.emit_for_results('@close')

        # Emit observer event.
        self._observer.emit('close')
    
    # Transport was closed.
    def transportClosed(self):
        if self._closed:
            return

        logging.debug('DataConsumer transportClosed()')

        self._closed = True

        self._dataChannel.close()

        self.emit('transportclose')

        self._observer.emit('close')
    
    def _handleDataChannel(self):
        @self._dataChannel.on('open')
        def on_open():
            if self._closed:
                return
            logging.debug('DataConsumer DataChannel "open" event')
            self.emit('open')

        # NOTE: aiortc.RTCDataChannel won't emit error event, here use pyee error event
        @self._dataChannel.on('error')
        def on_error(message):
            if self._closed:
                return

            logging.error(f'DataConsumer DataChannel "error" event: {message}')
            
            self.emit('error', message)

        @self._dataChannel.on('close')
        def on_close():
            if self._closed:
                return
            logging.warning('DataConsumer DataChannel "close" event')
            self._closed = True
            self.emit('@close')
            self._observer.emit('close')

        @self._dataChannel.on('message')
        def on_message(message):
            if self._closed:
                return
            self.emit('message', message)
