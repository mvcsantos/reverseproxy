import time
from proxy import ReverseProxyServer

if __name__ == '__main__':
    serverURL = 'pythonprogramming.net'
    netbusHost = 'webservices.nextbus.com'
    server = ReverseProxyServer('localhost')
    server.start()

