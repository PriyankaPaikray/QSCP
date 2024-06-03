import json

MSG_TYPE_AUTH = 0x02
MSG_TYPE_AUTH_ACK = 0x03
MSG_TYPE_AUTH_NACK = 0x04
MSG_TYPE_CHAT = 0x05
MSG_TYPE_CHAT_ACK = 0x06
MSG_TYPE_CHAT_NACK = 0x07
MSG_TYPE_PRESENCE = 0x08
MSG_TYPE_PRESENCE_ACK = 0x09
MSG_TYPE_ONLINE_USERS = 0x0A


class Datagram:
    def __init__(self, mtype: int, msg: str, sz: int = 0):
        self.mtype = mtype
        self.msg = msg
        self.sz = len(self.msg)

    def to_json(self):
        return json.dumps(self.__dict__)

    @staticmethod
    def from_json(json_str):
        return Datagram(**json.loads(json_str))

    def to_bytes(self):
        return json.dumps(self.__dict__).encode("utf-8")

    @staticmethod
    def from_bytes(json_bytes):
        return Datagram(**json.loads(json_bytes.decode("utf-8")))
