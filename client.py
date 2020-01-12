"""
    Client side
"""

import socket
from json import dumps, loads
import sys

SERVER = sys.argv[1]
PORT = int(sys.argv[2])

# Made a socket instance
CLIENT = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Buffer size
BUFFER = 1024

# Gives 10 seconds perform a command
socket.setdefaulttimeout(10)


def send(message):
    """
        Sends a message to the server. If the message length is more than buffer size, it sends this
        message in parts.
    """
    message = dumps(message)
    length = len(message)
    CLIENT.sendall(str(length).encode())
    while CLIENT.recv(BUFFER) != 'ready':
        while length > BUFFER:
            CLIENT.sendall(message.encode()[:BUFFER])
            message = message[BUFFER:]
            length -= BUFFER
        CLIENT.sendall(message.encode())
        break


def receive():
    """
        Receives a message from the client. It receives its length first and then receives the
        message whether in full or in parts, depending on its length.
    """
    length = CLIENT.recv(BUFFER)
    CLIENT.sendall('ready'.encode())
    messageb = b''
    while len(messageb) != int(length):
        messageb += CLIENT.recv(BUFFER)
    return loads(messageb)


try:
    # Tries to connect
    CLIENT.connect((SERVER, PORT))
except ConnectionRefusedError:
    # If the server is turned off
    print('Server is not available')
    sys.exit()

try:
    # Sends GET_BOARDS as soon as connects
    send('GET_BOARDS')
    # Receives boards
    BOARDS = receive()
    if BOARDS == 'No message boards defined':
        print(BOARDS)  # Print no message boards defined
        raise KeyboardInterrupt
    # Prints message boards in a nice way:
    # Message board number: message board name
    REPLY = ''
    for i in BOARDS:
        REPLY = REPLY + '{}. {}\n'.format(i, BOARDS[i].replace('_', ' '))
    print(REPLY)
    print('Type your message:')
    while True:
        # Prompts user for the input
        MY_INPUT = input()
        if MY_INPUT == 'QUIT':
            raise KeyboardInterrupt
        if MY_INPUT == 'POST':
            BOARD_NUMBER = input('Board number: ')
            MESSAGE_TITLE = input('Message title: ').replace(' ', '_')
            MESSAGE_CONTENT = input('Message content: ')
            # Sends POST_MESSAGE request to the server
            send('POST_MESSAGE {} {} {}'.format(BOARD_NUMBER, MESSAGE_TITLE, MESSAGE_CONTENT))
            # Prints 'sent' or errors
            print(receive())
        else:
            send('GET_MESSAGES ' + MY_INPUT)
            RECEIVED = receive()
            # If received data is not a dictionary, it is an error (string)
            if isinstance(RECEIVED, dict):
                FILES_LI = ''
                for i in RECEIVED:
                    FILES_LI = FILES_LI + '{}: {}\n'.format(i[16:-4].replace('_', ' '), RECEIVED[i])
                print(FILES_LI)
            else:
                # Prints error
                print(RECEIVED)
except KeyboardInterrupt:
    # When user quits
    print('Goodbye!')
    CLIENT.close()
    sys.exit()
except (EOFError, ConnectionRefusedError, ValueError, ConnectionResetError, BrokenPipeError):
    # When the server is turned off after the client connected or other problems with the server
    print('Server is not available')
    CLIENT.close()
    sys.exit()
except socket.timeout:
    print('Timeout')
