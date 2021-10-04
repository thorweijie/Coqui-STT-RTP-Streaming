# -*- coding: utf-8 -*-
"""
Created on Sat Oct  2 15:17:41 2021

@author: Wei Jie
"""

import collections
import logging
import numpy as np
import os
import queue
from rtp import RTP
import socket
import stt
import webrtcvad

localIP = "127.0.0.1"
localPort = 20001
bufferSize = 4096
sampleRate = 16000
bufferQueue = queue.Queue()

msgFromServer = ""
def bytesToSend (msgFromServer):
    return str.encode(msgFromServer)

# Create a datagram socket

UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Bind to address and IP

UDPServerSocket.bind((localIP, localPort))
print("UDP server up and running")

# Generate directories for model and scorer files

cwd = (os.getcwd())
modelDir = os.path.join(cwd, "coqui-stt-0.9.3-models.tflite")
scorerDir = os.path.join(cwd, "coqui-stt-0.9.3-models.scorer")

# Start CoquiSTT

print('Initializing model...')
logging.info("Model: %s", modelDir)
model = stt.Model(modelDir)
logging.info("Scorer: %s", scorerDir)
model.enableExternalScorer(scorerDir)
stream_context = model.createStream()

# Listen for incoming datagrams 

while(True):
    byteAddressPair = UDPServerSocket.recvfrom(bufferSize)
    message = byteAddressPair[0]
    address = byteAddressPair[1]
    clientMsg = f"Message from client: {message}"
    clientIP = f"Client IP address: {address}"
    print(clientMsg)
    print(clientIP)
    
    # Sends acknowledgemnt if voice gateway attempts to communicate with server
    
    if message.decode() == "Connecting with server":
        msgFromServer = "Received communication from voice gateway"
        UDPServerSocket.sendto(bytesToSend(msgFromServer), address)
    else: 
        # Decode RTP packet and get payload
        
        decodedPayload = RTP().fromBytes(message).payload
        
        # Append payload to buffer
        
        bufferQueue.put(decodedPayload)
             
        # Create VAD object with aggressiveness set to 3 (most aggressive)
        
        vad = webrtcvad.Vad(3)
        
        # Run payload through VAD, only stream payload with voice to CoquiSTT  
        
        def frame_generator():
            """Generator that yields all audio frames from payload."""
            while True:
                yield bufferQueue.get()
        
        def vad_collector(padding_ms=300, ratio=0.75, frame_duration_ms = 20, frames = None):
            """Generator that yields series of consecutive audio frames comprising each utterence, separated by yielding a single None.
            Determines voice activity by ratio of frames in padding_ms. Uses a buffer to include padding_ms prior to being triggered.
            Example: (frame, ..., frame, None, frame, ..., frame, None, ...)
                      |---utterence---|        |---utterence---|
            """
            if frames is None: frames = frame_generator()
            num_padding_frames = padding_ms // frame_duration_ms
            ring_buffer = collections.deque(maxlen=num_padding_frames)
            triggered = False
    
            for frame in frames:
                if len(frame) < 640:
                    return
    
                is_speech = vad.is_speech(frame, sampleRate)
    
                if not triggered:
                    ring_buffer.append((frame, is_speech))
                    num_voiced = len([f for f, speech in ring_buffer if speech])
                    if num_voiced > ratio * ring_buffer.maxlen:
                        triggered = True
                        for f, s in ring_buffer:
                            yield f
                        ring_buffer.clear()
    
                else:
                    yield frame
                    ring_buffer.append((frame, is_speech))
                    num_unvoiced = len([f for f, speech in ring_buffer if not speech])
                    if num_unvoiced > ratio * ring_buffer.maxlen:
                        triggered = False
                        yield None
                        ring_buffer.clear()
        
        # Stream frames with voice to CoquiSTT
        
        frames = vad_collector()
        for frame in frames:
            if frame is not None:
                logging.debug("streaming frame")
                stream_context.feedAudioContent(np.frombuffer(frame, np.int16))
        else:
            logging.debug("end utterence")
            text = stream_context.finishStream()
            print("Recognized: %s" % text)
            stream_context = model.createStream()                
        
