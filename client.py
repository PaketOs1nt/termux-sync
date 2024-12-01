from concurrent.futures import ThreadPoolExecutor
from sync import default

import ipaddress
import threading
import argparse
import hashlib
import socket
import psutil
import gzip
import time
import json
import os

default_port = default.port
default_password = default.password
current_path = '.'
download_dir = 'downloads'

if not os.path.exists(download_dir):
    os.makedirs(download_dir)



class Network:
    @staticmethod
    def getranges():
        networks = []
        for _, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    try:
                        if not ip.startswith("127") and not ip.startswith("169.254"):
                            network = ipaddress.IPv4Network(f"{ip}/{addr.netmask}", strict=False)
                            networks.append(str(network.network_address) + '/' + str(network.prefixlen))
                    except ValueError:
                        pass
        
        return networks
    
    @staticmethod
    def scanport(host: str, port: int) -> bool:
        try:    
            with socket.socket() as s:
                result = s.connect_ex((host, port))
            return result == 0
        except: return False

def scanner():
    ctime = time.time()
    plock = threading.Lock()

    def _scan(ip: str):
        if Network.scanport(ip, default_port):
            with plock:
                print('[+] detected device with sync-server: ' + ip)

    with ThreadPoolExecutor(2000) as executor:
        for range in Network.getranges():
            range = ipaddress.IPv4Network(range)
            for ippp in range.hosts():
                executor.submit(_scan, ippp.compressed)

    print(f"[i] scan time: {time.time()-ctime:.3}")

def connect(ip: str):
    global current_path
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, default_port))
        sock.send(hashlib.sha384(default_password.encode('utf-8')).hexdigest().encode('utf-8'))

        while True:
            command = input(f'termux-sync@{ip} {current_path} $ ')
            if command.startswith('ls ') or command == 'ls':
                if command == 'ls':
                    command = f'ls {current_path}'

                sock.send(command.encode('utf-8'))
                data = json.loads(sock.recv(4096).decode('utf-8'))
                for file, format in data.items():
                    print(f'{file}        [{format}]')
            
            elif command.startswith('dl '):
                path = command[3:]
                if current_path != '.':
                    command = f'dl {os.path.join(current_path[2:], path)}'
                sock.send(command.encode('utf-8'))
                ftype = sock.recv(1024).decode('utf-8')

                raw_fsize = sock.recv(1024)
                fsize = int.from_bytes(raw_fsize, byteorder='big')
                
                print(f'downloading {path} ({fsize} bytes, type: {ftype}) ')

                if not ftype == 'dir':
                    content = gzip.decompress(sock.recv(fsize))
                else:
                    content = sock.recv(fsize)
    
                if ftype == 'dir':
                    path+='.zip'

                nfile = os.path.join(download_dir, path)
                with open(nfile, 'wb') as f:
                    f.write(content)
                    
                print(f'downloaded {path} and saved in {nfile}')
            
            elif command.startswith('cd '):
                path = command[3:]
                if path == '.':
                    pass

                elif path == '..':
                    current_path = os.path.dirname(current_path)
                
                else:
                    current_path = os.path.join(current_path, path)
    
    except KeyboardInterrupt:
        exit()

    except Exception as e:
        input(e)


def main():
    parser = argparse.ArgumentParser(description="Termux synchronization client")

    parser.add_argument("-port", help="set custom port", required=False, type=int)
    parser.add_argument("-target", help="target ip (no scanning)", required=False, type=str)
    parser.add_argument("-password", help="set custom password", required=False, type=str)
        
    args = parser.parse_args()
    target = args.target

    if args.port:
        global default_port
        default_port = args.port

    if args.password:
        global default_password
        default_port = args.password

    if target:
        connect(target)

    else:
        socket.setdefaulttimeout(3)
        scanner()
        socket.setdefaulttimeout(None)
        while True:
            connect(input('[?] enter target ip: '))

if __name__ == '__main__':
    main()