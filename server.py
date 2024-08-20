import os
import socket
import threading
from flask import Flask, request, send_from_directory, abort, render_template
from flask_cors import CORS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024 * 10  # 10 GB

# Ensure the uploads directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def handle_upload_chunk(filename, start, data):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    # Initialize the file if it doesn't exist
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            f.write(b'\0' * (start + len(data)))
    with open(file_path, 'r+b') as f:
        f.seek(start)
        f.write(data)

def handle_download_chunk(filename, start, end):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    try:
        with open(file_path, 'rb') as f:
            f.seek(start)
            return f.read(end - start)
    except Exception as e:
        logging.error(f"Error during chunk reading: {e}")
        raise


@app.route('/filesize/<filename>', methods=['GET'])
def get_file_size(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return str(os.path.getsize(file_path))
    return "0", 404

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        start = int(request.args.get('start'))
        end = int(request.args.get('end'))
    except (TypeError, ValueError) as e:
        logging.error(f"Invalid start or end parameters: {e}")
        return "Invalid range parameters", 400
    
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    logging.info(f"Trying to download file from path: {file_path} with range {start}-{end}")
    
    if os.path.exists(file_path):
        try:
            data = handle_download_chunk(filename, start, end)
            return data, 200
        except Exception as e:
            logging.error(f"Error reading file chunk: {e}")
            return "Error reading file chunk", 500
    else:
        logging.error(f"File not found: {file_path}")
        return "File not found", 404



@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    filename = request.form['filename']
    start = int(request.form['start'])

    save_path = os.path.join(UPLOAD_FOLDER, filename)

    logging.info(f"Starting upload of chunk to {save_path} starting at {start}")

    # Tạo tệp mới nếu tệp không tồn tại
    if not os.path.exists(save_path):
        with open(save_path, 'wb') as f:
            f.write(b'\0' * start)

    with open(save_path, 'r+b') as f:
        f.seek(start)
        f.write(file.read())

    logging.info(f"Uploaded chunk to {save_path} starting at {start}")
    return "Upload successful", 200


@app.route('/')
def home():
    return render_template('app.html')

@app.route('/download_complete/<filename>', methods=['GET'])
def download_complete_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        logging.info(f"Serving file: {file_path}")
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    else:
        logging.error(f"File not found: {file_path}")
        abort(404, description="File not found")


def start_socket_server():
    SOCKET_IP = "127.0.0.1"
    SOCKET_PORT = 12345
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((SOCKET_IP, SOCKET_PORT))
        s.listen()
        logging.info(f"Socket server started on {SOCKET_IP}:{SOCKET_PORT}")
        while True:
            client_socket, addr = s.accept()
            logging.info(f"Connection from {addr}")
            # Handle client connection
    finally:
        s.close()

if __name__ == '__main__':
    socket_thread = threading.Thread(target=start_socket_server, daemon=True)
    socket_thread.start()
    
    app.run(port=5000, debug=True)
