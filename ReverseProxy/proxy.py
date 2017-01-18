import socket
import sys
import threading
import select
import asyncio
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

    def __init__(self, host = None, port = 9001):
        # proxy info
        self.HOST = host
        self.PORT = port

        # number of threads to handle request to the Nextbus
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

        self.initializeServerSocket()

        #listenRequestsThread = threading.Thread(target=self.startListening)
        #listenRequestsThread.daemon = True
        #listenRequestsThread.start()
        #self.threads.append(listenRequestsThread)

        # start receiving connections
        #loop = asyncio.get_event_loop()
        #listening = self.startListening()
        #loop.run_until_complete(listening)

        self.initServer()

    # initialize the proxy to receive connections
    # using TCP/IP protocol
    def initializeServerSocket(self):
        for res in socket.getaddrinfo(self.HOST, self.PORT, socket.AF_UNSPEC,
                                      socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                self.proxy_socket = socket.socket(af, socktype, proto)
                self.proxy_socket.setblocking(False)
            except OSError as msg:
                self.proxy_socket = None
                continue
            try:
                self.proxy_socket.bind(sa)
                self.proxy_socket.listen(5)
            except OSError as msg:
                self.proxy_socket.close()
                self.proxy_socket = None
                continue
            break
        if self.proxy_socket is None:
            print('could not open socket')
            sys.exit(1)

            '''
            # Sockets from which we expect to read
            inputs = [self.proxy_socket]
            # Sockets to which we expect to write
            outputs = []
            # Outgoing message queues (socket:Queue)
            message_queues = {}
            self.communication_channels = [inputs, outputs, message_queues]
        '''

    def initServer(self):
        self.proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.proxy_socket.bind((self.HOST, self.PORT))
        self.proxy_socket.listen(10)

        kqueue = select.kqueue()
        kevent = select.kevent(self.proxy_socket.fileno(),
                               filter=select.KQ_FILTER_READ,
                               flags=select.KQ_EV_ADD | select.KQ_EV_ENABLE)

        while True:
            revents = kqueue.control([kevent], 1, None)
            for event in revents:
                # If the kernel notifies us saying there is a read event available
                # on the master fd(s.fileno()), we accept() the
                # connection so that we can recv()/send() on the the accept()ed
                # socket
                if (event.filter == select.KQ_FILTER_READ):
                    conn, _ = self.proxy_socket.accept()
                    self.queue.put(conn)

    # deprecated
    def startListening2(self):
        while True:
            print('Wainting for connections:')
            conn, addr = self.proxy_socket.accept()
            with conn:
                print('Connected by', addr)
                self.clientHandler(conn, addr)

    def clientHandler(self, conn, addr):
        self.queue.put(conn)

    # process the request's queue
    def process_requests(self):
        while True:
            conn = self.queue.get()

            request = ""
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                request = data

            if len(request) > 0:
                # check cache first
                response = self.get(request)
                with self.print_lock:
                    print('Response: \n', response, '\n\n')
                conn.send(request.encode())

            else:
                with self.print_lock:
                    print('Not able to receive client data')
                    conn.close()
                #conn.send(b'Not able to receive client data')
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



