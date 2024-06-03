from typing import Coroutine, Callable, Optional


class QuicStreamEvent:
    def __init__(self, stream_id, data, end_stream):
        self.stream_id = stream_id
        self.data = data
        self.end_stream = end_stream


class EchoQuicConnection:
    def __init__(self, send, receive, close, new_stream):
        self.send = send
        self.receive = receive
        self.close = close
        self.new_stream = new_stream

    def new_stream(self):
        return self.new_stream()
