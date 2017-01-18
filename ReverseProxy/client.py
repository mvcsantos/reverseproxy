# Echo client program
import socket
import sys

HOST = 'localhost'    # The remote host
PORT = 9001              # The same port as used by the server
RECV_BUFFER = 2048
s = None

for res in socket.getaddrinfo(HOST, PORT, socket.AF_UNSPEC, socket.SOCK_STREAM):
    af, socktype, proto, canonname, sa = res

    try:
        s = socket.socket(af, socktype, proto)
    except OSError as msg:
        s = None
        continue
    try:
        s.connect(sa)
    except OSError as msg:
        s.close()
        s = None
        continue
    break

if s is None:
    print('could not open socket')
    sys.exit(1)
with s:
    netbusHost = 'webservices.nextbus.com'
    path = "/service/publicXMLFeed?command=agencyList"
    request = "GET " + path + " HTTP/1.1\r\nHost: " + netbusHost + "\r\nAccept-Encoding: gzip, deflate\n\n"
    s.settimeout(1)
    s.sendall(request.encode())

    data = bytes()

    try:
        while True:
            incomingData = s.recv(RECV_BUFFER)

            if incomingData and len(incomingData) > 0:
                data += incomingData
            else:
                s.close()
                break

    except Exception as ex:
        s.close()


print('Received', repr(data))