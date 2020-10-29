from pymediasoup.rtp_parameters import RtpCapabilities


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