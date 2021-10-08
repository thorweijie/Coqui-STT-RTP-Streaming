# -*- coding: utf-8 -*-
"""
Created on Sat Oct  2 15:17:41 2021

@author: Wei Jie
"""

import asyncio
from asyncio.tasks import create_task
import collections
from datetime import datetime
import numpy as np
import os
import queue
from numpy.lib.function_base import append
from rtp import RTP
import stt
import wave
import webrtcvad

localIP = "127.0.0.1"
localPort = 5004
bufferSize = 4096
sampleRate = 16000
padding = 300
ratio = 0.75
frameDuration = 20

class RtpServerProtocol:
    """Protocol to process received RTP packets"""

    def __init__(self, model) -> None:
        numPaddingFrames = padding // frameDuration
        self.ringBuffer = collections.deque(maxlen=numPaddingFrames)
        self.unDecodedBufferQueue = queue.Queue()
        self.triggered = False
        self.voicedFrames = []
        self.model = model

        # Create VAD object with aggressiveness set to 3 (most aggressive)
        self.vad = webrtcvad.Vad(3)
    
    def connection_made(self, transport):
        self.transport = transport

    # Stream frames with voice to CoquiSTT
    def transcribeAudio(self, frames):
        stream_context = self.model.createStream()
        print("streaming frame")
        for frame in frames:
            stream_context.feedAudioContent(np.frombuffer(frame, np.int16))
        print("end utterence")
        text = stream_context.finishStream()
        print("Recognized:", text)

    def datagram_received(self, data, addr):

        # Decode RTP packet and get payload
        decodedPayload = RTP().fromBytes(data).payload

        is_speech = self.vad.is_speech(decodedPayload, sampleRate)

        if not self.triggered:
            self.ringBuffer.append((decodedPayload, is_speech))
            num_voiced = len([f for f, speech in self.ringBuffer if speech])
            if num_voiced > ratio * self.ringBuffer.maxlen:
                self.triggered = True
                for f, s in self.ringBuffer:
                    self.voicedFrames.append(f)
                self.ringBuffer.clear()
        else:
            self.voicedFrames.append(decodedPayload)
            self.ringBuffer.append((decodedPayload, is_speech))
            num_unvoiced = len([f for f, speech in self.ringBuffer if not speech])
            if num_unvoiced > ratio * self.ringBuffer.maxlen:
                self.triggered = False
                self.ringBuffer.clear()
                self.transcribeAudio(self.voicedFrames)
                self.voicedFrames.clear()

async def main():

    # Generate directories for model and scorer files
    loop = asyncio.get_running_loop()
    cwd = (os.getcwd())
    modelDir = os.path.join(cwd, "coqui-stt-0.9.3-models.tflite")
    scorerDir = os.path.join(cwd, "coqui-stt-0.9.3-models.scorer")

    # Start CoquiSTT
    print('Initializing model...')
    print("Model: ", modelDir)
    model = stt.Model(modelDir)
    print("Scorer: ", scorerDir)
    model.enableExternalScorer(scorerDir)
    
    # Create a datagram socket, listen for incoming datagrams and put in buffer
    print("UDP server up and running")
    print("Server listening on port", localPort)
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: RtpServerProtocol(model),
        local_addr=(localIP, localPort))

    try:
        await asyncio.sleep(3600)  # Serve for 1 hour.
    finally:
        transport.close()

asyncio.get_event_loop().run_until_complete(main())