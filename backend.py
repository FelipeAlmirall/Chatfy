import asyncio
import websockets
import json
from datetime import datetime

USERS       = set()
NAMES       = set()
USERS_NAMES = dict()

HISTORY     = [] # Historical Data Appended with the following pattern:
                 # ["Timestamp", "Sender", "Receiver", "Content"]

# GENERATE JSON MESSAGE FROM SERVER TO CLIENT
def accept_name(user):
    message = user
    return json.dumps({"action": "acceptName", "sender":"system", "content": message})

def private_message_event(message,sender):
    return json.dumps({"action": "pvtMessage", "sender":sender, "content": message})

def public_message_event(message,sender):
    return json.dumps({"action": "publicMessage", "sender":sender, "content": message})

def joined_event(user):
    return json.dumps({"action": "publicMessage", "sender":"system", "content": "%s joined the room."%(user)})

def left_event(user):
    return json.dumps({"action": "publicMessage", "sender":"system", "content": "%s left the room."%(user)})

def retry_name_message_event():
    return json.dumps({"action": "retryName", "sender":"system", "content": 'error'})

##########################################################################################################

async def private_message(connection, message, receiver):
    if USERS:  # asyncio.wait doesn't accept an empty list
        receiver_connection = None
        for conn, name in USERS_NAMES.items():
            if name == receiver:
                receiver_connection = conn
            
        if receiver_connection:
            message = private_message_event(message, USERS_NAMES[connection])
            await receiver_connection.send(message)

async def public_message(connection, message):
    if USERS:  # asyncio.wait doesn't accept an empty list
        message = public_message_event(message,USERS_NAMES[connection])
        for user in USERS:
            if user != connection:
                await user.send(message)

async def enter_room(connection):
    if USERS:
        message = joined_event(USERS_NAMES[connection])
        for user in USERS:
            if user != connection:
                await user.send(message)

async def leave_room(connection):
    if USERS:
        message = left_event(USERS_NAMES[connection])
        for user in USERS:
            if user != connection:
                await user.send(message)

async def name_retry(connection):
    message = retry_name_message_event()
    await connection.send(message)

async def register(connection):
    while True:
        json_msg = await connection.recv()
        name_aux = json.loads(json_msg)["content"]
        if name_aux.startswith("@name "):
            name = name_aux[6:]
            if name not in NAMES:
                message = accept_name(name)
                await connection.send(message)
                break
            else:
                message = retry_name_message_event()
                await connection.send(message)
        else:
            message = retry_name_message_event()
            await connection.send(message)
    
    USERS.add(connection)
    NAMES.add(name)
    USERS_NAMES[connection] = name
    await enter_room(connection)

async def unregister(connection):
    USERS.remove(connection)
    NAMES.remove(USERS_NAMES[connection])
    await leave_room(connection)

async def main(connection, path):
    await register(connection)
    try:
        async for message in connection:
            data = json.loads(message)
            if data["action"] == "publicMessage":
                HISTORY.append([datetime.now(), data])
                await public_message(connection, data["content"])
            elif data["action"] == "pvtMessage":
                HISTORY.append([datetime.now(), data])
                await private_message(connection, data["content"], data["receiver"])
            elif data["action"] == "tryName":
                await name_retry(connection, data["content"], data["receiver"])                 
    except:
        await unregister(connection)

start_server = websockets.serve(main, "localhost", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()


