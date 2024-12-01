from sync import proto, default

import threading
import argparse
import socket
import os

default_port = default.port
default_password = default.password

os.chdir(os.path.expanduser("~"))

def client_worker(server: proto.Server, clsock: socket.socket, addr):
    try:
        with clsock:
            authed = server.auth(clsock)
            if authed:
                print(f'new authed client! {addr[0]}')
                while True:
                    command = clsock.recv(1024).decode('utf-8')
                    if command.startswith('ls '):
                        if len(command) < 4:
                            path = '.'
                        else:
                            path = command[3:]

                        server.send_info(clsock, path)
                    
                    elif command.startswith('dl '):
                        if not len(command) < 4:
                            path = command[3:]
                            server.send_data(clsock, path)

            else:
                clsock.send(b'auth_error')
                clsock.close()

    except KeyboardInterrupt:
        print('stopping...')
        exit()

    except Exception as e:
        print(f'client worker error: {e}')


def server():
    global default_password, default_port
    print('server started!')
    try:
        with proto.Server(password=default_password, port=default_port) as server:
            while True:
                sock, addr = server.accept()
                threading.Thread(target=client_worker, args=(server, sock, addr), daemon=True).start()

    except Exception as e:
        print(f'server error: {e}')

def main():
    parser = argparse.ArgumentParser(description="Termux synchronization server")

    parser.add_argument("-port", help="set custom port", required=False, type=int)
    parser.add_argument("-password", help="set custom password", required=False, type=str)
        
    args = parser.parse_args()

    if args.port:
        global default_port
        default_port = args.port

    if args.password:
        global default_password
        default_port = args.password

    server()
if __name__ == '__main__':
    main()