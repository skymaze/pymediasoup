import json
import time
import asyncio
import argparse
import secrets
from typing import Optional, Dict, Awaitable, Any, TypeVar, cast
from asyncio.futures import Future
from urllib.parse import urlsplit

import pymediasoup
from pymediasoup import Device
from pymediasoup import AiortcHandler
from pymediasoup.transport import Transport
from pymediasoup.consumer import Consumer
from pymediasoup.producer import Producer
from pymediasoup.data_consumer import DataConsumer
from pymediasoup.data_producer import DataProducer
from pymediasoup.sctp_parameters import SctpStreamParameters

# Import aiortc
from aiortc import VideoStreamTrack
from aiortc.mediastreams import AudioStreamTrack
from aiortc.contrib.media import MediaPlayer, MediaBlackhole, MediaRecorder

# Implement simple protoo client
import websockets
from websockets.typing import Subprotocol, Origin
from random import random

T = TypeVar("T")


class Demo:
    def __init__(
        self,
        uri,
        player=None,
        recorder: Optional[MediaRecorder | MediaBlackhole] = None,
    ):
        self._uri = uri
        self._player = player
        self._recorder = recorder if recorder is not None else MediaBlackhole()
        # Save answers temporarily
        self._answers: Dict[int, Future] = {}
        self._websocket = None
        self._device = None

        self._tracks = []

        if player and player.audio:
            audioTrack = player.audio
        else:
            audioTrack = AudioStreamTrack()
        if player and player.video:
            videoTrack = player.video
        else:
            videoTrack = VideoStreamTrack()

        self._videoTrack = videoTrack
        self._audioTrack = audioTrack

        self._tracks.append(videoTrack)
        self._tracks.append(audioTrack)

        self._sendTransport: Optional[Transport] = None
        self._recvTransport: Optional[Transport] = None
        self._chatDataProducer: Optional[DataProducer] = None

        self._producers = []
        self._consumers = []
        self._tasks = []
        self._closed = False

    @property
    def websocket(self) -> websockets.ClientConnection:
        if self._websocket is None:
            raise RuntimeError("WebSocket is not connected yet")
        return self._websocket

    @property
    def device(self) -> Device:
        if self._device is None:
            raise RuntimeError("Device is not loaded yet")
        return self._device

    @property
    def sendTransport(self) -> Transport:
        if self._sendTransport is None:
            raise RuntimeError("Send transport is not created yet")
        return self._sendTransport

    @property
    def recvTransport(self) -> Transport:
        if self._recvTransport is None:
            raise RuntimeError("Recv transport is not created yet")
        return self._recvTransport

    # websocket receive task
    async def recv_msg_task(self):
        while True:
            await asyncio.sleep(0.5)
            message = json.loads(await self.websocket.recv())
            if message.get("response"):
                if message.get("id") is not None:
                    answer = self._answers.get(message.get("id"))
                    if answer and not answer.done():
                        if message.get("ok", True):
                            answer.set_result(message)
                        else:
                            reason = (
                                message.get("errorReason")
                                or message.get("reason")
                                or message.get("error")
                                or "unknown server error"
                            )
                            answer.set_exception(RuntimeError(str(reason)))
            elif message.get("request"):
                if message.get("method") == "newConsumer":
                    consumer_id = message["data"].get("id") or message["data"].get(
                        "consumerId"
                    )
                    await self.consume(
                        id=consumer_id,
                        producerId=message["data"]["producerId"],
                        kind=message["data"]["kind"],
                        rtpParameters=message["data"]["rtpParameters"],
                    )
                    response = {
                        "response": True,
                        "id": message["id"],
                        "ok": True,
                        "data": {},
                    }
                    await self.websocket.send(json.dumps(response))
                elif message.get("method") == "newDataConsumer":
                    data_consumer_id = message["data"].get("id") or message["data"].get(
                        "dataConsumerId"
                    )
                    await self.consumeData(
                        id=data_consumer_id,
                        dataProducerId=message["data"]["dataProducerId"],
                        label=message["data"]["label"],
                        protocol=message["data"]["protocol"],
                        sctpStreamParameters=message["data"]["sctpStreamParameters"],
                    )
                    response = {
                        "response": True,
                        "id": message["id"],
                        "ok": True,
                        "data": {},
                    }
                    await self.websocket.send(json.dumps(response))
            elif message.get("notification"):
                print(message)

    # wait for answer ready
    async def _wait_for(
        self, fut: Awaitable[T], timeout: Optional[float], **kwargs: Any
    ) -> T:
        try:
            return await asyncio.wait_for(fut, timeout=timeout, **kwargs)
        except asyncio.TimeoutError:
            raise Exception("Operation timed out")

    async def _send_request(self, request):
        self._answers[request["id"]] = asyncio.get_running_loop().create_future()
        await self.websocket.send(json.dumps(request))

    def _require_data(self, response: dict, method: str) -> dict:
        data = response.get("data")
        if data is None:
            raise RuntimeError(f"{method} failed: {response}")
        return data

    # Generates a random positive integer.
    def generateRandomNumber(self) -> int:
        return round(random() * 10000000)

    async def run(self):
        parsed = urlsplit(self._uri)
        origin = cast(Origin, f"https://{parsed.hostname}") if parsed.hostname else None
        self._websocket = await websockets.connect(
            self._uri,
            subprotocols=[cast(Subprotocol, "protoo")],
            origin=origin,
        )
        task_run_recv_msg = asyncio.create_task(self.recv_msg_task())
        self._tasks.append(task_run_recv_msg)

        await self.load()
        await self.createSendTransport()
        await self.createRecvTransport()
        await self.produce()

        await task_run_recv_msg

    async def load(self):
        # Init device
        self._device = Device(
            handlerFactory=AiortcHandler.createFactory(tracks=self._tracks)
        )

        # Get Router RtpCapabilities
        reqId = self.generateRandomNumber()
        req = {
            "request": True,
            "id": reqId,
            "method": "getRouterRtpCapabilities",
            "data": {},
        }
        await self._send_request(req)
        ans = await self._wait_for(self._answers[reqId], timeout=15)

        # Load Router RtpCapabilities
        data = self._require_data(ans, "getRouterRtpCapabilities")
        await self.device.load(data.get("routerRtpCapabilities", data))

    async def createSendTransport(self):
        if self._sendTransport is not None:
            return
        # Send create sendTransport request
        reqId = self.generateRandomNumber()
        req = {
            "request": True,
            "id": reqId,
            "method": "createWebRtcTransport",
            "data": {
                "forceTcp": False,
                "producing": True,
                "consuming": False,
                "sctpCapabilities": self.device.sctpCapabilities.dict(),
                "appData": {"direction": "producer"},
            },
        }
        await self._send_request(req)
        ans = await self._wait_for(self._answers[reqId], timeout=15)
        data = self._require_data(ans, "createWebRtcTransport(send)")
        transport_id_raw = data.get("id") or data.get("transportId")
        if transport_id_raw is None:
            raise RuntimeError(
                "createWebRtcTransport(send) failed: missing transport id"
            )
        transport_id = str(transport_id_raw)

        # Create sendTransport
        self._sendTransport = self.device.createSendTransport(
            id=transport_id,
            iceParameters=data["iceParameters"],
            iceCandidates=data["iceCandidates"],
            dtlsParameters=data["dtlsParameters"],
            sctpParameters=data["sctpParameters"],
        )

        @self.sendTransport.on("connect")
        async def on_connect(dtlsParameters):
            reqId = self.generateRandomNumber()
            req = {
                "request": True,
                "id": reqId,
                "method": "connectWebRtcTransport",
                "data": {
                    "transportId": self.sendTransport.id,
                    "dtlsParameters": dtlsParameters.dict(exclude_none=True),
                },
            }
            await self._send_request(req)
            ans = await self._wait_for(self._answers[reqId], timeout=15)
            print(ans)

        @self.sendTransport.on("produce")
        async def on_produce(kind: str, rtpParameters, appData: dict):
            reqId = self.generateRandomNumber()
            req = {
                "id": reqId,
                "method": "produce",
                "request": True,
                "data": {
                    "transportId": self.sendTransport.id,
                    "kind": kind,
                    "rtpParameters": rtpParameters.dict(exclude_none=True),
                    "appData": appData,
                },
            }
            await self._send_request(req)
            ans = await self._wait_for(self._answers[reqId], timeout=15)
            data = self._require_data(ans, "produce")
            return data.get("id") or data.get("producerId")

        @self.sendTransport.on("producedata")
        async def on_producedata(
            sctpStreamParameters: SctpStreamParameters,
            label: str,
            protocol: str,
            appData: dict,
        ):

            reqId = self.generateRandomNumber()
            req = {
                "id": reqId,
                "method": "produceData",
                "request": True,
                "data": {
                    "transportId": self.sendTransport.id,
                    "label": label,
                    "protocol": protocol,
                    "sctpStreamParameters": sctpStreamParameters.dict(
                        exclude_none=True
                    ),
                    "appData": appData,
                },
            }
            await self._send_request(req)
            ans = await self._wait_for(self._answers[reqId], timeout=15)
            data = self._require_data(ans, "produceData")
            return data.get("id") or data.get("dataProducerId")

    async def produce(self):
        if self._sendTransport is None:
            await self.createSendTransport()

        # Join room
        reqId = self.generateRandomNumber()
        req = {
            "request": True,
            "id": reqId,
            "method": "join",
            "data": {
                "displayName": "pymediasoup",
                "device": {
                    "flag": "broadcaster",
                    "name": "pymediasoup",
                    "version": pymediasoup.__version__,
                },
                "rtpCapabilities": self.device.rtpCapabilities.dict(exclude_none=True),
                "sctpCapabilities": self.device.sctpCapabilities.dict(
                    exclude_none=True
                ),
            },
        }
        await self._send_request(req)
        ans = await self._wait_for(self._answers[reqId], timeout=15)
        print(ans)

        # produce
        videoProducer: Producer = await self.sendTransport.produce(
            track=self._videoTrack, stopTracks=False, appData={}
        )
        self._producers.append(videoProducer)
        audioProducer: Producer = await self.sendTransport.produce(
            track=self._audioTrack, stopTracks=False, appData={}
        )
        self._producers.append(audioProducer)

        # produce data
        await self.produceData()

    async def produceData(self):
        if self._sendTransport is None:
            await self.createSendTransport()

        dataProducer: DataProducer = await self.sendTransport.produceData(
            ordered=False,
            maxPacketLifeTime=5555,
            label="chat",
            protocol="",
            appData={"channel": "chat"},
        )
        self._chatDataProducer = dataProducer
        self._producers.append(dataProducer)
        task_run_data_send = asyncio.create_task(self._data_send_loop(dataProducer))
        self._tasks.append(task_run_data_send)

    async def _data_send_loop(self, dataProducer: DataProducer):
        while not self._closed and not dataProducer.closed:
            if dataProducer.readyState != "open":
                await asyncio.sleep(0.1)
                continue

            await asyncio.sleep(1)
            try:
                dataProducer.send(f"Hello at {time.time()}")
            except Exception as exc:
                print(f"DataProducer send failed: {exc}")
                break

    async def _send_reply_when_ready(self, reply: str, timeout: float = 10.0):
        waited = 0.0
        interval = 0.1

        while not self._closed and waited < timeout:
            producer = self._chatDataProducer
            if producer and not producer.closed and producer.readyState == "open":
                producer.send(reply)
                return
            await asyncio.sleep(interval)
            waited += interval

        print(f"DataProducer not ready after {timeout}s, skip reply: {reply}")

    async def createRecvTransport(self):
        if self._recvTransport is not None:
            return
        # Send create recvTransport request
        reqId = self.generateRandomNumber()
        req = {
            "request": True,
            "id": reqId,
            "method": "createWebRtcTransport",
            "data": {
                "forceTcp": False,
                "producing": False,
                "consuming": True,
                "sctpCapabilities": self.device.sctpCapabilities.dict(),
                "appData": {"direction": "consumer"},
            },
        }
        await self._send_request(req)
        ans = await self._wait_for(self._answers[reqId], timeout=15)
        data = self._require_data(ans, "createWebRtcTransport(recv)")
        transport_id_raw = data.get("id") or data.get("transportId")
        if transport_id_raw is None:
            raise RuntimeError(
                "createWebRtcTransport(recv) failed: missing transport id"
            )
        transport_id = str(transport_id_raw)

        # Create recvTransport
        self._recvTransport = self.device.createRecvTransport(
            id=transport_id,
            iceParameters=data["iceParameters"],
            iceCandidates=data["iceCandidates"],
            dtlsParameters=data["dtlsParameters"],
            sctpParameters=data["sctpParameters"],
        )

        @self.recvTransport.on("connect")
        async def on_connect(dtlsParameters):
            reqId = self.generateRandomNumber()
            req = {
                "request": True,
                "id": reqId,
                "method": "connectWebRtcTransport",
                "data": {
                    "transportId": self.recvTransport.id,
                    "dtlsParameters": dtlsParameters.dict(exclude_none=True),
                },
            }
            await self._send_request(req)
            ans = await self._wait_for(self._answers[reqId], timeout=15)
            print(ans)

    async def consume(self, id, producerId, kind, rtpParameters):
        if self._recvTransport is None:
            await self.createRecvTransport()
        consumer: Consumer = await self.recvTransport.consume(
            id=id, producerId=producerId, kind=kind, rtpParameters=rtpParameters
        )
        self._consumers.append(consumer)
        track = consumer.track
        if track is None:
            raise RuntimeError("Received consumer without a media track")
        self._recorder.addTrack(track)
        await self._recorder.start()

    async def consumeData(
        self,
        id,
        dataProducerId,
        sctpStreamParameters,
        label=None,
        protocol=None,
        appData=None,
    ):
        if appData is None:
            appData = {}

        dataConsumer: DataConsumer = await self.recvTransport.consumeData(
            id=id,
            dataProducerId=dataProducerId,
            sctpStreamParameters=sctpStreamParameters,
            label=label,
            protocol=protocol,
            appData=appData,
        )
        self._consumers.append(dataConsumer)

        @dataConsumer.on("message")
        def on_message(message):
            if isinstance(message, bytes):
                text = message.decode("utf-8", errors="replace")
            else:
                text = str(message)

            print(f"DataChannel {label}-{protocol}: {text}")

            reply = f"received {text}"
            task_send_reply = asyncio.create_task(self._send_reply_when_ready(reply))
            self._tasks.append(task_send_reply)

    async def close(self):
        for consumer in self._consumers:
            await consumer.close()
        for producer in self._producers:
            await producer.close()
        for task in self._tasks:
            task.cancel()
        if self._sendTransport:
            await self.sendTransport.close()
        if self._recvTransport:
            await self.recvTransport.close()
        await self._recorder.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PyMediaSoup")
    parser.add_argument("room", nargs="?")
    parser.add_argument("--play-from", help="Read the media from a file and sent it.")
    parser.add_argument("--record-to", help="Write received media to a file.")
    args = parser.parse_args()

    if not args.room:
        args.room = secrets.token_urlsafe(8).lower()
    peerId = secrets.token_urlsafe(8).lower()

    uri = f"wss://v3demo.mediasoup.org:4443/?roomId={args.room}&peerId={peerId}"

    if args.play_from:
        player = MediaPlayer(args.play_from)
    else:
        player = None

    # create media sink
    if args.record_to:
        recorder = MediaRecorder(args.record_to)
    else:
        recorder = MediaBlackhole()

    async def main():
        demo = Demo(uri=uri, player=player, recorder=recorder)
        try:
            await demo.run()
        except websockets.exceptions.InvalidStatus as exc:
            status_code = getattr(exc, "status_code", None)
            if status_code is None:
                response = getattr(exc, "response", None)
                status_code = getattr(response, "status_code", None) or getattr(
                    response, "status", None
                )
            status_label = (
                f"HTTP {status_code}" if status_code is not None else "unknown status"
            )
            raise RuntimeError(
                f"WebSocket handshake rejected ({status_label}). Please make sure the roomId is valid, "
                "the v3demo room page is open in your browser, and the connection includes the correct Origin."
            ) from exc
        except websockets.exceptions.WebSocketException as exc:
            raise RuntimeError(f"WebSocket error: {exc}") from exc
        finally:
            await demo.close()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
