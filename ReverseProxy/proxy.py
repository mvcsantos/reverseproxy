import socket
import sys
import threading
import select
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

    def start(self):
        self.proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.proxy_socket.bind((self.HOST, self.PORT))
        self.proxy_socket.listen(5)

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

    # process the request's queue
    def process_requests(self):
        while True:
            conn = self.queue.get()

            request = conn.recv(1024).decode()

            if len(request) > 0:
                # check cache first
                response = self.get(request)
                with self.print_lock:
                    print('Response: \n', response, '\n\n')
                if response:
                    conn.send(response)

            else:
                with self.print_lock:
                    print('Not able to receive client data')
                    conn.close()
                #conn.send(b'Not able to receive client data')
            self.queue.task_done()

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



