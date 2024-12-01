import hashlib
import zipfile
import socket
import json
import gzip
import time
import os
import io

bytesloader = lambda kb: ((kb + 1023) // 1024) * 1024

class Server:
    def __init__(self, password: str, port: int):
        self.__password = password

        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__sock.bind(('0.0.0.0', port))
        self.__sock.listen(16)
    
    def accept(self):
        return self.__sock.accept()

    def memory_zip(self, dir: str) -> bytes:
        buffer = io.BytesIO()
        
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for root, _, files in os.walk(dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, start=dir)
                    zip_file.write(full_path, arcname=arcname)

        return buffer.getvalue()

    def dir_structure(self, path: str) -> dict:
        try:
            result = {}
            for entry in os.scandir(path):
                if entry.is_file():
                    result[entry.name] = "file"

                elif entry.is_dir():
                    result[entry.name] = "dir"
        except:
            result = {'error': 'dir not exits, return to "."'}    
        return result

    def close(self):
        self.__sock.close()

    def auth(self, client_sock: socket.socket) -> bool:
        passhash = client_sock.recv(1024)
        if passhash.decode('utf-8') == hashlib.sha384(self.__password.encode('utf-8')).hexdigest():
            return True
        else:
            return False
    
    def send_info(self, client_sock: socket.socket, path: str):
        raw_structure = self.dir_structure(path=path)
        structure = json.dumps(raw_structure).encode('utf-8')
        client_sock.send(structure)

    def send_data(self, client_sock: socket.socket, path: str):
        if os.path.exists(path):
            if not os.path.isdir(path):
                with open(path, mode='rb') as fdataf:
                    data = gzip.compress(fdataf.read())

                ftype = 'file'

            else:
                data = self.memory_zip(path)
                ftype = 'dir'
            
            int_data_size = bytesloader(len(data))
            data_size = int_data_size.to_bytes((int_data_size.bit_length() + 7) // 8, byteorder='big')
            client_sock.send(ftype.encode('utf-8'))
            time.sleep(0.005)
            client_sock.send(data_size)
            time.sleep(0.005)
            client_sock.send(data)

        else:
            client_sock.send(b'invalid_path')

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()