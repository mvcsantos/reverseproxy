# reverseproxy
Reverse proxy implementation using KQueue in python 3.6

Technology used:

- KQueue to create assyncronouns taks in the main thread
- Python Multithreading, Queue and Sockets to process each request

How it works:

The main thread waits for connections and accept them assynchronously. Once a client connects to the socket, the main thread adds the accepted connection into the queue in order to be processed. A pool of threads will dequeue the accepted connection, redirect the request to the NextBus API and return the data back to the client. Once everything is taken care of, the connection is closed and the thread is ready to process another request.
