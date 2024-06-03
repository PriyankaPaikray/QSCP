import asyncio
from typing import Coroutine, Dict
import json
from echo_quic import EchoQuicConnection, QuicStreamEvent
import pdu
import auth
import user

users = {}

async def broadcast_online_users():
    # Broadcast online users to all connected clients
    online_users = user.get_online_users()
    dgram_out = pdu.Datagram(pdu.MSG_TYPE_ONLINE_USERS, {"online_users": online_users})
    rsp_msg = dgram_out.to_bytes()
    for user_conn in users.values():
        new_stream_id = (
            user_conn.new_stream()
        )  # Generate a new stream ID for each user connection
        rsp_evnt = QuicStreamEvent(new_stream_id, rsp_msg, False)
        await user_conn.send(rsp_evnt)


async def chat_server_proto(scope: Dict, conn: EchoQuicConnection):
    while True:
        message: QuicStreamEvent = await conn.receive()
        dgram_in = pdu.Datagram.from_bytes(message.data)

        if dgram_in.mtype == pdu.MSG_TYPE_AUTH:
            username = dgram_in.msg["username"]
            password = dgram_in.msg["password"]

            if auth.authenticate_user(username, password):
                users[username] = conn

                # Send MSG_TYPE_AUTH_ACK to the authenticated client
                dgram_out = pdu.Datagram(pdu.MSG_TYPE_AUTH_ACK, {"username": username})
                rsp_msg = dgram_out.to_bytes()
                rsp_evnt = QuicStreamEvent(message.stream_id, rsp_msg, False)
                await conn.send(rsp_evnt)

                # Broadcast updated online users list
                await broadcast_online_users()
            else:
                dgram_out = pdu.Datagram(
                    pdu.MSG_TYPE_AUTH_NACK, {"reason": "Invalid credentials"}
                )
                rsp_msg = dgram_out.to_bytes()
                rsp_evnt = QuicStreamEvent(message.stream_id, rsp_msg, False)
                await conn.send(rsp_evnt)

        elif dgram_in.mtype == pdu.MSG_TYPE_CHAT:
            sender_username = dgram_in.msg["sender_username"]
            recipient_username = dgram_in.msg["recipient_username"]
            chat_message = dgram_in.msg["message"]
            print(recipient_username, users)
            if recipient_username in users:
                recipient_conn = users[recipient_username]
                new_stream_id = recipient_conn.new_stream()
                dgram_out = pdu.Datagram(
                    pdu.MSG_TYPE_CHAT,
                    {"sender_username": sender_username, "message": chat_message},
                )
                rsp_msg = dgram_out.to_bytes()
                rsp_evnt = QuicStreamEvent(new_stream_id, rsp_msg, False)
                await recipient_conn.send(rsp_evnt)

                dgram_ack = pdu.Datagram(
                    pdu.MSG_TYPE_CHAT_ACK, {"message_id": dgram_in.msg["message_id"]}
                )
                ack_msg = dgram_ack.to_bytes()
                ack_evnt = QuicStreamEvent(message.stream_id, ack_msg, False)
                await conn.send(ack_evnt)
            else:
                dgram_nack = pdu.Datagram(
                    pdu.MSG_TYPE_CHAT_NACK, {"reason": "Recipient not available"}
                )
                nack_msg = dgram_nack.to_bytes()
                nack_evnt = QuicStreamEvent(message.stream_id, nack_msg, False)
                await conn.send(nack_evnt)

        elif dgram_in.mtype == pdu.MSG_TYPE_PRESENCE:
            username = dgram_in.msg["username"]
            status = dgram_in.msg["status"]

            user.update_user_status(username, status)

            dgram_ack = pdu.Datagram(pdu.MSG_TYPE_PRESENCE_ACK, {"username": username})
            ack_msg = dgram_ack.to_bytes()
            ack_evnt = QuicStreamEvent(message.stream_id, ack_msg, False)
            await conn.send(ack_evnt)

            if status == "offline":
                # Remove the disconnected user from the users dictionary
                users.pop(username, None)


            # Broadcast updated online users list
            await broadcast_online_users()
        else:
            print(f"[svr] Unsupported message type: {dgram_in.mtype}")