import sys
if sys.version_info >= (3, 8):
    from typing import Dict, Literal, List, Optional, Any
else:
    from typing import Dict, List, Optional, Any
    from typing_extensions import Literal

import logging
from aiortc import RTCIceServer, RTCPeerConnection, RTCSessionDescription, RTCRtpTransceiver, MediaStreamTrack
import sdp_transform
from .sdp import common_utils
from .sdp.remote_sdp import RemoteSdp
from .sdp.unified_plan_utils import addLegacySimulcast, getRtpEncodings
from .sdp.common_utils import applyCodecParameters, extractDtlsParameters
from .handler_interface import HandlerInterface
from ..ortc import ExtendedRtpCapabilities
from ..rtp_parameters import MediaKind, RtpParameters, RtpCapabilities, RtpCodecCapability, RtpEncodingParameters, RtcpParameters
from ..sctp_parameters import SctpCapabilities, SctpParameters, SctpStreamParameters
from ..ortc import getSendingRtpParameters, getSendingRemoteRtpParameters, reduceCodecs
from ..scalability_modes import parse as smParse
from ..models.transport import IceCandidate, IceParameters, DtlsParameters, DtlsRole
from ..models.handler_interface import HandlerRunOptions, HandlerSendOptions, HandlerSendResult, HandlerSendDataChannelResult, HandlerReceiveDataChannelResult, HandlerReceiveOptions, HandlerReceiveResult, HandlerReceiveDataChannelOptions
from ..producer import ProducerCodecOptions


SCTP_NUM_STREAMS = { 'OS': 1024, 'MIS': 1024 }

