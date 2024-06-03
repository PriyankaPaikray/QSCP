import asyncio
from typing import Coroutine, Dict
import json
from echo_quic import EchoQuicConnection, QuicStreamEvent
import pdu
import user
import aioconsole


async def send_presence(conn: EchoQuicConnection, username: str, status: str):
    datagram = pdu.Datagram(
        pdu.MSG_TYPE_PRESENCE,
        {
            "username": username,
            "status": status,
        },
    )
    new_stream_id = conn.new_stream()
    qs = QuicStreamEvent(new_stream_id, datagram.to_bytes(), False)
    await conn.send(qs)


async def send_message(
    conn: EchoQuicConnection, username: str, recipient_username: str, chat_message: str
):
    datagram = pdu.Datagram(
        pdu.MSG_TYPE_CHAT,
        {
            "sender_username": username,
            "recipient_username": recipient_username,
            "message": chat_message,
            "message_id": user.generate_message_id(),
        },
    )
    new_stream_id = conn.new_stream()
    qs = QuicStreamEvent(new_stream_id, datagram.to_bytes(), False)
    await conn.send(qs)


async def chat_client_proto(scope: Dict, conn: EchoQuicConnection):
    username = await aioconsole.ainput("Enter your username: ")
    password = await aioconsole.ainput("Enter your password: ")
    
    datagram = pdu.Datagram(
        pdu.MSG_TYPE_AUTH, {"username": username, "password": password}
    )
    new_stream_id = conn.new_stream()
    qs = QuicStreamEvent(new_stream_id, datagram.to_bytes(), False)
    await conn.send(qs)

    authenticated_future = asyncio.Future()
    input_event = asyncio.Event()
    state = "USER_SELECTION"  

    async def receive_messages():
        try:
            while True:
                message: QuicStreamEvent = await conn.receive()
                dgram_resp = pdu.Datagram.from_bytes(message.data)

                if dgram_resp.mtype == pdu.MSG_TYPE_AUTH_ACK:
                    print(f"Authentication successful.")
                    authenticated_future.set_result(True)
                elif dgram_resp.mtype == pdu.MSG_TYPE_AUTH_NACK:
                    print(f"Authentication failed. Reason: {dgram_resp.msg['reason']}")
                    authenticated_future.set_result(False)
                elif dgram_resp.mtype == pdu.MSG_TYPE_ONLINE_USERS:
                    if state == "USER_SELECTION" or state == "CHAT":
                        online_users = dgram_resp.msg["online_users"]
                        print("\033c", end="")  # Clear the console
                        print(f"Hey, {username.upper()} Welcome\n")
                        print("===================================================================")
                        print("Online users:")
                        for online_user in online_users:
                            if online_user != username:
                                print(online_user)
                        print()
                        print("===================================================================")

                        if state == "USER_SELECTION":
                            print(
                                "Enter the username of the user you want to chat with (or 'quit' to exit): ",
                                flush=True,
                                end="",
                            )
                        elif state == "CHAT":
                            input_event.set()
                elif dgram_resp.mtype == pdu.MSG_TYPE_CHAT:
                    sender_username = dgram_resp.msg["sender_username"]
                    chat_message = dgram_resp.msg["message"]
                    print(
                        f"\033[2K\033[1GNew message from {sender_username}: {chat_message}",
                        flush=True,
                    )
                    print("Enter your message (or 'back' to select another user): ", end="")
                elif dgram_resp.mtype == pdu.MSG_TYPE_PRESENCE_ACK:
                    pass  
                elif dgram_resp.mtype == pdu.MSG_TYPE_CHAT_ACK:
                    pass 
                elif dgram_resp.mtype == pdu.MSG_TYPE_CHAT_NACK:
                    pass 
                else:
                    print(f"Unsupported message type: {dgram_resp.mtype}")
        except asyncio.CancelledError:
         pass
    receive_task = asyncio.create_task(receive_messages())

    authenticated = await authenticated_future
    if not authenticated:
        return

    await send_presence(conn, username, "online")

    while True:
        if state == "USER_SELECTION":
            recipient_username = await aioconsole.ainput(
                "Enter the username of the user you want to chat with (or 'quit' to exit): "
            )
            if recipient_username == "quit":
                print("Ending session")
                await send_presence(
                    conn, username, "offline"
                )  
                break
            state = "CHAT"  
            input_event.clear()

        elif state == "CHAT":
            input_task = asyncio.create_task(
                aioconsole.ainput(
                    "Enter your message (or 'back' to select another user): "
                )
            )
            wait_event_task = asyncio.create_task(input_event.wait())

            done, pending = await asyncio.wait(
                {input_task, wait_event_task}, return_when=asyncio.FIRST_COMPLETED
            )

            if input_task in done:
                chat_message = input_task.result()
                if chat_message == "back":
                    state = "USER_SELECTION"  
                    print(
                        "\033c", end=""
                    )  
                    wait_event_task.cancel()
                    continue
                await send_message(conn, username, recipient_username, chat_message)
            else:
                input_task.cancel()
                try:
                    await input_task
                except asyncio.CancelledError:
                    pass
                state = "USER_SELECTION" 
                print("\033c", end="")  

    receive_task.cancel()
    await receive_task
