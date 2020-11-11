import logging
from typing import Optional, Any
from aiortc import RTCRtpReceiver, MediaStreamTrack
from pyee import AsyncIOEventEmitter
from pydantic import BaseModel
from .errors import InvalidStateError, UnsupportedError
from .emitter import EnhancedEventEmitter
from .rtp_parameters import MediaKind, RtpParameters


class ConsumerOptions(BaseModel):
    id: str
    producerId: str
    kind: MediaKind
    rtpParameters: RtpParameters
    appData: Optional[dict] = {}

class Consumer(EnhancedEventEmitter):
    def __init__(
        self,
        id: str,
        localId: str,
        producerId: str,
        track: MediaStreamTrack,
        rtpParameters: RtpParameters,
        rtpReceiver: Optional[RTCRtpReceiver] = None,
        appData: Optional[dict] = {},
        loop=None
    ):
        super(Consumer, self).__init__(loop=loop)

        # Closed flag.
        self._closed: bool = False
        # Observer instance.
        self._observer: AsyncIOEventEmitter = AsyncIOEventEmitter()

        self._id = id
        self._localId = localId
        self._producerId = producerId
        self._track = track
        # NOTE: 'AudioStreamTrack' object has no attribute 'enabled'
        self._paused: bool = False
        self._rtpParameters = rtpParameters
        self._rtpReceiver = rtpReceiver
        self._appData = appData
        
        self._handleTrack()
    
    # Consumer id.
    @property
    def id(self) -> str:
        return self._id
    
    # Local id.
    @property
    def localId(self) -> str:
        return self._localId

    # Associated Producer id.
    @property
    def producerId(self) -> str:
        return self._producerId
    
    # Whether the Consumer is closed.
    @property
    def closed(self) -> bool:
        return self._closed
    
    # Media kind.
    @property
    def kind(self) -> MediaStreamTrack.kind:
        return self._track.kind
    
    # Associated RTCRtpReceiver.
    @property
    def rtpReceiver(self) -> Optional[RTCRtpReceiver]:
        return self._rtpReceiver
    
    # The associated track.
    @property
    def track(self) -> Optional[MediaStreamTrack]:
        return self._track
    
    # RTP parameters.
    @property
    def rtpParameters(self) -> RtpParameters:
        return self._rtpParameters
    
    # Whether the Consumer is paused.
    @property
    def paused(self) -> bool:
        return self._paused
    
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
    # @emits pause
    # @emits resume
    # @emits trackended
    @property
    def observer(self) -> AsyncIOEventEmitter:
        return self._observer

    async def close(self):
        if self._closed:
            return
        
        logging.debug('Consumer close()')

        self._closed = True

        self._destroyTrack()

        await self.emit_for_results('@close')

        # Emit observer event.
        self._observer.emit('close')
  
    # Transport was closed.
    def transportClosed(self):
        if self._closed:
            return

        logging.debug('Consumer transportClosed()')

        self._closed = True

        self._destroyTrack()

        self.emit('transportclose')

        self._observer.emit('close')
    
    # Get associated RTCRtpSender stats.
    async def getStats(self):
        if self._closed:
            raise InvalidStateError('closed')

        return await self.emit_for_results('@getstats')
    
    # Pauses sending media.
    def pause(self):
        logging.debug('Consumer pause()')

        if self._closed:
            logging.debug('Consumer pause() | Consumer closed')
            return
        
        self._paused = True

        if self._track and self._disableTrackOnPause:
            # TODO: MediaStreamTrack missing enable property
            # self._track.enabled = False
            pass
        
        self._observer.emit('pause')
    
    # Resumes sending media.
    def resume(self):
        logging.debug('Consumer resume()')

        if self._closed:
            logging.debug('Consumer resume() | Consumer closed')
            return
        
        self._paused = False

        if self._track and self._disableTrackOnPause:
            # TODO: MediaStreamTrack missing enable property
            # self._track.enabled = True
            pass
        
        self._observer.emit('resume')
    
    def _onTrackEnded(self):
        logging.debug('track "ended" event')
        self.emit('trackended')
        # Emit observer event.
        self._observer.emit('trackended')
    
    def _handleTrack(self):
        if not self._track:
            return

        self._track.on('ended', self._onTrackEnded)
    
    def _destroyTrack(self):
        if not self._track:
            return

        self._track.remove_listener('ended', self._onTrackEnded)

        self._track.stop()
