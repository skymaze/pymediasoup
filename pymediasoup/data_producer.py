import logging
from typing import Optional, Any, Union, Literal
from pyee import AsyncIOEventEmitter
from aiortc import RTCDataChannel
from pydantic import BaseModel
from .errors import InvalidStateError
from .emitter import EnhancedEventEmitter


class DataProducerOptions(BaseModel):
    ordered: Optional[bool]
    maxPacketLifeTime: Optional[int]
    maxRetransmits: Optional[int]
    priority: Optional[Literal['very-low','low','medium','high']]
    label: Optional[str]
    protocol: Optional[str]
    appData: Optional[Any]

class DataProducer(EnhancedEventEmitter):
    # Closed flag.
    _closed: bool = False
    # Observer instance.
    _observer: AsyncIOEventEmitter = AsyncIOEventEmitter()

    def __init__(
        self,
        id: str,
        dataChannel: RTCDataChannel,
        appData: Any = None
    ):
        super(DataProducer, self).__init__()
        self._id = id
        self._dataChannel = dataChannel
        self._appData = appData
    
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
    def readyState(self) -> RTCDataChannelState:
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
    def close(self):
        if self._closed:
            return
        
        logging.debug('Producer close()')

        self._closed = True

        self._destroyTrack()

        self.emit('@close')

        # Emit observer event.
        self._observer.emit('close')
    
    # Transport was closed.
    def transportClosed(self):
        if self._closed:
            return

        logging.debug('Producer transportClosed()')

        self._closed = True

        self._destroyTrack()

        self.emit('transportclose')

        self._observer.emit('close')
    
    # Send a message.
    def send(self, data: Union[bytes, str]):
        logging.debug('DataProducer send()')

        if self._closed:
            raise InvalidStateError('closed')
        
        self._dataChannel.send(data)
    
    def onDataChannelOpen(self):
        if self._closed:
            return
        
        logging.debug('DataProducer DataChannel "open" event')

        self.emit('open')
    
    # NOTE: aiortc.RTCDataChannel won't emit error event
    def onDataChannelError(self, event: dict):
        if self._closed:
            return
        
        error = event.get('error')

        if not error:
            logging.error('unknown DataChannel error')
        
        elif error.get('errorDetail') == 'sctp-failure':
            logging.error(f"DataChannel SCTP error [sctpCauseCode:{error.get('sctpCauseCode')}]: {error.get('message')}")
        
        else:
            logging.error(f'DataChannel "error" event: {error}')
        
        self.emit('error', error)
    
    def onDataChannelClose(self):
        if self._closed:
            return
        
        logging.warning('DataChannel "close" event')

        self._closed = True

        self.emit('@close')
        
        self._observer.emit('close')
    
    def onDataChannelMessage(self, message):
        if self._closed:
            return
        
        logging.debug(f'DataChannel "message" event in a DataProducer, {message}')
    
    def onDataChannelBufferedamountlow(self):
        if self._closed:
            return
        
        self.emit('bufferedamountlow')
    
    def _handleDataChannel(self):
        self._dataChannel.on('open', self.onDataChannelOpen)
        # NOTE: aiortc.RTCDataChannel won't emit error event
        # self._dataChannel.on('error')
        self._dataChannel.on('close', self.onDataChannelClose)
        self._dataChannel.on('message', self.onDataChannelMessage)
        self._dataChannel.on('bufferedamountlow')