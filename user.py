import uuid

online_users = {}


def update_user_status(username, status):
    if status == "online":
        online_users[username] = status
    elif status == "offline":
        online_users.pop(username, None)


def get_online_users():
    return [user for user, status in online_users.items() if status == "online"]


def generate_message_id():
    return str(uuid.uuid4())