class AiortcHandler(HandlerInterface):

    def __init__(self, tracks: List[MediaStreamTrack]=[], loop=None):
        super(AiortcHandler, self).__init__(loop=loop)
        # Handler direction.
        self._direction: Optional[Literal['send', 'recv']] = None
        # Remote SDP handler.
        self._remoteSdp: Optional[RemoteSdp] = None
        # Generic sending RTP parameters for audio and video.
        self._sendingRtpParametersByKind: Dict[str, RtpParameters] = {}
        # Generic sending RTP parameters for audio and video suitable for the SDP
        # remote answer.
        self._sendingRemoteRtpParametersByKind: Dict[str, RtpParameters] = {}
        # RTCPeerConnection instance.
        self._pc: Optional[RTCPeerConnection] = None
        # Map of RTCTransceivers indexed by MID.
        self._mapMidTransceiver: Dict[str, RTCRtpTransceiver] = {}
        # Whether a DataChannel m=application section has been created.
        self._hasDataChannelMediaSection = False
        # Sending DataChannel id value counter. Incremented for each new DataChannel.
        self._nextSendSctpStreamId = 0
        # Got transport local and remote parameters.
        self._transportReady = False
        self._tracks = tracks

    @classmethod
    def createFactory(cls, tracks: List[MediaStreamTrack]=[], loop=None):
        return lambda: cls(tracks, loop)

    @property
    def name(self) -> str:
        return 'aiortc'
    
    @property
    def pc(self) -> RTCPeerConnection:
        if self._pc:
            return self._pc
        else:
            raise Exception('PeerConnection not ready')
    
    @property
    def remoteSdp(self) -> RemoteSdp:
        if self._remoteSdp:
            return self._remoteSdp
        else:
            raise Exception('Remote SDP not ready')
    
    async def close(self):
        logging.debug('close()')

        if self._pc:
            await self._pc.close()

    async def getNativeRtpCapabilities(self) -> RtpCapabilities:
        logging.debug('getNativeRtpCapabilities()')

        pc = RTCPeerConnection()
        for track in self._tracks:
            pc.addTrack(track)
        pc.addTransceiver('audio')
        pc.addTransceiver('video')

        offer: RTCSessionDescription = await pc.createOffer()
        await pc.close()

        sdpDict: dict = sdp_transform.parse(offer.sdp)
        nativeRtpCapabilities:RtpCapabilities = common_utils.extractRtpCapabilities(sdpDict)

        return nativeRtpCapabilities
    
    async def getNativeSctpCapabilities(self) -> SctpCapabilities:
        logging.debug('getNativeSctpCapabilities()')
        return SctpCapabilities.parse_obj({
            'numStreams': SCTP_NUM_STREAMS
        })
    
    def run(
        self,
        direction: Literal['send', 'recv'],
        iceParameters: IceParameters,
        iceCandidates: List[IceCandidate],
        dtlsParameters: DtlsParameters,
        extendedRtpCapabilities: ExtendedRtpCapabilities,
        sctpParameters: Optional[SctpParameters]=None,
        iceServers: Optional[RTCIceServer]=None,
        iceTransportPolicy: Optional[Literal['all', 'relay']]=None,
        additionalSettings: Optional[Any]=None,
        proprietaryConstraints: Optional[Any]=None
    ):
        logging.debug('AiortcHandler run()')
        options = HandlerRunOptions(
            direction=direction,
            iceParameters=iceParameters,
            iceCandidates=iceCandidates,
            dtlsParameters=dtlsParameters,
            sctpParameters=sctpParameters,
            iceServers=iceServers,
            iceTransportPolicy=iceTransportPolicy,
            additionalSettings=additionalSettings,
            proprietaryConstraints=proprietaryConstraints,
            extendedRtpCapabilities=extendedRtpCapabilities
        )
        self._direction = options.direction
        self._remoteSdp = RemoteSdp(
            iceParameters=options.iceParameters,
            iceCandidates=options.iceCandidates,
            dtlsParameters=options.dtlsParameters,
            sctpParameters=options.sctpParameters
        )
        self._sendingRtpParametersByKind = {
            'audio': getSendingRtpParameters('audio', options.extendedRtpCapabilities),
            'video': getSendingRtpParameters('video', options.extendedRtpCapabilities)
        }
        self._sendingRemoteRtpParametersByKind = {
            'audio': getSendingRemoteRtpParameters('audio', options.extendedRtpCapabilities),
            'video': getSendingRemoteRtpParameters('video', options.extendedRtpCapabilities)
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
        logging.warning('updateIceServers() not implemented')
        # TODO: aiortc can not update iceServers
    
    async def restartIce(self, iceParameters):
        logging.debug('restartIce()')
        self._remoteSdp.updateIceParameters(iceParameters)
        if not self._transportReady:
            return
        if self._direction == 'send':
            # NOTE: aiortc RTCPeerConnection createOffer do not have iceRestart options
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

    async def send(
        self,
        track: MediaStreamTrack,
        encodings: List[RtpEncodingParameters]=[],
        codecOptions: Optional[ProducerCodecOptions]=None,
        codec: Optional[RtpCodecCapability]=None
    ) -> HandlerSendResult:
        options = HandlerSendOptions(
            track=track,
            encodings=encodings,
            codecOptions=codecOptions,
            codec=codec
        )
        self._assertSendDirection()
        logging.debug(f'send() [kind:{options.track.kind}, track.id:{options.track.id}]')
        if options.encodings:
            for idx in range(len(options.encodings)):
                options.encodings[idx].rid = f'r{idx}'

        sendingRtpParameters: RtpParameters = self._sendingRtpParametersByKind[options.track.kind].copy(deep=True)
        sendingRtpParameters.codecs = reduceCodecs(sendingRtpParameters.codecs, options.codec)

        sendingRemoteRtpParameters: RtpParameters = self._sendingRemoteRtpParametersByKind[options.track.kind].copy(deep=True)
        sendingRemoteRtpParameters.codecs = reduceCodecs(sendingRemoteRtpParameters.codecs, options.codec)

        mediaSectionIdx = self.remoteSdp.getNextMediaSectionIdx()
        transceiver = self.pc.addTransceiver(options.track, direction='sendonly')

        offer: RTCSessionDescription  = await self.pc.createOffer()
        offerMediaDict: dict
        localSdpDict = sdp_transform.parse(offer.sdp)
        if not self._transportReady:
            await self._setupTransport(localDtlsRole='server', localSdpDict=localSdpDict)
        # Special case for VP9 with SVC.
        hackVp9Svc = False
        if options.encodings:
            layers=smParse(options.encodings[0].scalabilityMode if options.encodings[0].scalabilityMode else '')
        else:
            layers=smParse('')
        if len(options.encodings) == 1 and layers.spatialLayers > 1 and sendingRtpParameters.codecs[0].mimeType.lower() == 'video/vp9':
            logging.debug('send() | enabling legacy simulcast for VP9 SVC')
            hackVp9Svc = True
            localSdpDict = sdp_transform.parse
            offerMediaDict = localSdpDict['media'][mediaSectionIdx.idx]
            addLegacySimulcast(offerMediaDict=offerMediaDict, numStreams=layers.spatialLayers)
            offer = RTCSessionDescription(
                type='offer',
                sdp=sdp_transform.write(localSdpDict)
            )
        
        logging.debug(f'send() | calling pc.setLocalDescription() [offer:{offer}]')

        await self.pc.setLocalDescription(offer)
        # We can now get the transceiver.mid.
        localId = transceiver.mid
        # Set MID.
        sendingRtpParameters.mid = localId
        localSdpDict = sdp_transform.parse(self.pc.localDescription.sdp)

        offerMediaDict = localSdpDict['media'][mediaSectionIdx.idx]

        logging.debug(f"send() | get offerMediaDict {offerMediaDict} \n from localSdpDict {localSdpDict['media']} index {mediaSectionIdx.idx}")
        # Set RTCP CNAME.
        if sendingRtpParameters.rtcp == None:
            sendingRtpParameters.rtcp = RtcpParameters()
        sendingRtpParameters.rtcp.cname = common_utils.getCname(offerMediaDict)
        # Set RTP encodings by parsing the SDP offer if no encodings are given.
        if not options.encodings:
            sendingRtpParameters.encodings = getRtpEncodings(offerMediaDict)
        # Set RTP encodings by parsing the SDP offer and complete them with given
        # one if just a single encoding has been given.
        elif len(options.encodings) == 1:
            newEncodings = getRtpEncodings(offerMediaDict)
            if newEncodings and options.encodings[0]:
                firstEncodingDict: dict = newEncodings[0].dict()
                optionsEncodingDict: dict = options.encodings[0].dict()
                firstEncodingDict.update(optionsEncodingDict)
                newEncodings[0] = RtpEncodingParameters(**firstEncodingDict)
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
        self.remoteSdp.send(
            offerMediaDict=offerMediaDict,
            reuseMid=mediaSectionIdx.reuseMid,
            offerRtpParameters=sendingRtpParameters,
            answerRtpParameters=sendingRemoteRtpParameters,
            codecOptions=options.codecOptions,
            extmapAllowMixed=True
        )
        answer: RTCSessionDescription = RTCSessionDescription(
            type='answer',
            sdp=self.remoteSdp.getSdp()
        )
        logging.debug(f'send() | calling pc.setRemoteDescription() [answer:{answer}]')
        await self.pc.setRemoteDescription(answer)
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
    
    async def sendDataChannel(
        self,
        streamId: Optional[int]=None,
        ordered: Optional[bool]=True,
        maxPacketLifeTime: Optional[int]=None,
        maxRetransmits: Optional[int]=None,
        priority: Optional[Literal['very-low','low','medium','high']]=None,
        label: Optional[str]=None,
        protocol: Optional[str]=None
    ) -> HandlerSendDataChannelResult:
        if streamId == None:
            streamId = self._nextSendSctpStreamId
        options=SctpStreamParameters(
            streamId=streamId,
            ordered=ordered,
            maxPacketLifeTime=maxPacketLifeTime,
            maxRetransmits=maxRetransmits,
            priority=priority,
            label=label,
            protocol=protocol
        )
        self._assertSendDirection()
        logging.debug('sendDataChannel()')
        dataChannel = self.pc.createDataChannel(
            label=options.label,
            maxPacketLifeTime=options.maxPacketLifeTime,
            ordered=options.ordered,
            protocol=options.protocol,
            negotiated=True,
            id=self._nextSendSctpStreamId
        )
        # Increase next id.
        self._nextSendSctpStreamId = (self._nextSendSctpStreamId + 1) % SCTP_NUM_STREAMS.get('MIS', 1)
        # If this is the first DataChannel we need to create the SDP answer with
        # m=application section.
        if not self._hasDataChannelMediaSection:
            offer: RTCSessionDescription = await self.pc.createOffer()
            localSdpDict = sdp_transform.parse(offer.sdp)
            offerMediaDicts = [m for m in localSdpDict.get('media') if m.get('type') == 'application']
            if not offerMediaDicts:
                raise Exception('No datachannel')
            offerMediaDict = offerMediaDicts[0]

            if not self._transportReady:
                await self._setupTransport(localDtlsRole='server', localSdpDict=localSdpDict)
            
            logging.debug(f'sendDataChannel() | calling pc.setLocalDescription() [offer:{offer}]')
            await self.pc.setLocalDescription(offer)
            self.remoteSdp.sendSctpAssociation(offerMediaDict=offerMediaDict)
            answer: RTCSessionDescription = RTCSessionDescription(
                type='answer',
                sdp=self.remoteSdp.getSdp()
            )

            logging.debug(f'sendDataChannel() | calling pc.setRemoteDescription() [answer:{answer}]')
            await self.pc.setRemoteDescription(answer)
            self._hasDataChannelMediaSection = True
        
        return HandlerSendDataChannelResult(
            dataChannel=dataChannel,
            sctpStreamParameters=options
        )
    
    async def receive(
        self,
        trackId: str,
        kind: MediaKind,
        rtpParameters: RtpParameters
    ) -> HandlerReceiveResult:
        options = HandlerReceiveOptions(
            trackId=trackId,
            kind=kind,
            rtpParameters=rtpParameters
        )
        self._assertRecvDirection()
        logging.debug(f'receive() [trackId:{options.trackId}, kind:{options.kind}]')
        localId = options.rtpParameters.mid if options.rtpParameters.mid != None else str(len(self._mapMidTransceiver))
        self.remoteSdp.receive(
            mid=localId,
            kind=options.kind,
            offerRtpParameters=options.rtpParameters,
            streamId=options.rtpParameters.rtcp.cname,
            trackId=options.trackId
        )
        offer: RTCSessionDescription = RTCSessionDescription(
            type='offer',
            sdp=self.remoteSdp.getSdp()
        )
        logging.debug(f'receive() | calling pc.setRemoteDescription() [offer:{offer}]')
        await self.pc.setRemoteDescription(offer)
        answer: RTCSessionDescription = await self.pc.createAnswer()
        localSdpDict = sdp_transform.parse(answer.sdp)
        answerMediaDict = [m for m in localSdpDict.get('media') if str(m.get('mid')) == localId][0]
        # May need to modify codec parameters in the answer based on codec
        # parameters in the offer.
        applyCodecParameters(offerRtpParameters=options.rtpParameters, answerMediaDict=answerMediaDict)
        answer = RTCSessionDescription(
            type='answer',
            sdp=sdp_transform.write(localSdpDict)
        )
        if not self._transportReady:
            await self._setupTransport(localDtlsRole='client', localSdpDict=localSdpDict)
        logging.debug(f'receive() | calling pc.setLocalDescription() [answer:{answer}]')
        await self.pc.setLocalDescription(answer)
        transceivers = [t for t in self.pc.getTransceivers() if t.mid == localId]
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
        self.remoteSdp.closeMediaSection(transceiver.mid)
        offer: RTCSessionDescription = RTCSessionDescription(
            type='offer',
            sdp=self.remoteSdp.getSdp()
        )
        logging.debug(f'stopReceiving() | calling pc.setRemoteDescription() [offer:{offer}]')
        await self.pc.setRemoteDescription(offer)
        answer = await self.pc.createAnswer()
        logging.debug(f'stopReceiving() | calling pc.setLocalDescription() [answer:{answer}]')
        await self.pc.setLocalDescription(answer)
    
    async def getReceiverStats(self, localId: str):
        self._assertRecvDirection()
        transceiver = self._mapMidTransceiver.get(localId)
        if not transceiver:
            raise Exception('associated RTCRtpTransceiver not found')
        return await transceiver.receiver.getStats()
    
    async def receiveDataChannel(
        self,
        sctpStreamParameters: SctpStreamParameters,
        label: Optional[str]=None,
        protocol: Optional[str]=None
    ) -> HandlerReceiveDataChannelResult:
        options = HandlerReceiveDataChannelOptions(
            sctpStreamParameters=sctpStreamParameters,
            label=label,
            protocol=protocol
        )
        self._assertRecvDirection()
        logging.debug(f'[receiveDataChannel() [options:{options.sctpStreamParameters}]]')
        dataChannel = self.pc.createDataChannel(
            label=options.label,
            maxPacketLifeTime=options.sctpStreamParameters.maxPacketLifeTime,
            maxRetransmits=options.sctpStreamParameters.maxRetransmits,
            ordered=options.sctpStreamParameters.ordered,
            protocol=options.protocol,
            negotiated=True,
            id=options.sctpStreamParameters.streamId
        )

        # If this is the first DataChannel we need to create the SDP offer with
        # m=application section.
        if not self._hasDataChannelMediaSection:
            self.remoteSdp.receiveSctpAssociation()
            offer: RTCSessionDescription = RTCSessionDescription(
                type='offer',
                sdp=self.remoteSdp.getSdp()
            )
            logging.debug(f'receiveDataChannel() | calling pc.setRemoteDescription() [offer:{offer}]')
            await self.pc.setRemoteDescription(offer)
            answer = await self.pc.createAnswer()
            if not self._transportReady:
                localSdpDict = sdp_transform.parse(answer.sdp)
                await self._setupTransport(localDtlsRole='client', localSdpDict=localSdpDict)
            logging.debug(f'receiveDataChannel() | calling pc.setRemoteDescription() [answer:{answer}]')
            await self.pc.setLocalDescription(answer)
            self._hasDataChannelMediaSection = True
        return HandlerReceiveDataChannelResult(dataChannel=dataChannel)
    
    async def _setupTransport(self, localDtlsRole: DtlsRole, localSdpDict: dict={}):
        if localSdpDict == {}:
            localSdpDict = sdp_transform.parse(self.pc.localDescription.sdp)
        # Get our local DTLS parameters.
        dtlsParameters: DtlsParameters = extractDtlsParameters(localSdpDict)
        # Set our DTLS role.
        dtlsParameters.role = localDtlsRole
        # Update the remote DTLS role in the SDP.
        self.remoteSdp.updateDtlsRole('server' if localDtlsRole == 'client' else 'client')
        # Need to tell the remote transport about our parameters.
        await self.emit_for_results('@connect', dtlsParameters)
        self._transportReady = True
    
    def _assertSendDirection(self):
        if self._direction != 'send':
            raise Exception('method can just be called for handlers with "send" direction')
    
    def _assertRecvDirection(self):
        if self._direction != 'recv':
            raise Exception('method can just be called for handlers with "recv" direction')
