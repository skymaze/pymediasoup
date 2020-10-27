import logging
from typing import Dict, Literal, List, Optional, Any
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCRtpTransceiver
from .sdp.remote_sdp import RemoteSdp
from .sdp import common_utils
from .sdp.sdp_transform import parse as sdpParse
from .sdp.sdp_transform import write as sdpWrite
from .handler_interface import HandlerInterface, HandlerSendOptions, HandlerSendResult, HandlerSendDataChannelResult, HandlerReceiveOptions, HandlerReceiveResult, HandlerReceiveDataChannelOptions
from ..rtp_parameters import RtpParameters, RtpCapabilities, RtpEncodingParameters
from ..sctp_parameters import SctpCapabilities, SctpStreamParameters
from ..ortc import getSendingRtpParameters, getSendingRemoteRtpParameters, reduceCodecs
from ..scalability_modes import parse as smParse
from .sdp.unified_plan_utils import addLegacySimulcast, getRtpEncodings
from .sdp.common_utils import applyCodecParameters, extractDtlsParameters
from ..transport import DtlsParameters


SCTP_NUM_STREAMS = { 'OS': 1024, 'MIS': 1024 }

class AiortcHandler(HandlerInterface):
    # Handler direction.
    _direction: Optional[Literal['send', 'recv']]
    # Remote SDP handler.
    _remoteSdp: Optional[RemoteSdp]
    # Generic sending RTP parameters for audio and video.
    _sendingRtpParametersByKind: Optional[Dict[str, RtpParameters]]
    # Generic sending RTP parameters for audio and video suitable for the SDP
    # remote answer.
    _sendingRemoteRtpParametersByKind: Optional[Dict[str, RtpParameters]]
    # RTCPeerConnection instance.
    _pc: RTCPeerConnection
    # Map of RTCTransceivers indexed by MID.
    _mapMidTransceiver: Dict[str, RTCRtpTransceiver] = {}
    # Whether a DataChannel m=application section has been created.
    _hasDataChannelMediaSection = False
    # Sending DataChannel id value counter. Incremented for each new DataChannel.
    _nextSendSctpStreamId = 0
    # Got transport local and remote parameters.
    _transportReady = False

    def __init__(self, loop=None):
        super(AiortcHandler, self).__init__(loop=loop)

    @property
    def name(self) -> str:
        return 'aiortc'
    
    async def close(self):
        logging.debug('close()')

        if self._pc:
            await self._pc.close()

    async def getNativeRtpCapabilities(self) -> RtpCapabilities:
        logging.debug('getNativeRtpCapabilities()')

        pc = RTCPeerConnection()
        pc.addTransceiver('audio')
        pc.addTransceiver('video')

        offer: RTCSessionDescription = await pc.createOffer()
        await pc.close()

        sdpDict: dict = sdpParse(offer.sdp)
        nativeRtpCapabilities:RtpCapabilities = common_utils.extractRtpCapabilities(sdpDict)

        return nativeRtpCapabilities
    
    async def getNativeSctpCapabilities(self) -> SctpCapabilities:
        logging.debug('getNativeSctpCapabilities()')
        return SctpCapabilities.parse_obj({
            'numStreams': SCTP_NUM_STREAMS
        })
    
    def run(
        self,
        direction,
        iceParameters,
        iceCandidates,
        dtlsParameters,
        sctpParameters,
        iceServers,
        iceTransportPolicy,
        additionalSettings,
        proprietaryConstraints,
        extendedRtpCapabilities
    ):
        logging.debug('run()')
        self._direction = direction
        self._remoteSdp = RemoteSdp(
            iceParameters=iceParameters,
            iceCandidates=iceCandidates,
            dtlsParameters=dtlsParameters,
            sctpParameters=sctpParameters
        )
        self._sendingRtpParametersByKind = {
            'audio': getSendingRtpParameters('audio', extendedRtpCapabilities),
            'video': getSendingRtpParameters('video', extendedRtpCapabilities)
        }
        self._sendingRemoteRtpParametersByKind = {
            'audio': getSendingRemoteRtpParameters('audio', extendedRtpCapabilities),
            'video': getSendingRemoteRtpParameters('video', extendedRtpCapabilities)
        }
        self._pc = RTCPeerConnection()
        @self._pc.on('iceconnectionstatechange')
        def on_iceconnectionstatechange():
            if self._pc.iceConnectionState == 'checking':
                self.emit('@connectionstatechange', 'connecting')
            elif self._pc.iceConnectionState in ['connected', 'completed']:
                self.emit('@connectionstatechange', 'connected')
            elif self._pc.iceConnectionState == 'failed':
                self.emit('@connectionstatechange', 'failed')
            elif self._pc.iceConnectionState == 'disconnected':
                self.emit('@connectionstatechange', 'disconnected')
            elif self._pc.iceConnectionState == 'closed':
                self.emit('@connectionstatechange', 'closed')
        
    async def updateIceServers(self, iceServers):
        logging.debug('updateIceServers() passed')
        # TODO: aiortc can not update iceServers
    
    async def restartIce(self, iceParameters):
        logging.debug('restartIce()')
        self._remoteSdp.updateIceParameters(iceParameters)
        if not self._transportReady:
            return
        if self._direction == 'send':
            # NOTE: aiortc RTCPeerConnection createOffer do not have iceRestart
            offer = await self._pc.createOffer()
            logging.debug(f'restartIce() | calling pc.setLocalDescription() [offer:{offer}]')
            await self._pc.setLocalDescription(offer)
            answer: RTCSessionDescription = RTCSessionDescription(
                type='answer',
                sdp=self._remoteSdp.getSdp()
            )
            logging.debug(f'restartIce() | calling pc.setRemoteDescription() [answer:{answer}]')
            await self._pc.setRemoteDescription(answer)
        else:
            offer: RTCSessionDescription = RTCSessionDescription(
                type='offer',
                sdp=self._remoteSdp.getSdp()
            )
            logging.debug(f'restartIce() | calling pc.setRemoteDescription() [offer:{offer}]')
            await self._pc.setRemoteDescription(offer)
            answer = await self._pc.createAnswer()
            logging.debug(f'restartIce() | calling pc.setLocalDescription() [answer:{answer}]')
            await self._pc.setLocalDescription(answer)
        
    async def getTransportStats(self):
        return self._pc.getStats()

    async def send(self, options: HandlerSendOptions):
        self._assertSendDirection()
        logging.debug(f'send() [kind:{options.track.kind}, track.id:{options.track.id}]')
        if options.encodings:
            for idx in range(len(options.encodings)):
                options.encodings[idx].rid = f'r{idx}'
        sendingRtpParameters: RtpParameters = RtpParameters(**self._sendingRtpParametersByKind[options.track.kind].dict())
        sendingRtpParameters.codecs = reduceCodecs(sendingRtpParameters.codecs, options.codec)

        sendingRemoteRtpParameters: RtpParameters = RtpParameters(**self._sendingRemoteRtpParametersByKind[options.track.kind].dict())
        sendingRemoteRtpParameters.codecs = reduceCodecs(sendingRemoteRtpParameters.codecs, options.codec)

        mediaSectionIdx = self._remoteSdp.getNextMediaSectionIdx()
        transceiver = self._pc.addTransceiver(options.track, direction='sendonly')

        offer = self._pc.createOffer()
        localSdpDict = sdpParse(offer.sdp)
        if not self._transportReady:
            await self._setupTransport(localDtlsRole='server', localSdpDict=localSdpDict)
        # Special case for VP9 with SVC.
        hackVp9Svc = False
        layers=smParse(options.encodings[0].scalabilityMode)
        if len(options.encodings) == 1 and layers.spatialLayers > 1 and sendingRtpParameters.codecs[0].mimeType.lower() == 'video/vp9':
            logging.debug('send() | enabling legacy simulcast for VP9 SVC')
            hackVp9Svc = True
            localSdpDict = sdpParse
            offerMediaDict = localSdpDict['media'][mediaSectionIdx['idx']]
            addLegacySimulcast(offerMediaDict=offerMediaDict, numStreams=layers.spatialLayers)
            offer: RTCSessionDescription = RTCSessionDescription(
                type='offer',
                sdp=sdpWrite(localSdpDict)
            )
        
        logging.debug(f'send() | calling pc.setLocalDescription() [offer:{offer}]')

        await self._pc.setLocalDescription(offer)
        # We can now get the transceiver.mid.
        localId = transceiver.mid
        # Set MID.
        sendingRtpParameters.mid = localId
        localSdpDict = sdpParse(self._pc.localDescription.sdp)
        offerMediaDict = localSdpDict['media'][mediaSectionIdx['idx']]
        # Set RTCP CNAME.
        sendingRtpParameters.rtcp.cname = common_utils.getCname(offerMediaDict)
        # Set RTP encodings by parsing the SDP offer if no encodings are given.
        if not options.encodings:
            sendingRtpParameters.encodings = getRtpEncodings(offerMediaDict)
        # Set RTP encodings by parsing the SDP offer and complete them with given
        # one if just a single encoding has been given.
        elif len(options.encodings) == 1:
            newEncodings = getRtpEncodings(offerMediaDict)
            newEncodingDict: dict = newEncodings[0].dict().update(options.encodings[0].dict())
            newEncodings[0]:RtpEncodingParameters = RtpEncodingParameters(**newEncodingDict)
            if hackVp9Svc:
                newEncodings = [newEncodings[0]]
            sendingRtpParameters.encodings = newEncodings
        # Otherwise if more than 1 encoding are given use them verbatim.
        else:
            sendingRtpParameters.encodings = options.encodings
        
        # If VP8 or H264 and there is effective simulcast, add scalabilityMode to
        # each encoding.
        if len(sendingRtpParameters.encodings) > 1 and (sendingRtpParameters.codecs[0].mimeType.lower() == 'video/vp8' or sendingRtpParameters.codecs[0].mimeType.lower() == 'video/h264'):
            for encoding in sendingRtpParameters.encodings:
                encoding.scalabilityMode = 'S1T3'
        self._remoteSdp.send(
            offerMediaDict=offerMediaDict,
            reuseMid=mediaSectionIdx.reuseMid,
            offerRtpParameters=sendingRtpParameters,
            answerRtpParameters=sendingRemoteRtpParameters,
            codecOptions=options.codecOptions,
            extmapAllowMixed=True
        )
        answer: RTCSessionDescription = RTCSessionDescription(
            type='answer',
            sdp=self._remoteSdp.getSdp()
        )
        logging.debug(f'send() | calling pc.setRemoteDescription() [answer:{answer}]')
        await self._pc.setRemoteDescription(answer)
        # Store in the map.
        self._mapMidTransceiver[localId] = transceiver
        return HandlerSendResult(
            localId=localId,
            rtpParameters=sendingRtpParameters,
            rtpSender=transceiver.sender
        )

    async def stopSending(self, localId):
        pass
        # self._assertSendDirection()
        # logging.debug(f'stopSending() [localId:{localId}]')
        # transceiver = self._mapMidTransceiver.get(localId)
        # if not transceiver:
        #     raise Exception('associated RTCRtpTransceiver not found')
        # transceiver.sender.replaceTrack()
        # # TODO:RTCPeerConnection do not have removeTrack()
        # self._pc.removeTrack(transceiver.sender)
        # self._remoteSdp.closeMediaSection(transceiver.mid)
        # offer = await self._pc.createOffer()
        # logging.debug(f'stopSending() | calling pc.setLocalDescription() [offer:{offer}]')
        # await self._pc.localDescription(offer)
        # answer: RTCSessionDescription = RTCSessionDescription(
        #     type='answer',
        #     sdp=self._remoteSdp.getSdp()
        # )
        # logging.debug(f'stopSending() | calling pc.setRemoteDescription() [answer:{answer}]')
        # await self._pc.setRemoteDescription(answer)
    
    async def replaceTrack(self, localId, track=None):
        self._assertSendDirection()
        if track:
            logging.debug(f'replaceTrack() [localId:{localId}, track.id:{track.id}]')
        else:
            logging.debug(f'replaceTrack() [localId:{localId}, no track]')
        transceiver = self._mapMidTransceiver.get(localId)
        if not transceiver:
            raise Exception('associated RTCRtpTransceiver not found')

        await transceiver.sender.replaceTrack(track)
    
    async def setMaxSpatialLayer(self, localId: str, spatialLayer: int):
        logging.warning('setMaxSpatialLayer() not implemented')
        # NOTE: RTCRtpSender do not have getParameters()
        # self._assertSendDirection()
        # logging.debug(f'setMaxSpatialLayer() [localId:{localId}, spatialLayer:{spatialLayer}]')
        # transceiver = self._mapMidTransceiver.get(localId)
        # if not transceiver:
        #     raise Exception('associated RTCRtpTransceiver not found')
        # parameters = transceiver.sender.getParameters()
    
    async def setRtpEncodingParameters(self, localId: str, params: Any):
        logging.warning('setRtpEncodingParameters() not implemented')
        # NOTE: RTCRtpSender do not have getParameters()
    
    async def getSenderStats(self, localId: str):
        self._assertSendDirection()
        transceiver = self._mapMidTransceiver.get(localId)
        if not transceiver:
            raise Exception('associated RTCRtpTransceiver not found')
        return await transceiver.sender.getStats()
    
    async def sendDataChannel(self, options: SctpStreamParameters) -> HandlerSendDataChannelResult:
        self._assertSendDirection()
        logging.debug(f'sendDataChannel() [options:{options}]')
        dataChannel = self._pc.createDataChannel(
            label=options.label,
            maxPacketLifeTime=options.maxPacketLifeTime,
            ordered=options.ordered,
            protocol=options.protocol,
            negotiated=True,
            id=self._nextSendSctpStreamId
        )
        # Increase next id.
        self._nextSendSctpStreamId = (self._nextSendSctpStreamId + 1) % SCTP_NUM_STREAMS.get('MIS')
        # If this is the first DataChannel we need to create the SDP answer with
        # m=application section.
        if not self._hasDataChannelMediaSection:
            offer: RTCSessionDescription = await self._pc.createOffer()
            localSdpDict = sdpParse(offer.sdp)
            offerMediaDicts = [m for m in localSdpDict.get('media') if m.get('type') == 'application']
            if not offerMediaDicts:
                raise Exception('No datachannel')
            offerMediaDict = offerMediaDicts[0]

            if not self._transportReady:
                await self._setupTransport(localDtlsRole='server', localSdpDict=localSdpDict)
            
            logging.debug(f'sendDataChannel() | calling pc.setLocalDescription() [offer:{offer}]')
            await self._pc.setLocalDescription(offer)
            self._remoteSdp.sendSctpAssociation(offerMediaDict=offerMediaDict)
            answer: RTCSessionDescription = RTCSessionDescription(
                type='answer',
                sdp=self._remoteSdp.getSdp()
            )

            logging.debug('sendDataChannel() | calling pc.setRemoteDescription() [answer:{answer}]')
            await self._pc.setRemoteDescription(answer)
            self._hasDataChannelMediaSection = True
        
        return HandlerSendDataChannelResult(
            dataChannel=dataChannel,
            sctpStreamParameters=options
        )
    
    async def receive(self, options: HandlerReceiveOptions) -> HandlerReceiveResult:
        self._assertRecvDirection()
        logging.debug(f'receive() [trackId:{options.trackId}, kind:{options.kind}]')
        localId = options.rtpParameters.mid if options.rtpParameters.mid else str(len(self._mapMidTransceiver))
        self._remoteSdp.receive(
            mid=localId,
            kind=options.kind,
            offerRtpParameters=options.rtpParameters,
            streamId=options.rtpParameters.rtcp.cname,
            trackId=options.trackId
        )
        offer: RTCSessionDescription = RTCSessionDescription(
            type='offer',
            sdp=self._remoteSdp.getSdp()
        )
        logging.debug(f'receive() | calling pc.setRemoteDescription() [offer:{offer}]')
        await self._pc.setRemoteDescription(offer)
        answer = await self._pc.createAnswer()
        localSdpDict = sdpParse(answer.sdp)
        answerMediaDict = [m for m in localSdpDict.get('media') if m.get('mid') == localId][0]
        # May need to modify codec parameters in the answer based on codec
        # parameters in the offer.
        applyCodecParameters(offerRtpParameters=options.rtpParameters, answerMediaDict=answerMediaDict)
        answer: RTCSessionDescription = RTCSessionDescription(
            type='answer',
            sdp=sdpWrite(localSdpDict)
        )
        if not self._transportReady:
            await self._setupTransport(localDtlsRole='client', localSdpDict=localSdpDict)
        logging.debug(f'receive() | calling pc.setLocalDescription() [answer:{answer}]')
        await self._pc.setLocalDescription(answer)
        transceivers = [t for t in self._pc.getTransceivers() if t.mid == localId]
        if not transceivers:
            raise Exception('new RTCRtpTransceiver not found')
        # Store in the map.
        transceiver = transceivers[0]
        self._mapMidTransceiver[localId] = transceiver

        return HandlerReceiveResult(
            localId=localId,
            track=transceiver.receiver.track,
            rtpReceiver=transceiver.receiver
        )
        
    async def stopReceiving(self, localId: str):
        self._assertRecvDirection()
        logging.debug(f'stopReceiving() [localId:{localId}]')
        transceiver = self._mapMidTransceiver.get(localId)
        if not transceiver:
            raise Exception('associated RTCRtpTransceiver not found')
        self._remoteSdp.closeMediaSection(transceiver.mid)
        offer: RTCSessionDescription = RTCSessionDescription(
            type='offer',
            sdp=self._remoteSdp.getSdp()
        )
        logging.debug(f'stopReceiving() | calling pc.setRemoteDescription() [offer:{offer}]')
        await self._pc.setRemoteDescription(offer)
        answer = await self._pc.createAnswer()
        logging.debug(f'stopReceiving() | calling pc.setLocalDescription() [answer:{answer}]')
        await self._pc.setLocalDescription(answer)
    
    async def getReceiverStats(self, localId: str):
        self._assertRecvDirection()
        transceiver = self._mapMidTransceiver.get(localId)
        if not transceiver:
            raise Exception('associated RTCRtpTransceiver not found')
        return await transceiver.receiver.getStats()
    
    async def receiveDataChannel(self, options: HandlerReceiveDataChannelOptions) -> HandlerReceiveDataChannelResult:
        self._assertRecvDirection()
        logging.debug(f'[receiveDataChannel() [options:{options.sctpStreamParameters}]]')
        dataChannel = self._pc.createDataChannel(
            label=options.label,
            maxPacketLifeTime=options.sctpStreamParameters.maxPacketLifeTime,
            maxRetransmits=options.sctpStreamParameters.maxRetransmits,
            ordered=options.sctpStreamParameters.ordered,
            protocol=options.sctpStreamParameters.protocol,
            negotiated=True,
            id=options.sctpStreamParameters.streamId
        )

        # If this is the first DataChannel we need to create the SDP offer with
        # m=application section.
        if not self._hasDataChannelMediaSection:
            self._remoteSdp.receiveSctpAssociation()
            offer: RTCSessionDescription = RTCSessionDescription(
                type='offer',
                sdp=self._remoteSdp.getSdp()
            )
            logging.debug(f'receiveDataChannel() | calling pc.setRemoteDescription() [offer:{offer}]')
            await self._pc.setRemoteDescription(offer)
            answer = await self._pc.createAnswer()
            if not self._transportReady:
                localSdpDict = sdpParse(answer.sdp)
                await self._setupTransport(localDtlsRole='client', localSdpDict=localSdpDict)
            logging.debug(f'receiveDataChannel() | calling pc.setRemoteDescription() [answer:{answer}]')
            await self._pc.setLocalDescription(answer)
            self._hasDataChannelMediaSection = True
        return dataChannel
    
    async def _setupTransport(self, localDtlsRole: str, localSdpDict: Optional[dict]=None):
        if not localSdpDict:
            localSdpDict = sdpParse(self._pc.localDescription.sdp)
        # Get our local DTLS parameters.
        dtlsParameters: DtlsParameters = extractDtlsParameters(localSdpDict)
        # Set our DTLS role.
        dtlsParameters.role = localDtlsRole
        # Update the remote DTLS role in the SDP.
        self._remoteSdp.updateDtlsRole('server' if localDtlsRole == 'client' else 'client')
        # Need to tell the remote transport about our parameters.
        await self.emit_for_results('@connect', dtlsParameters)
        self._transportReady = True
    
    def _assertSendDirection(self):
        if self._direction != 'send':
            raise Exception('method can just be called for handlers with "send" direction')
    
    def _assertRecvDirection(self):
        if self._direction != 'recv':
            raise Exception('method can just be called for handlers with "recv" direction')
        