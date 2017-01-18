import time
from proxy import ReverseProxyServer

if __name__ == '__main__':
    server = ReverseProxyServer('localhost')
    server.start()

