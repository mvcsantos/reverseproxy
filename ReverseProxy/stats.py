import threading
import socket
import json
import time


'''
    Client requests statistics
'''
class Stats (threading.Thread):

    stats_lock = threading.Lock()

    def __init__(self, host, port):
        threading.Thread.__init__(self)

        # endpoint
        self.HOST = host
        self.PORT = port
        self.BUFFSIZE = 1024

        self.slow_requests = {}
        self.queries = {}
        self.threshold = 10.0

    def run(self):
        self.startEndpoint()

    '''
        Start listening for statistics requests
    '''
    def startEndpoint(self):
        print("init proxy")
        try:
            self.proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.proxy_socket.settimeout(1)
            self.proxy_socket.setblocking(True)
            self.proxy_socket.bind((self.HOST, self.PORT))

            self.proxy_socket.listen(10)

            while True:
                print('Wainting for connections: ')
                conn, addr = self.proxy_socket.accept()
                print('Connected to : ', addr, ' (client)')

                data = conn.recv(self.BUFFSIZE).decode()
                response = self.processRequest(data)
                conn.send("HTTP/1.0 200 OK\r\n".encode())
                conn.send("Content-Type: application/json\r\n\r\n".encode())
                conn.send(response.encode())
                conn.close()
                time.sleep(0.05)

        except socket.error as socketerror:
            print("Error: ", socketerror)

    '''
        Check the path and generates the JSON response
    '''
    def processRequest(self, request):
        request_line, headers = request.split('\r\n', 1)
        list = request_line.split(' ')
        path = list[1]

        if path == "/api/v1/stats":
            return json.dumps({"slow_requests":self.slow_requests, "queries":self.queries})
        elif path == "/api/v1/slowrequests":
            return json.dumps(self.slow_requests)
        elif path == "/api/v1/queries":
            return json.dumps(self.queries)
        else:
            return "Invalid request"

    '''
        Add new data in Slow requests
    '''
    def addStat(self, time, path):
        if time > self.threshold:
            with self.stats_lock:
                self.slow_requests.update({path:time})

    '''
        Increments the request counter
    '''
    def requestCounter(self, path):
        if path in self.queries:
            with self.stats_lock:
                self.queries.update({path: self.queries[path]+1})
        else:
            with self.stats_lock:
                self.queries.update({path:1})



