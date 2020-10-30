from uuid import uuid4
from typing import List
from pymediasoup.rtp_parameters import RtpCapabilities
from pymediasoup.models.transport import IceParameters, IceCandidate, DtlsParameters, DtlsFingerprint, SctpParameters


def generateRouterRtpCapabilities():
    return RtpCapabilities(
        **{
            'codecs' :
            [
                {
                    'mimeType'             : 'audio/opus',
                    'kind'                 : 'audio',
                    'preferredPayloadType' : 100,
                    'clockRate'            : 48000,
                    'channels'             : 2,
                    'rtcpFeedback'         :
                    [
                        { 'type': 'transport-cc' }
                    ],
                    'parameters' :
                    {
                        'useinbandfec' : 1,
                        'foo'          : 'bar'
                    }
                },
                {
                    'mimeType'             : 'video/VP8',
                    'kind'                 : 'video',
                    'preferredPayloadType' : 101,
                    'clockRate'            : 90000,
                    'rtcpFeedback'         :
                    [
                        { 'type': 'nack' },
                        { 'type': 'nack', 'parameter': 'pli' },
                        { 'type': 'ccm', 'parameter': 'fir' },
                        { 'type': 'goog-remb' },
                        { 'type': 'transport-cc' }
                    ],
                    'parameters' :
                    {
                        'x-google-start-bitrate' : 1500
                    }
                },
                {
                    'mimeType'             : 'video/rtx',
                    'kind'                 : 'video',
                    'preferredPayloadType' : 102,
                    'clockRate'            : 90000,
                    'rtcpFeedback'         : [],
                    'parameters'           :
                    {
                        'apt' : 101
                    }
                },
                {
                    'mimeType'             : 'video/H264',
                    'kind'                 : 'video',
                    'preferredPayloadType' : 103,
                    'clockRate'            : 90000,
                    'rtcpFeedback'         :
                    [
                        { 'type': 'nack' },
                        { 'type': 'nack', 'parameter': 'pli' },
                        { 'type': 'ccm', 'parameter': 'fir' },
                        { 'type': 'goog-remb' },
                        { 'type': 'transport-cc' }
                    ],
                    'parameters' :
                    {
                        'level-asymmetry-allowed' : 1,
                        'packetization-mode'      : 1,
                        'profile-level-id'        : '42e01f'
                    }
                },
                {
                    'mimeType'             : 'video/rtx',
                    'kind'                 : 'video',
                    'preferredPayloadType' : 104,
                    'clockRate'            : 90000,
                    'rtcpFeedback'         : [],
                    'parameters'           :
                    {
                        'apt' : 103
                    }
                }
            ],
            'headerExtensions' :
            [
                {
                    'kind'             : 'audio',
                    'uri'              : 'urn:ietf:params:rtp-hdrext:sdes:mid',
                    'preferredId'      : 1,
                    'preferredEncrypt' : False,
                    'direction'        : 'sendrecv'
                },
                {
                    'kind'             : 'video',
                    'uri'              : 'urn:ietf:params:rtp-hdrext:sdes:mid',
                    'preferredId'      : 1,
                    'preferredEncrypt' : False,
                    'direction'        : 'sendrecv'
                },
                {
                    'kind'             : 'video',
                    'uri'              : 'urn:ietf:params:rtp-hdrext:sdes:rtp-stream-id',
                    'preferredId'      : 2,
                    'preferredEncrypt' : False,
                    'direction'        : 'recvonly'
                },
                {
                    'kind'             : 'video',
                    'uri'              : 'urn:ietf:params:rtp-hdrext:sdes:repaired-rtp-stream-id',
                    'preferredId'      : 3,
                    'preferredEncrypt' : False,
                    'direction'        : 'recvonly'
                },
                {
                    'kind'             : 'audio',
                    'uri'              : 'http://www.webrtc.org/experiments/rtp-hdrext/abs-send-time',
                    'preferredId'      : 4,
                    'preferredEncrypt' : False,
                    'direction'        : 'sendrecv'
                },
                {
                    'kind'             : 'video',
                    'uri'              : 'http://www.webrtc.org/experiments/rtp-hdrext/abs-send-time',
                    'preferredId'      : 4,
                    'preferredEncrypt' : False,
                    'direction'        : 'sendrecv'
                },
                {
                    'kind'             : 'audio',
                    'uri'              : 'http://www.ietf.org/id/draft-holmer-rmcat-transport-wide-cc-extensions-01',
                    'preferredId'      : 5,
                    'preferredEncrypt' : False,
                    'direction'        : 'recvonly'
                },
                {
                    'kind'             : 'video',
                    'uri'              : 'http://www.ietf.org/id/draft-holmer-rmcat-transport-wide-cc-extensions-01',
                    'preferredId'      : 5,
                    'preferredEncrypt' : False,
                    'direction'        : 'sendrecv'
                },
                {
                    'kind'             : 'video',
                    'uri'              : 'http://tools.ietf.org/html/draft-ietf-avtext-framemarking-07',
                    'preferredId'      : 6,
                    'preferredEncrypt' : False,
                    'direction'        : 'sendrecv'
                },
                {
                    'kind'             : 'video',
                    'uri'              : 'urn:ietf:params:rtp-hdrext:framemarking',
                    'preferredId'      : 7,
                    'preferredEncrypt' : False,
                    'direction'        : 'sendrecv'
                },
                {
                    'kind'             : 'audio',
                    'uri'              : 'urn:ietf:params:rtp-hdrext:ssrc-audio-level',
                    'preferredId'      : 10,
                    'preferredEncrypt' : False,
                    'direction'        : 'sendrecv'
                },
                {
                    'kind'             : 'video',
                    'uri'              : 'urn:3gpp:video-orientation',
                    'preferredId'      : 11,
                    'preferredEncrypt' : False,
                    'direction'        : 'sendrecv'
                },
                {
                    'kind'             : 'video',
                    'uri'              : 'urn:ietf:params:rtp-hdrext:toffset',
                    'preferredId'      : 12,
                    'preferredEncrypt' : False,
                    'direction'        : 'sendrecv'
                }
            ],
            'fecMechanisms' : []
        }
    )

