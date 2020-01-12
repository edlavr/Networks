"""
    Server side
"""

import socket
import threading
from json import dumps, loads
import os
import sys
import time

# Buffer size
BUFFER = 1024


def number_to_name(number, my_dict):
    """
        Converts a board number to a board name
    """
    return my_dict[int(number)].strip("'")


def vibe_check(string):
    """
        Checks if the string is alphanumerical+underscores
    """
    if string.isdigit():
        return True
    if string == '':
        return False
    for letter in string:
        if not (letter.isalnum() or letter == '_'):
            return False
    return True


class ClientThread(threading.Thread):
    """
        A separate thread for every user
    """
    def send(self, message):
        """
            Sends a message to the client. If the message length is more than buffer size,
            it sends this message in parts.
        """
        message = dumps(message)
        length = len(message)
        self.csocket.sendall(str(length).encode())
        while self.csocket.recv(BUFFER) != 'ready':
            while length > BUFFER:
                self.csocket.sendall(message.encode()[:BUFFER])
                message = message[BUFFER:]
                length -= BUFFER
            self.csocket.sendall(message.encode())
            break

    def receive(self):
        """
            Receives a message from the client. It receives its length first and then receives the
            message whether in full or in parts, depending on its length.
        """
        length = self.csocket.recv(BUFFER)
        self.csocket.sendall('ready'.encode())
        messageb = b''
        while len(messageb) != int(length):
            messageb += self.csocket.recv(BUFFER)
        return loads(messageb)

    def __init__(self, clientsocket, clientthread):
        threading.Thread.__init__(self)
        self.csocket = clientsocket
        self.clientthread = clientthread

    def run(self):
        """
            Main sequence
        """
        while True:
            # Status is 'error' unless the command is successful. Used in server log
            status = 'Error'

            try:
                # Receives a message
                received = self.receive()
                print('Received message of type ' + type(received).__name__ + ' from client ' +
                      CLIENT_ADDRESS[0] + ':' + str(CLIENT_ADDRESS[1]))
            except ValueError:
                # ValueError occurs when no information is received. That happens when
                # client quits from the program. When client quits, the server closes the thread.
                print('\nUser ' + CLIENT_ADDRESS[0] + ':' + str(CLIENT_ADDRESS[1]) + ' exited\n')
                self.csocket.close()
                break

            try:
                # Sorts message boards in /board, excludes not folders and .DS_Store log file that
                # is sometimes created by MacOS automatically, then makes a dictionary with message
                # boards numbers as keys and message board names as values.
                boards = sorted(os.listdir('./board'))
                for i in boards:
                    if os.path.isfile(i) or i == '.DS_Store':
                        boards.remove(i)
                boards = dict(enumerate(boards, 1))
            except FileNotFoundError:
                # If there is no /board folder, FileNotFoundError occurs
                boards = {}

            if received == 'GET_BOARDS':
                if boards != {}:
                    status = 'OK'
                    reply = boards
                else:
                    reply = 'No message boards defined'

            elif received[:12] == 'GET_MESSAGES':
                board = received[13:]  # extracts board number
                received = received[:12]  # extracts GET_MESSAGES, made for server log
                try:
                    if not board.isdigit():
                        raise IndexError
                    board = number_to_name(board, boards)
                    # sorts by timestamp. Newest message is at the bottom
                    messages_li = sorted(os.listdir('./board/' + board), key=lambda x: x[:14])
                    # removes .DS_Store, this time from message boards
                    if '.DS_Store' in messages_li:
                        messages_li.remove('.DS_Store')
                    # makes a dictionary with message titles as keys and message content as values
                    reply = {}
                    for items in messages_li:
                        with open('./board/' + board + '/' + items, errors='ignore') as file:
                            reply[items] = file.read()
                    if reply == {}:
                        raise ValueError
                    # if there are more than 100 messages, cuts the dictionary
                    if len(list(reply.keys())) > 100:
                        reply = dict(list(reply.items())[-100:])
                except ValueError:
                    # if the message board is empty
                    status = 'OK'
                    reply = 'Empty message board'
                except KeyError:
                    # if there is no message board that matches the input number
                    reply = 'Message board not found'
                except IndexError:
                    # if board number is not a number
                    reply = 'Invalid input'
                else:
                    status = 'OK'

            elif received[:12] == 'POST_MESSAGE':
                try:
                    # received is 'POST_MESSAGE'
                    # board is the first input: a message board number
                    # message_title is the second input: a title of the message
                    # message_content is the third input: what is inside the file
                    received, board, message_title, message_content = received.split(' ', 3)
                    if not board.isdigit():
                        raise FileNotFoundError
                    board = number_to_name(int(board), boards)
                    if not vibe_check(message_title):
                        raise IndexError
                    if message_content == '':
                        raise SyntaxError
                    # adds a timestamp to the title
                    message_title = time.strftime("%Y%m%d-%H%M%S") + '-' + message_title
                    # creates a new file
                    with open('./board/' + board + '/' + message_title + '.txt', "w",
                              errors='ignore') as file:
                        file.write(message_content)
                    reply = 'Sent'
                    status = 'OK'
                except (FileNotFoundError, ValueError):
                    # when board number is not a number
                    reply = 'Invalid board number'
                except IndexError:
                    # when title is not alphanumerical
                    reply = 'Invalid message title'
                except KeyError:
                    # no board title found for the board number
                    reply = 'Unknown board'
                except SyntaxError:
                    reply = 'Empty message content'
                except OSError:
                    # That is OS limitation
                    reply = 'Message title too long'

            else:
                # useless else but otherwise gives a warning that reply might be referenced before
                # assignment
                reply = ''
            print('Sent message of type ' + type(reply).__name__ + ' to client ' +
                  CLIENT_ADDRESS[0] + ':' + str(CLIENT_ADDRESS[1]) + '\n')
            self.send(reply)
            with open('server.log', 'a') as log:
                log.write(self.clientthread[0] + ':' + str(self.clientthread[1]) + '\t' +
                          time.strftime("%d.%m.%Y-%H:%M:%S\t") + received + '\t' + status + '\n')


LOCALHOST = sys.argv[1]
PORT = int(sys.argv[2])

# creates a socket
SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('Socket Created')
SERVER.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# tries binding, fails if, for example, the port is busy
try:
    SERVER.bind((LOCALHOST, PORT))
    print('Sock Bounded')
except socket.error:
    print('Binding Failed')
    sys.exit()

print('Socket Ready')

while True:
    try:
        SERVER.listen(1)
        CLIENT_SOCK, CLIENT_ADDRESS = SERVER.accept()
        print('\nNew User: ' + CLIENT_ADDRESS[0] + ':' + str(CLIENT_ADDRESS[1]) + '\n')
        # creates a thread
        NEW_THREAD = ClientThread(CLIENT_SOCK, CLIENT_ADDRESS)
        # starts a thread
        NEW_THREAD.start()
    except KeyboardInterrupt:
        os._exit(1)
