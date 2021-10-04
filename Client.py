# -*- coding: utf-8 -*-
"""
Created on Sat Oct  2 15:17:41 2021

@author: Wei Jie
"""

import socket

serverAddressPort = ("127.0.0.1", 20001)
bufferSize = 1024

msgFromClient = "Connecting with server"
bytesToSend = str.encode(msgFromClient)

# Create a UDP socket at client side

UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Send to server using created UDP socket

UDPClientSocket.sendto(bytesToSend, serverAddressPort)

msgFromServer = UDPClientSocket.recvfrom(bufferSize)

msg = f"Message from server: {msgFromServer[0]}"

print(msg)
