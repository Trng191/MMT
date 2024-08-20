import socket
import threading
import os
import requests
from tkinter import Tk, Button, Entry, Label, filedialog

# Configuration for server URL and socket connection
SERVER_URL = "http://127.0.0.1:5000"
SOCKET_IP = "127.0.0.1"
SOCKET_PORT = 12345

def get_file_size(filename):
    response = requests.get(f"{SERVER_URL}/filesize/{filename}")
    if response.status_code == 200:
        return int(response.text)
    else:
        return 0

def download_chunk(filename, start, end, save_path):
    response = requests.get(f"{SERVER_URL}/download/{filename}", params={'start': start, 'end': end}, stream=True)
    if response.status_code == 200:
        chunk_filename = f"{save_path}.part{start}"
        with open(chunk_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
    else:
        print(f"Failed to download chunk [{start}:{end}]")

def upload_chunk(filename, start, end, remote_filename):
    with open(filename, 'rb') as f:
        f.seek(start)
        chunk = f.read(end - start)
    
    files = {'file': (remote_filename, chunk)}
    data = {'filename': remote_filename, 'start': start}
    response = requests.post(f"{SERVER_URL}/upload", files=files, data=data)

    if response.status_code != 200:
        print(f"Failed to upload chunk [{start}:{end}]: {response.text}")

def download_file(filename, save_path, num_threads=4):
    file_size = get_file_size(filename)
    chunk_size = file_size // num_threads

    threads = []
    for i in range(num_threads):
        start = i * chunk_size
        end = file_size if i == num_threads - 1 else (i + 1) * chunk_size
        thread = threading.Thread(target=download_chunk, args=(filename, start, end, save_path))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Combine the downloaded file parts
    with open(save_path, 'wb') as f:
        for i in range(num_threads):
            part_filename = f"{save_path}.part{i * chunk_size}"
            with open(part_filename, 'rb') as part_file:
                f.write(part_file.read())
            os.remove(part_filename)

def upload_file(local_path, remote_filename, num_threads=4):
    file_size = os.path.getsize(local_path)
    chunk_size = file_size // num_threads

    threads = []
    for i in range(num_threads):
        start = i * chunk_size
        end = file_size if i == num_threads - 1 else (i + 1) * chunk_size
        thread = threading.Thread(target=upload_chunk, args=(local_path, start, end, remote_filename))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

def establish_socket_connection():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SOCKET_IP, SOCKET_PORT))
    return s

def send_socket_message(s, message):
    s.sendall(message.encode())
    response = s.recv(1024)
    print(f"Server response: {response.decode()}")

def choose_file_upload():
    local_path = filedialog.askopenfilename()
    if local_path:
        remote_filename = os.path.basename(local_path)
        upload_file(local_path, remote_filename)

def choose_file_download():
    filename = input_filename.get()
    save_path = filedialog.asksaveasfilename(defaultextension="*.*", initialfile=filename)
    if filename and save_path:
        download_file(filename, save_path)

def handle_socket_operations():
    s = establish_socket_connection()
    send_socket_message(s, "Hello Server!")
    s.close()

# GUI setup
root = Tk()
root.title("Client File Transfer")

Label(root, text="Server IP:").grid(row=0, column=0)
server_ip = Entry(root)
server_ip.grid(row=0, column=1)
server_ip.insert(0, SOCKET_IP)

Label(root, text="Port:").grid(row=1, column=0)
port = Entry(root)
port.grid(row=1, column=1)
port.insert(0, str(SOCKET_PORT))

Label(root, text="File Name for Download:").grid(row=2, column=0)
input_filename = Entry(root)
input_filename.grid(row=2, column=1)

Button(root, text="Upload File", command=choose_file_upload).grid(row=3, column=0, pady=10)
Button(root, text="Download File", command=choose_file_download).grid(row=3, column=1, pady=10)
Button(root, text="Socket Operation", command=handle_socket_operations).grid(row=4, column=0, columnspan=2, pady=10)

root.mainloop()
