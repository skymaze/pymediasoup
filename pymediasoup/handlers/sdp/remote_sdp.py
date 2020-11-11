import sys
if sys.version_info >= (3, 8):
    from typing import List, Optional, Literal, Dict
else:
    from typing import List, Optional, Dict
    from typing_extensions import Literal

import logging
from pydantic import BaseModel
from aiortc import RTCIceCandidate
import sdp_transform
from .media_section import MediaSection, AnswerMediaSection, OfferMediaSection
from ...models.transport import IceCandidate, IceParameters, DtlsParameters, DtlsRole, PlainRtpParameters, DtlsRole
from ...producer import ProducerCodecOptions
from ...rtp_parameters import MediaKind, RtpParameters
from ...sctp_parameters import SctpParameters


class MediaSectionIdx(BaseModel):
    idx: int
    reuseMid: Optional[str]

class RemoteSdp:
    def __init__(
        self,
        iceParameters: Optional[IceParameters] = None,
        iceCandidates: List[IceCandidate] = [],
        dtlsParameters: Optional[DtlsParameters] = None,
        sctpParameters: SctpParameters = None,
        plainRtpParameters: Optional[PlainRtpParameters] = None,
        planB: bool = False
    ):
        self._iceParameters: Optional[IceParameters] = iceParameters
        self._iceCandidates: List[RTCIceCandidate] = iceCandidates
        self._dtlsParameters: Optional[DtlsParameters] = dtlsParameters
        self._sctpParameters: Optional[SctpParameters] = sctpParameters
        self._plainRtpParameters: Optional[PlainRtpParameters] = plainRtpParameters
        self._planB: bool = planB
        self._mediaSections: List[MediaSection] = []
        self._midToIndex: Dict[str, int] = {}
        self._firstMid: Optional[str] = None
        self._sdpDict: dict = {
            'version': 0,
            'origin': {
                'address': '0.0.0.0',
                'ipVer': 4,
                'netType': 'IN',
                'sessionId': 10000,
                'sessionVersion': 0,
                'username': 'mediasoup-client'
            },
            'name': '-',
            'timing': { 'start': 0, 'stop': 0 },
            'media': []
        }

        # If ICE parameters are given, add ICE-Lite indicator.
        if iceParameters:
            if iceParameters.iceLite:
                self._sdpDict['icelite'] = 'ice-lite'
        
        # If DTLS parameters are given, assume WebRTC and BUNDLE.
        if dtlsParameters:
            self._sdpDict['msidSemantic'] = { 'semantic': 'WMS', 'token': '*' }
            # NOTE: aiortc currently only support sha-256
            for fingerprint in dtlsParameters.fingerprints:
                if fingerprint.algorithm == 'sha-256':

                    self._sdpDict['fingerprint'] = {
                        'type': fingerprint.algorithm,
                        'hash': fingerprint.value
                    }
            # # NOTE: Mediasoup Client take the latest fingerprint.
            # self._sdpDict['fingerprint'] = {
            #     'type': dtlsParameters.fingerprints[-1].algorithm,
            #     'hash': dtlsParameters.fingerprints[-1].value
            # }
            self._sdpDict['groups'] = [{ 'type': 'BUNDLE', 'mids': '' }]
        
        # If there are plain RPT parameters, override SDP origin.
        if plainRtpParameters:
            self._sdpDict['origin']['address'] = plainRtpParameters.ip
            self._sdpDict['origin']['ipVer'] = plainRtpParameters.ipVersion
    
    def updateIceParameters(self, iceParameters: IceParameters):
        logging.debug(f'updateIceParameters() [iceParameters:{iceParameters}]')
        self._iceParameters = iceParameters
        self._sdpDict['icelite'] = 'ice-lite' if iceParameters.iceLite else None
    
    def updateDtlsRole(self, role: DtlsRole):
        logging.debug(f'updateDtlsRole() [role:{role}]')
        if self._dtlsParameters:
            self._dtlsParameters.role = role
            for mediaSection in self._mediaSections:
                mediaSection.setDtlsRole(role)
        
    def getNextMediaSectionIdx(self):
        # If a closed media section is found, return its index.
        for idx, mediaSection in enumerate(self._mediaSections):
            if mediaSection.closed:
                logging.debug(f'remoteSdp | getNextMediaSectionIdx() Closed media sections found { mediaSection}')
                return MediaSectionIdx(idx=idx, reuseMid=mediaSection.mid)
        # If no closed media section is found, return next one.
        logging.debug(f'remoteSdp | getNextMediaSectionIdx() No closed media sections found, return next {len(self._mediaSections)}')
        return MediaSectionIdx(idx=len(self._mediaSections))
    
    def send(
        self,
        offerMediaDict: dict,
        offerRtpParameters: RtpParameters,
        answerRtpParameters: RtpParameters,
        codecOptions: Optional[ProducerCodecOptions]=None,
        reuseMid: Optional[str]=None,
        extmapAllowMixed = False
    ):
        logging.debug(f'remoteSdp | send() offerMediaDict {offerMediaDict}')
        mediaSection = AnswerMediaSection(
            sctpParameters=self._sctpParameters,
            iceParameters=self._iceParameters,
            iceCandidates=self._iceCandidates,
            dtlsParameters=self._dtlsParameters,
            plainRtpParameters=self._plainRtpParameters,
            planB=self._planB,
            offerMediaDict=offerMediaDict,
            offerRtpParameters=offerRtpParameters,
            answerRtpParameters=answerRtpParameters,
            codecOptions=codecOptions,
            extmapAllowMixed=extmapAllowMixed
        )
        # Unified-Plan with closed media section replacement.
        if reuseMid:
            self._replaceMediaSection(mediaSection, reuseMid)
        # Unified-Plan or Plan-B with different media kind.
        elif mediaSection.mid not in self._midToIndex.keys():
            self._addMediaSection(mediaSection)
        # Plan-B with same media kind.
        else:
            self._replaceMediaSection(mediaSection)
        
    def receive(
        self,
        mid: str,
        kind: Literal['audio', 'video', 'application'],
        offerRtpParameters: RtpParameters,
        streamId: str,
        trackId: str
    ):
        idx: int = self._midToIndex.get(str(mid), -1)
        if idx != -1:
            mediaSection = self._mediaSections[idx]
            # Plan-B.
            mediaSection.planBReceive(offerRtpParameters, streamId, trackId)
            self._replaceMediaSection(mediaSection)
        # Unified-Plan or different media kind.
        else:
            mediaSection = OfferMediaSection(
                iceParameters=self._iceParameters,
                iceCandidates=self._iceCandidates,
                dtlsParameters=self._dtlsParameters,
                plainRtpParameters=self._plainRtpParameters,
                planB=self._planB,
                mid=mid,
                kind=kind,
                offerRtpParameters=offerRtpParameters,
                streamId=streamId,
                trackId=trackId
            )
            # Let's try to recycle a closed media section (if any).
            # NOTE: Yes, we can recycle a closed m=audio section with a new m=video.
            closedMediaSections = [ms for ms in self._mediaSections if ms.closed]
            if closedMediaSections:
                self._replaceMediaSection(mediaSection, closedMediaSections[0].mid)
            else:
                self._addMediaSection(mediaSection)
            
    def disableMediaSection(self, mid: str):
        idx: int = self._midToIndex.get(str(mid), -1)
        if idx == -1:
            raise Exception(f"no media section found with mid '{mid}'")
        mediaSection = self._mediaSections[idx]
        mediaSection.disable()
    
    def closeMediaSection(self, mid: str):
        idx: int = self._midToIndex.get(str(mid), -1)
        if idx == -1:
            raise Exception(f"no media section found with mid '{mid}'")
        mediaSection = self._mediaSections[idx]
        # NOTE: Closing the first m section is a pain since it invalidates the
        # bundled transport, so let's avoid it.
        if mid == self._firstMid:
            logging.debug(f'closeMediaSection() | cannot close first media section, disabling it instead [mid:{mid}]')
            self.disableMediaSection(mid)
            return
        mediaSection.close()
        # Regenerate BUNDLE mids.
        self._regenerateBundleMids()
    
    def planBStopReceiving(self, mid: str, offerRtpParameters: RtpParameters):
        idx: int = self._midToIndex.get(str(mid), -1)
        if idx == -1:
            raise Exception(f"no media section found with mid '{mid}'")
        mediaSection = self._mediaSections[idx]
        mediaSection.planBStopReceiving(offerRtpParameters)
        self._replaceMediaSection(mediaSection)
    
    def sendSctpAssociation(self, offerMediaDict: dict):
        mediaSection = AnswerMediaSection(
            iceParameters=self._iceParameters,
            iceCandidates=self._iceCandidates,
            dtlsParameters=self._dtlsParameters,
            sctpParameters=self._sctpParameters,
            plainRtpParameters=self._plainRtpParameters,
            offerMediaDict=offerMediaDict
        )
        self._addMediaSection(mediaSection)
    
    def receiveSctpAssociation(self, oldDataChannelSpec: bool = False):
        mediaSection = OfferMediaSection(
            iceParameters=self._iceParameters,
            iceCandidates=self._iceCandidates,
            dtlsParameters=self._dtlsParameters,
            sctpParameters=self._sctpParameters,
            plainRtpParameters=self._plainRtpParameters,
            mid='datachannel',
            kind='application',
            oldDataChannelSpec=oldDataChannelSpec
        )
        self._addMediaSection(mediaSection)
    
    def getSdp(self) -> str:
        # Increase SDP version.
        self._sdpDict['origin']['sessionVersion'] += 1
        return sdp_transform.write(self._sdpDict)
    
    def _addMediaSection(self, newMediaSection: MediaSection):
        if self._firstMid == None:
            self._firstMid = newMediaSection.mid
        # Add to the list.
        self._mediaSections.append(newMediaSection)
        # Add to the map.
        self._midToIndex[newMediaSection.mid] = len(self._mediaSections) - 1
        # Add to the SDP object.
        self._sdpDict['media'].append(newMediaSection.getDict())
        # Regenerate BUNDLE mids.
        self._regenerateBundleMids()

    def _replaceMediaSection(self, newMediaSection: MediaSection, reuseMid: Optional[str]=None):
        # Store it in the map.
        if reuseMid:
            idx = self._midToIndex.get(str(reuseMid), -1)
            if idx == -1:
                raise Exception(f"no media section found with mid '{reuseMid}'")
            oldMediaSection = self._mediaSections[idx]
            # Replace the index in the vector with the new media section.
            self._mediaSections[idx] = newMediaSection
            # Update the map.
            del self._midToIndex[oldMediaSection.mid]
            self._midToIndex[newMediaSection.mid] =idx
            # Update the SDP object.
            self._sdpDict['media'][idx] = newMediaSection.getDict()
            # Regenerate BUNDLE mids.
            self._regenerateBundleMids()
        else:
            idx = self._midToIndex.get(newMediaSection.mid, -1)
            if idx == -1:
                raise Exception(f"no media section found with mid '{newMediaSection.mid}'")
            # Replace the index in the vector with the new media section.
            self._mediaSections[idx] = newMediaSection
            # Update the SDP object.
            self._sdpDict['media'][idx] = newMediaSection.getDict()
    
    def _regenerateBundleMids(self):
        if not self._dtlsParameters:
            return
        self._sdpDict['groups'][0]['mids'] = ' '.join([ms.mid for ms in self._mediaSections if not ms.closed])