def generateTransportRemoteParameters():
    id: str = str(uuid4())
    iceParameters: IceParameters = IceParameters(**{
        'iceLite'          : True,
        'password'         : 'yku5ej8nvfaor28lvtrabcx0wkrpkztz',
        'usernameFragment' : 'h3hk1iz6qqlnqlne'
    })
    iceCandidates: List[IceCandidate] = [
        IceCandidate(**{
            'family'     : 'ipv4',
            'foundation' : 'udpcandidate',
            'ip'         : '9.9.9.9',
            'port'       : 40533,
            'priority'   : 1078862079,
            'protocol'   : 'udp',
            'type'       : 'host'
        }),
        IceCandidate(**{
            'family'     : 'ipv6',
            'foundation' : 'udpcandidate',
            'ip'         : '9.9.9.9',
            'port'       : 41333,
            'priority'   : 1078862089,
            'protocol'   : 'udp',
            'type'       : 'host'
        })
    ]
    dtlsParameters: DtlsParameters = DtlsParameters(**{
        'fingerprints' :[
            {
                'algorithm' : 'sha-256',
                'value'     : 'A9:F4:E0:D2:74:D3:0F:D9:CA:A5:2F:9F:7F:47:FA:F0:C4:72:DD:73:49:D0:3B:14:90:20:51:30:1B:90:8E:71'
            },
            {
                'algorithm' : 'sha-384',
                'value'     : '03:D9:0B:87:13:98:F6:6D:BC:FC:92:2E:39:D4:E1:97:32:61:30:56:84:70:81:6E:D1:82:97:EA:D9:C1:21:0F:6B:C5:E7:7F:E1:97:0C:17:97:6E:CF:B3:EF:2E:74:B0'
            },
            {
                'algorithm' : 'sha-512',
                'value'     : '84:27:A4:28:A4:73:AF:43:02:2A:44:68:FF:2F:29:5C:3B:11:9A:60:F4:A8:F0:F5:AC:A0:E3:49:3E:B1:34:53:A9:85:CE:51:9B:ED:87:5E:B8:F4:8E:3D:FA:20:51:B8:96:EE:DA:56:DC:2F:5C:62:79:15:23:E0:21:82:2B:2C'
            }
        ],
        'role' : 'auto'
    })
    sctpParameters: SctpParameters = SctpParameters(**{
        'port'           : 5000,
        'OS'             : 1024,
        'MIS'            : 1024,
        'maxMessageSize' : 2000000
    })
    
    return id, iceParameters, iceCandidates, dtlsParameters, sctpParameters