import socket
import threading
import select
from queue import Queue



# Notes: python 3.6 socket seems to be synchronous
# so there is a need to implement multithreading to improve performance
# and allow the proxy to scale

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
        self.buffer_size = 8096

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

    # Threaded request processing
    # Process the request's from the queue
    def process_requests(self):
        response = b'No data to return'
        while True:
            conn = self.queue.get()
            request = conn.recv(1024).decode()

            # TODO: check if it's a valid http request (regex)
            if len(request) > 0:
                # edit the request to use the NextBus domain
                request = self.format_request(request)

                # check cache first
                response = self.doRequest(request)
                if response:
                    with self.print_lock:
                        print('Response: \n', response, '\n\n')

                else:
                    print('Not able to connect to NextBus')
                    return

            else:
                with self.print_lock:
                    print('Not able to receive client data')
            conn.sendall(response)
            self.queue.task_done()

    # request data from the NextBus API
    def doRequest(self, request):
        response = ""

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
                    response = proxySocket.recv(self.buffer_size)
                    proxySocket.close()
                    #size = re.search('^Content-Length: [0-9]+$', result)

                except:
                    print('Port ', self.NETBUS_PORT, ' is closed!')
                    return
        return response

    def format_request(self, data):
        request_line, headers = data.split('\r\n', 1)
        list = request_line.split(' ')
        http_request = list[0]
        path = list[1]
        request = http_request+" " + path + " HTTP/1.1\r\nHost: " + self.NETBUS_DOMAIN + "\r\nAccept-Encoding: gzip, deflate\n\n"

        return request