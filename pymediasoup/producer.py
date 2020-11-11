import logging
from typing import List, Optional, Any
from pyee import AsyncIOEventEmitter
from pydantic import BaseModel
from aiortc import RTCRtpSender, MediaStreamTrack
from .emitter import EnhancedEventEmitter
from .errors import InvalidStateError, UnsupportedError
from .rtp_parameters import RtpParameters, RtpCodecCapability, RtpEncodingParameters


# https://mediasoup.org/documentation/v3/mediasoup-client/api/#ProducerCodecOptions
class ProducerCodecOptions(BaseModel):
    opusStereo: Optional[bool]
    opusFec: Optional[bool]
    opusDtx: Optional[bool]
    opusMaxPlaybackRate: Optional[int]
    opusPtime: Optional[int]
    videoGoogleStartBitrate: Optional[int]
    videoGoogleMaxBitrate: Optional[int]
    videoGoogleMinBitrate: Optional[int]

class ProducerOptions(BaseModel):
    track: Optional[MediaStreamTrack] = None
    encodings: Optional[List[RtpEncodingParameters]] = []
    codecOptions: Optional[ProducerCodecOptions] = None
    codec: Optional[RtpCodecCapability] = None
    stopTracks: bool = True
    disableTrackOnPause: bool = True
    zeroRtpOnPause: bool = False
    appData: Optional[Any] = {}

    class Config:
        arbitrary_types_allowed=True

class Producer(EnhancedEventEmitter):
    def __init__(
        self,
        id: str,
        localId: str,
        track: MediaStreamTrack,
        rtpParameters: RtpParameters,
        stopTracks: bool,
        disableTrackOnPause: bool,
        zeroRtpOnPause: bool,
        rtpSender: Optional[RTCRtpSender] = None,
        appData: Optional[dict] = None,
        loop=None
    ):
        super(Producer, self).__init__(loop=loop)

        # Closed flag.
        self._closed: bool = False
        # Observer instance.
        self._observer: AsyncIOEventEmitter = AsyncIOEventEmitter()

        self._id = id
        self._localId = localId
        self._rtpSender = rtpSender
        self._track = track
        self._rtpParameters = rtpParameters
        # NOTE: 'AudioStreamTrack' object has no attribute 'enabled'
        # self._paused = (not track.enabled) if disableTrackOnPause else False
        self._paused = False if disableTrackOnPause else False
        self._maxSpatialLayer: Optional[int] = None
        self._stopTracks = stopTracks
        self._disableTrackOnPause = disableTrackOnPause
        self._zeroRtpOnPause = zeroRtpOnPause
        self._appData = appData

        self._handleTrack()

    # Producer id.
    @property
    def id(self) -> str:
        return self._id
    
    # Local id.
    @property
    def localId(self) -> str:
        return self._localId
    
    # Whether the Producer is closed.
    @property
    def closed(self) -> bool:
        return self._closed
    
    # Media kind.
    @property
    def kind(self) -> MediaStreamTrack.kind:
        return self._track.kind
    
    # Associated RTCRtpSender.
    @property
    def rtpSender(self) -> Optional[RTCRtpSender]:
        return self._rtpSender
    
    # The associated track.
    @property
    def track(self) -> Optional[MediaStreamTrack]:
        return self._track
    
    # RTP parameters.
    @property
    def rtpParameters(self) -> RtpParameters:
        return self._rtpParameters
    
    # Whether the Producer is paused.
    @property
    def paused(self) -> bool:
        return self._paused
    
    # Max spatial layer.
    @property
    def maxSpatialLayer(self) -> Optional[int]:
        return self._maxSpatialLayer
    
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
        
        logging.debug('Producer close()')

        self._closed = True

        self._destroyTrack()

        await self.emit_for_results('@close')

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
    
    # Get associated RTCRtpSender stats.
    async def getStats(self):
        if self._closed:
            raise InvalidStateError('closed')

        return await self.emit_for_results('@getstats')
    
    # Pauses sending media.
    def pause(self):
        logging.warning("Producer pause() | 'AudioStreamTrack' object has no attribute 'enabled' pause() won't work")
        logging.debug('Producer pause()')

        if self._closed:
            logging.debug('Producer pause() | Producer closed')
            return
        
        self._paused = True

        if self._track and self._disableTrackOnPause:
            # TODO: MediaStreamTrack missing enable property
            # self._track.enabled = False
            pass
        
        if self._zeroRtpOnPause:
            self.emit('@replacetrack')
        
        self._observer.emit('pause')
    
    # Resumes sending media.
    def resume(self):
        logging.warning("Producer pause() | 'AudioStreamTrack' object has no attribute 'enabled' resume() may not work")
        logging.debug('Producer resume()')

        if self._closed:
            logging.debug('Producer resume() | Producer closed')
            return
        
        self._paused = False

        if self._track and self._disableTrackOnPause:
            # TODO: MediaStreamTrack missing enable property
            # self._track.enabled = True
            pass
        
        if self._zeroRtpOnPause:
            self.emit('@replacetrack')
        
        self._observer.emit('resume')

    # Replaces the current track with a new one or null.
    async def replaceTrack(self, track: MediaStreamTrack):
        logging.debug(f'replaceTrack() [track: {track}]')

        if self._closed:
            # This must be done here. Otherwise there is no chance to stop the given
            # track.
            if self._stopTracks:
                track.stop()

            raise InvalidStateError('closed')
    
        elif track.readyState == 'ended':
            raise InvalidStateError('ended')
        
        # Do nothing if this is the same track as the current handled one.
        if track == self._track:
            logging.debug('Producer replaceTrack() | same track, ignored')
            return
        
        if not self._zeroRtpOnPause or not self._paused:
            await self.emit_for_results('@replacetrack', track)

        # Destroy the previous track.
        self._destroyTrack()

        self._track = track

        # If this Producer was paused/resumed and the state of the new
        # track does not match, fix it.
        if self._track and self._disableTrackOnPause:
            if not self._paused:
                # TODO: MediaStreamTrack missing enable property
                # self._track.enabled = True
                pass
            elif self._paused:
                # TODO: MediaStreamTrack missing enable property
                # self._track.enabled = False
                pass
        
        self._handleTrack()

    # Sets the video max spatial layer to be sent.
    async def setMaxSpatialLayer(self, spatialLayer: int):
        if self._closed:
            raise InvalidStateError('closed')
        
        elif self._kind != 'video':
            raise UnsupportedError('not a video Producer')
        
        if spatialLayer == self._maxSpatialLayer:
            return
        
        await self.emit_for_results('@setmaxspatiallayer', spatialLayer)

        self._maxSpatialLayer = spatialLayer
    
    # Sets the DSCP value.
    # TODO: RTCRtpEncodingParameters
    async def setRtpEncodingParameters(self, params):
        if self._closed:
            raise InvalidStateError('closed')
        
        await self.emit_for_results('@setrtpencodingparameters', params)
    
    def _onTrackEnded(self):
            logging.debug('Producer track "ended" event')
            self.emit('trackended')
            self._observer.emit('trackended')
    
    def _handleTrack(self):
        if not self._track:
            return

        self._track.on('ended', self._onTrackEnded)
    
    def _destroyTrack(self):
        if not self._track:
            return

        if self._track.readyState == 'ended':
            return

        self._track.remove_listener('ended', self._onTrackEnded)

        if self._stopTracks:
            self._track.stop()
