import time
from proxy import ReverseProxyServer

if __name__ == '__main__':
    serverURL = 'pythonprogramming.net'
    netbusHost = 'webservices.nextbus.com'
    server = ReverseProxyServer('localhost')
    path = "/service/publicXMLFeed?command=agencyList"
    request = "GET " + path + " HTTP/1.1\nHost: " + netbusHost + "\nAccept-Encoding: gzip, deflate\n\n"

    while True:
        time.sleep(1.0)