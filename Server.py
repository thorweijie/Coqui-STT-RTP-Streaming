# -*- coding: utf-8 -*-
"""
Created on Sat Oct  2 15:17:41 2021

@author: Wei Jie
"""

import socket

localIP = "127.0.0.1"
localPort = 20001
bufferSize = 1024

msgFromServer = "Hello UDP Client"
bytesToSend = str.encode(msgFromServer)

# Create a datagram socket

UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Bind to address and IP

UDPServerSocket.bind((localIP, localPort))

print("UDP server up and running")

# Listen for incoming datagrams

while(True):
    byteAddressPair = UDPServerSocket.recvfrom(bufferSize)
    message = byteAddressPair[0]
    address = byteAddressPair[1]
    clientMsg = f"Message from client: {message}"
    clientIP = f"Client IP address: {address}"
    print(clientMsg)
    print(clientIP)
    
    # Sending a reply to a client
    
    UDPServerSocket.sendto(bytesToSend, address)


