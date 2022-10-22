#!/usr/bin/python3
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
import serial
from shared_memory_dict import SharedMemoryDict
from multiprocessing import Process
from urllib.parse import urlparse, parse_qs


f = serial.Serial(port='/dev/ttyAMA0',
                            baudrate=115200,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE,
                            bytesize=serial.EIGHTBITS,
                            timeout=0.3)


def decode_string(string):
    print(string)
    data = []

    for byte in string.strip("\n").split(":")[:21]:
        data.append(int(byte,16))

    start = data[0]
    idx = data[1] - 0xa0
    speed = float(data[2] | (data[3] << 8)) / 64.0
    in_checksum = data[-2] + (data[-1] << 8)

    # first data package (4 bytes after header)
    angle = idx*4 + 0
    angle_rad = angle * math.pi / 180.
    dist_mm = data[4] | ((data[5] & 0x1f) << 8)
    quality = data[6] | (data[7] << 8)

    if data[5] & 0x80:
         print("X - "),
    else:
        print("O - "),
    if data[5] & 0x40:
         print("NOT GOOD")

    return {"speed": speed, "angle": angle, "distance": dist_mm, "quality": quality}


def keep_reading_data():
    shm = SharedMemoryDict(name="x11_reading", size=1024)
    buf = f.read(1)
    started = False
    string = "Start"
    while True:
        if buf != b'':
            enc = (buf.hex() + ":")
            if enc == "fa:":
                if started:
                    try:
                        decoded = decode_string(string)
                        shm[str(decoded["angle"])] = decoded["distance"]

                    except Exception as e:
                        print(e)

                started = True
                string = "fa:"
            elif started:
                string += enc

        buf = f.read(1)



class X11Server(BaseHTTPRequestHandler):
    def do_GET(self):
        # first we need to parse it
        parsed = urlparse(self.path)
        # get the request path, this new path does not have the query string
        path = parsed.path

        if path == "/api/v1/data":
            self.send_response(200)
            self.send_header("Content-type", "text/json")
            self.end_headers()

            shm = SharedMemoryDict("x11_reading")

            wfile = self.wfile
            wfile.write(bytes("[\r\n", "utf-8"))
            first = True
            for k, v in shm:
                if not first:
                    wfile.write(b',')
                else:
                    first = False
                wfile.write(
                    bytes("{\"distance\":%s,\"angle\":%s}\r\n" % (v, k), "utf-8"))

            wfile.write(b']')
            wfile.flush()
        self.wfile.close()


if __name__ == '__main__':
    #  # Start to read lidar
    p = Process(target=keep_reading_data)
    print("Keep sensor reading")
    p.start()


    webServer = HTTPServer(("0.0.0.0", 8080), X11Server)
    print("Server started http://%s:%s" % ("0.0.0.0", 8080))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")