import socket
import sys
import threading
from queue import Queue


# Notes: python 3.6 socket seems to be synchronous
# so there is a need to implement multithreading to improve performance
# and allow the proxy to scale


# GET /pageyouwant.html HTTP/1.1[CRLF]
# Host: google.com[CRLF]
# Connection: close[CRLF]
# User-Agent: MyAwesomeUserAgent/1.0.0[CRLF]
# Accept-Encoding: gzip[CRLF]
# Accept-Charset: ISO-8859-1,UTF-8;q=0.7,*;q=0.7[CRLF]
# Cache-Control: no-cache[CRLF]
# [CRLF]

class ReverseProxyServer:

    NETBUS_DOMAIN = 'webservices.nextbus.com'
    NETBUS_PORT = 80
    proxy_socket = ''
    threads = []

    def __init__(self, host = None, port = 9000):
        # proxy info
        self.HOST = host
        self.PORT = port

        # number of threads
        self.num_threads = 2
        self.print_lock = threading.Lock()

        # feed buffer response
        self.buffer_size = 4096

        # store incoming requests
        self.queue = Queue()

        # initialize threads
        for i in range(self.num_threads):
            thread = threading.Thread(target=self.process_requests)
            thread.daemon = True
            thread.start()
            self.threads.append(thread)

        # start receiving connections
        #proxy_thread = threading.Thread(target=self.initProxy)
        #proxy_thread.daemon = True
        #proxy_thread.start()
        self.initProxy()

    # initialize the proxy to receive connections
    # using TCP/IP protocol
    def handle(self):
        for res in socket.getaddrinfo(self.HOST, self.PORT, socket.AF_UNSPEC,
                                      socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                self.proxy_socket = socket.socket(af, socktype, proto)
            except OSError as msg:
                self.proxy_socket = None
                continue
            try:
                self.proxy_socket.bind(sa)
                self.proxy_socket.listen(1)
            except OSError as msg:
                self.proxy_socket.close()
                self.proxy_socket = None
                continue
            break
        if self.proxy_socket is None:
            print('could not open socket')
            sys.exit(1)
        conn, addr = self.proxy_socket.accept()
        with conn:
            print('Connected by', addr)
            while True:
                data = conn.recv(1024)
                if not data: break
                conn.send(data)

    # process the request's queue
    def process_requests(self):
        while True:
            request = self.queue.get()
            # check cache first
            response = self.get(request)
            with self.print_lock:
                print('Response: \n', response, '\n\n')
            self.queue.task_done()

    def request_data(self, request):
        self.get(request)

    # request data from the NextBus API
    def get(self, request):
        with self.print_lock:
            print('Thread (',threading.current_thread().name,'): ', request)
        info = socket.getaddrinfo(self.NETBUS_DOMAIN, self.NETBUS_PORT, socket.AF_UNSPEC, socket.SOCK_STREAM)

        with self.print_lock:
            print('Address info: ', info)
        for res in info:
            af, socktype, proto, canonname, sa = res
            with socket.socket(af, socktype, proto) as proxySocket:
                try:
                    server_ip = socket.gethostbyname(self.NETBUS_DOMAIN)
                    print('Server IP: ', server_ip, '\n\n')

                    print('Connecting to ', self.NETBUS_DOMAIN, ' on port ', self.NETBUS_PORT)
                    proxySocket.connect((self.NETBUS_DOMAIN, self.NETBUS_PORT))
                    print('Connected to ', self.NETBUS_DOMAIN)
                    proxySocket.send(request.encode())
                    result = proxySocket.recv(self.buffer_size)

                    print(result)
                    return result
                except:
                    print('Port ', self.NETBUS_PORT, ' is closed!')
                    return



