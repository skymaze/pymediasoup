import logging
from typing import Optional, Literal, List, Any, Callable, Dict
from pyee import AsyncIOEventEmitter
from aiortc import RTCIceServer
from .ortc import canReceive, generateProbatorRtpParameters, ExtendedRtpCapabilities
from .errors import InvalidStateError, UnsupportedError
from .emitter import EnhancedEventEmitter
from .handlers.handler_interface import HandlerInterface
from .models.handler_interface import HandlerRunOptions, HandlerReceiveOptions, HandlerSendOptions, HandlerSendResult, HandlerReceiveResult, SctpStreamParameters, HandlerSendDataChannelResult, HandlerReceiveDataChannelOptions, HandlerReceiveDataChannelResult
from .models.transport import ConnectionState, IceParameters, InternalTransportOptions, DtlsParameters
from .consumer import Consumer, ConsumerOptions
from .producer import Producer, ProducerOptions
from .data_consumer import DataConsumer, DataConsumerOptions
from .data_producer import DataProducer, DataProducerOptions


class Transport(EnhancedEventEmitter):
    # Closed flag.
    _closed: bool = False
    # Whether we can produce audio/video based on computed extended RTP
    # capabilities.
    _canProduceByKind: Dict[str, bool]
    # App custom data.
    _appData: Optional[dict]
    # Transport connection state.
    _connectionState: ConnectionState = 'new'
    # Producers indexed by id
    _producers: Dict[str, Producer] = {}
    # Consumers indexed by id.
    _consumers: Dict[str, Consumer] = {}
    # DataProducers indexed by id
    _dataProducers: Dict[str, DataProducer] = {}
    # DataConsumers indexed by id.
    _dataConsumers: Dict[str, DataConsumer] = {}
    # Whether the Consumer for RTP probation has been created.
    _probatorConsumerCreated: bool = False
    # Observer instance.
    _observer: AsyncIOEventEmitter = AsyncIOEventEmitter()

    def __init__(
        self,
        options: InternalTransportOptions,
        loop=None
    ):
        super(Transport, self).__init__(loop=loop)

        logging.debug(f'constructor() [id:{options.id}, direction:{options.direction}]')
        # Id.
        self._id: str = options.id
        # Direction.
        self._direction: Literal['send', 'recv'] = options.direction
        # Extended RTP capabilities.
        self._extendedRtpCapabilities: ExtendedRtpCapabilities = options.extendedRtpCapabilities,
        self._canProduceByKind: Dict[str, bool] = options.canProduceByKind
        self._maxSctpMessageSize = options.sctpParameters.maxMessageSize if options.sctpParameters else None

        if options.additionalSettings:
            additionalSettings = options.additionalSettings.copy()
            del additionalSettings['iceServers']
            del additionalSettings['iceTransportPolicy']
            del additionalSettings['bundlePolicy']
            del additionalSettings['rtcpMuxPolicy']
            del additionalSettings['sdpSemantics']
        else:
            additionalSettings = None

        self._handler: HandlerInterface = options.handlerFactory()

        handlerRunOptions: HandlerRunOptions = HandlerRunOptions(
            direction=options.direction,
            iceParameters=options.iceParameters,
            iceCandidates=options.iceCandidates,
            dtlsParameters=options.dtlsParameters,
            sctpParameters=options.sctpParameters,
            iceServers=options.iceServers,
            iceTransportPolicy=options.iceTransportPolicy,
            additionalSettings=additionalSettings,
            proprietaryConstraints=options.proprietaryConstraints,
            extendedRtpCapabilities=options.extendedRtpCapabilities
        )

        self._handler.run(options=handlerRunOptions)

        self._appData = options.appData

        self._handleHandler()
    
    # Producer id.
    @property
    def id(self) -> str:
        return self._id
    
    # Whether the Producer is closed.
    @property
    def closed(self) -> bool:
        return self._closed
    
    # Transport direction.
    @property
    def direction(self) -> Literal['send', 'recv']:
        return self._direction
    
    # RTC handler instance.
    @property
    def handler(self) -> HandlerInterface:
        return self._handler
    
    # Connection state.
    @property
    def connectionState(self) -> ConnectionState:
        return self._connectionState
    
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
    # @emits newproducer - (producer: Producer)
    # @emits newconsumer - (producer: Producer)
    # @emits newdataproducer - (dataProducer: DataProducer)
    # @emits newdataconsumer - (dataProducer: DataProducer)
    @property
    def observer(self) -> AsyncIOEventEmitter:
        return self._observer

    # Close the Transport.
    def close(self):
        if self._closed:
            return
        
        logging.debug('Transport close()')

        self._closed = True

        # Close the handler.
        self._handler.close()

        # Close all Process.
        for process_dict in [self._producers, self._consumers, self._dataProducers, self._dataConsumers]:
            for process in process_dict.values():
                process.transportClosed()
            process_dict.clear()
        
        self._observer.emit('close')
    
    # Get associated Transport (RTCPeerConnection) stats.
    #
    # @returns {RTCStatsReport}
    async def getStats(self):
        if self._closed:
            raise InvalidStateError('closed')

        return await self._handler.getTransportStats()

    # Restart ICE connection.
    async def restartIce(self, iceParameters: IceParameters):
        if self._closed:
            raise InvalidStateError('closed')
        
        return await self._handler.restartIce(iceParameters)
    
    # Update ICE servers.
    async def updateIceServers(self, iceServers: List[RTCIceServer]):
        if self._closed:
            raise InvalidStateError('closed')

        return await self._handler.updateIceServers(iceServers)
    
    # Create a Producer.
    async def produce(self, options: ProducerOptions) -> Producer:
        logging.debug(f'Transport produce() [track:{options.track}]')
        if not options.track:
            raise TypeError('missing track')
        elif self._direction != 'send':
            raise UnsupportedError('not a sending Transport')
        elif not self._canProduceByKind.get(options.track.kind):
            raise UnsupportedError(f'cannot produce {options.track.kind}')
        elif options.track.readyState == 'ended':
            raise InvalidStateError('track ended')
        elif len(self.listeners('connect')) == 0 and self._connectionState == 'new':
            raise TypeError('no "connect" listener set into this transport')
        elif len(self.listeners('connect')) == 0:
            raise TypeError('no "produce" listener set into this transport')
        
        # NOTE: Mediasoup client enqueue command here.
        handlerSendOptions: HandlerSendOptions = HandlerSendOptions(
            track=options.track,
            encodings=options.encodings,
            codecOptions=options.codecOptions,
            codec=options.codec
        )
        handlerSendResult: HandlerSendResult = await self._handler.send(handlerSendOptions)

        ids = await self.emit_for_results(
            'produce',
            {
                'kind': options.track.kind,
                'rtpParameters': handlerSendResult.rtpParameters,
                'appData': options.appData
            }
        )

        producer = Producer(
            id=ids[0],
            localId=handlerSendResult.localId,
            rtpSender=handlerSendResult.rtpSender,
            track=options.track,
            rtpParameters=handlerSendResult.rtpParameters,
            stopTracks=options.stopTracks,
            disableTrackOnPause=options.disableTrackOnPause,
            zeroRtpOnPause=options.zeroRtpOnPause,
            appData=options.appData
        )

        self._producers[producer.id] = producer
        self._handleProducer(producer)

        # Emit observer event.
        self._observer.emit('newproducer', producer)

        return producer
    
        # TODO: stop the given track if the command above failed due to closed Transport.
    
    async def consume(self, options: ConsumerOptions) -> Consumer:
        logging.debug('Transport consume()')
        if self._closed:
            raise InvalidStateError('closed')
        elif self._direction != 'recv':
            raise UnsupportedError('not a receiving Transport')
        elif len(self.listeners('connect')) == 0 and self._connectionState == 'new':
            raise TypeError('no "connect" listener set into this transport')

        # NOTE: Mediasoup client enqueue command here.
        if not canReceive(rtpParameters=options.rtpParameters, extendedRtpCapabilities=self._extendedRtpCapabilities):
            raise UnsupportedError('cannot consume this Producer')

        handlerReceiveOptions: HandlerReceiveOptions = HandlerReceiveOptions(trackId=options.id, kind=options.kind, rtpParameters=options.rtpParameters)
        handlerReceiveResult: HandlerReceiveResult = await self._handler.receive(handlerReceiveOptions)

        consumer: Consumer = Consumer(
            id=options.id,
            localId=handlerReceiveResult.localId,
            producerId=options.producerId,
            track=handlerReceiveResult.track,
            rtpParameters=options.rtpParameters,
            appData=options.appData
        )

        self._consumers[consumer.id] = consumer
        self._handleConsumer(consumer)

        # If this is the first video Consumer and the Consumer for RTP probation
        # has not yet been created, create it now.
        if not self._probatorConsumerCreated and options.kind == 'video':
            probatorRtpParameters = generateProbatorRtpParameters(consumer.rtpParameters)
            await self._handler.receive(
                HandlerReceiveOptions(
                    trackId='probator',
                    kind='video',
                    rtpParameters=probatorRtpParameters
                )
            )

            logging.debug('Transport consume() | Consumer for RTP probation created')

            self._probatorConsumerCreated = True
        
        self._observer.emit('newconsumer', consumer)

        return consumer
    
    # Create a DataProducer
    async def produceData(self, options: DataProducerOptions) -> DataProducer:
        logging.debug('Transport produceData()')
        if self._direction != 'send':
            raise UnsupportedError('not a sending Transport')

        elif not self._maxSctpMessageSize:
            raise UnsupportedError('SCTP not enabled by remote Transport')

        elif len(self.listeners('connect')) == 0 and self._connectionState == 'new':
            raise TypeError('no "connect" listener set into this transport')

        elif len(self.listeners('connect')) == 0:
            raise TypeError('no "produce" listener set into this transport')

        if options.maxPacketLifeTime or options.maxRetransmits:
            options.ordered = False
        
        # NOTE: Mediasoup client enqueue command here.
        SctpStreamParameters: SctpStreamParameters = SctpStreamParameters(
            ordered=options.ordered,
            maxPacketLifeTime=options.maxPacketLifeTime,
            maxRetransmits=options.maxRetransmits,
            priority=options.priority,
            label=options.label,
            protocol=options.protocol
        )
        handlerSendDataChannelResult: HandlerSendDataChannelResult = await self._handler.sendDataChannel(SctpStreamParameters)

        ids = await self.emit_for_results(
            'producedata',
            {
                'sctpStreamParameters': handlerSendDataChannelResult.sctpStreamParameters,
                'label': options.label,
                'protocal': options.protocol,
                'appData': options.appData
            }
        )

        dataProducer = DataProducer(
            id=ids[0],
            dataChannel=handlerSendDataChannelResult.dataChannel,
            sctpStreamParameters=handlerSendDataChannelResult.sctpStreamParameters,
            appData=options.appData
        )

        self._dataProducers[dataProducer.id] = dataProducer
        self._handleDataProducer(dataProducer)

        # Emit observer event.
        self._observer.emit('newdataproducer', dataProducer)

        return dataProducer

    # Create a DataConsumer
    async def consumeData(self, options: DataConsumerOptions) -> DataConsumer:
        logging.debug('Transport consumeData()')
        if self._closed:
            raise InvalidStateError('closed')
        elif self._direction != 'recv':
            raise UnsupportedError('not a receiving Transport')
        elif len(self.listeners('connect')) == 0 and self._connectionState == 'new':
            raise TypeError('no "connect" listener set into this transport')
        
        # NOTE: Mediasoup client enqueue command here.
        handlerReceiveDataChannelOptions: HandlerReceiveDataChannelOptions = HandlerReceiveDataChannelOptions(
            sctpStreamParameters=options.sctpStreamParameters,
            label=options.label,
            protocol=options.protocol
        )
        handlerReceiveDataChannelResult: HandlerReceiveDataChannelResult = await self._handler.receiveDataChannel(handlerReceiveDataChannelOptions)

        dataConsumer: DataConsumer = DataConsumer(
            id=options.id,
            dataProducerId=options.dataProducerId,
            dataChannel=handlerReceiveDataChannelResult.dataChannel,
            sctpStreamParameters=options.sctpStreamParameters,
            appData=options.appData
        )

        self._dataConsumers[dataConsumer.id] = dataConsumer
        self._handleDataConsumer(dataConsumer)

        # Emit observer event.
        self._observer.emit('newdataconsumer', dataConsumer)

        return dataConsumer

    def _handleHandler(self):
        handler = self._handler

        @handler.on('@connect')
        async def on_connect(dtlsParameters: DtlsParameters):
            if self._closed:
                raise InvalidStateError('closed')
            else:
                self.emit('connect', dtlsParameters)

        @handler.on('@connectionstatechange')
        def on_connectionstatechange(connectionState: ConnectionState):
            self._connectionState = connectionState
            if not self._closed:
                self.emit('connectionstatechange', connectionState)
    
    def _handleProducer(self, producer: Producer):
        @producer.on('@close')
        async def on_close():
            del self._producers[producer.id]
            if self._closed:
                return
            await self._handler.stopSending(producer.localId)
        
        @producer.on('@replacetrack')
        async def on_replacetrack(track):
            await self._handler.replaceTrack(producer.localId, track)
        
        @producer.on('@setmaxspatiallayer')
        async def on_setmaxspatiallayer(spatialLayer):
            await self._handler.setMaxSpatialLayer(producer.localId, spatialLayer)
        
        @producer.on('@setrtpencodingparameters')
        async def on_setrtpencodingparameters(params):
            await self._handler.setRtpEncodingParameters(producer.localId, params)
        
        @producer.on('@getstats')
        async def on_getstats():
            if self._closed:
                return InvalidStateError('closed')
            return await self._handler.getSenderStats(producer.localId)
    
    def _handleConsumer(self, consumer: Consumer):
        @consumer.on('@close')
        async def on_close():
            del self._consumers[consumer.id]
            if self._closed:
                return
            await self._handler.stopReceiving(consumer.localId)

        @consumer.on('@getstats')
        async def on_getstats():
            if self._closed:
                return InvalidStateError('closed')
            return await self._handler.getReceiverStats(consumer.localId)
        
    def _handleDataProducer(self, dataProducer: DataProducer):
        @dataProducer.on('@close')
        def on_close():
            del self._dataProducers[dataProducer.id]
        
    def _handleDataConsumer(self, dataConsumer: DataConsumer):
        @dataConsumer.on('@close')
        def on_close():
            del self._dataConsumers[dataConsumer.id]