import socket
import threading
import select
import time
from stats import Stats

from queue import Queue

'''
    Reverse proxy implementation using KQueue and multithreading
    Each request is processed by a different thread (Daemon)

    Note: KQueue is only supported by MacOS and FreeBSD

'''
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
        self.num_threads = 10
        self.print_lock = threading.Lock()

        # feed buffer response
        self.BUFFSIZE = 32384

        # store incoming requests
        self.queue = Queue()

        # start statistics socket
        self.stats = Stats('', 9012)
        self.stats.start()

        # initialize threads
        for i in range(self.num_threads):
            thread = threading.Thread(target=self.process_requests)
            thread.daemon = True
            thread.start()
            self.threads.append(thread)

    '''
        Starts the proxy to receive connections
    '''
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
            print('Wainting for connections: ')
            revents = kqueue.control([kevent], 1, None)
            for event in revents:
                # If the kernel notifies us saying there is a read event available
                # on the master fd(proxy_socket.fileno()), we accept() the
                # connection so that we can recv()/send() on the the accept()ed
                # socket
                if (event.filter == select.KQ_FILTER_READ):
                    conn, addr = self.proxy_socket.accept()
                    print('Connected to : ', addr, ' (client)')
                    self.queue.put(conn)
                    #conn.shutdown(socket.SHUT_WR)
                    #conn.close()
            time.sleep(0.05)

        kqueue.close()
        self.queue.join()

    '''
        Threaded request processing
        Process the request's from the queue
        Process the request in a different thread while
        the main thread is waiting for new requests
    '''
    def process_requests(self):

        while True:
            conn = self.queue.get()
            request = conn.recv(1024).decode()

            if request and len(request) > 0:
                # edit the request to use the NextBus domain
                request = self.format_request(request)

                if request is None:
                    conn.shutdown(socket.SHUT_WR)
                    conn.close()
                else:
                    start = time.time()
                    self.doRequest(request, conn)
                    request_line, _ = request.split('\r\n', 1)
                    list = request_line.split(' ')
                    path = list[1]
                    self.stats.addStat(time.time()-start, path)
                    self.stats.requestCounter(path)
            else:
                with self.print_lock:
                    print('Not able to receive client data from client')

                conn.shutdown(socket.SHUT_WR)
                conn.close()

            time.sleep(0.05)

    '''
        request data from the NextBus API
    '''
    def doRequest(self, request, conn):
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
                    proxySocket.settimeout(1)
                    proxySocket.connect((self.NETBUS_DOMAIN, self.NETBUS_PORT))
                except:
                    print('Port ', self.NETBUS_PORT, ' is closed!')
                try:
                    print('Connected to ', self.NETBUS_DOMAIN)
                    proxySocket.send(request.encode())

                    while True:
                        data = proxySocket.recv(self.BUFFSIZE)

                        if data and len(data) > 0:
                            conn.send(data)
                        else:
                            conn.shutdown(socket.SHUT_WR)
                            conn.close()
                            break

                    proxySocket.close()
                except Exception as msg:
                    conn.shutdown(socket.SHUT_WR)
                    conn.close()
                    proxySocket.shutdown(socket.SHUT_RD)
                    proxySocket.close()

    '''
        Create the new request to retrieve data from NextBus
    '''
    def format_request(self, data):
        request = None

        if len(data) > 0:
            request_line, _ = data.split('\r\n', 1)
            list = request_line.split(' ')
            http_request = list[0]
            path = list[1]
            request = http_request+" " + path + " HTTP/1.1\r\nHost: " + self.NETBUS_DOMAIN \
                      + "\r\nAccept-Encoding: gzip, deflate\n\n"
        return request



if __name__ == '__main__':
    server = ReverseProxyServer('localhost')
    server.start()

