from prometheus_client import start_http_server, Gauge
from http.server import BaseHTTPRequestHandler, HTTPServer
import serial
import os
from multiprocessing import shared_memory, Process
import mysql.connector
from urllib.parse import urlparse, parse_qs


##########################
# TFLuna Lidar
##########################
#
ser = serial.Serial("/dev/serial0", 115200,timeout=0.05) # mini UART serial device
#
############################
# read ToF data from TF-Luna
############################
#
def read_tfluna_data():
    while True:
         bytes_serial = ser.read(9) # read 9 bytes
         counter = len(bytes_serial) # count the number of bytes of the serial port
         if counter > 8:
            ser.reset_input_buffer() # reset buffer

            if bytes_serial[0] == 0x59 and bytes_serial[1] == 0x59: # check first two bytes
                distance = bytes_serial[2] + bytes_serial[3]*256 # distance in next two bytes
                strength = bytes_serial[4] + bytes_serial[5]*256 # signal strength in next two bytes
                temperature = bytes_serial[6] + bytes_serial[7]*256 # temp in next two bytes
                return distance,strength,temperature


if ser.isOpen() == False:
    ser.open() # open serial port if not open


def keep_reading_data(distance, cnx):
    shm = shared_memory.SharedMemory(name="tf_luna_reading", create=True, size=6)
    while True:
        distance_reading, strength, temperature = read_tfluna_data()  # read values
        buffer = shm.buf
        buffer[:2] = distance_reading.to_bytes(2, 'little')
        buffer[2:4] = strength.to_bytes(2, 'little')
        buffer[4:] = temperature.to_bytes(2, 'little')

        if distance_reading < 220:
            distance.set(distance_reading)
            insert_distance(distance_reading, cnx)
        else:
            distance.set(224)


def insert_distance(distance_reading, cnx):
    cursor = cnx.cursor()

    sql = ("INSERT INTO distance (date_created, distance) VALUES (NOW(), %(distance)s)")

    distance_values = {'distance': distance_reading}

    # Insert new employee
    cursor.execute(sql, distance_values)

    # Make sure data is committed to the database
    cnx.commit()

    cursor.close()


def start_prometheus():
    # Create a metric to track time spent and requests made.
    distance = Gauge('distance', 'The distance in centimeter between the sensor and the object underneath.')

    start_http_server(8090)


    cnx = mysql.connector.MySQLConnection(user='root', password=os.getenv('MYSQL_PASSWORD', None),
                                          host='127.0.0.1',
                                          database='distance')

    keep_reading_data(distance, cnx)


def get_distance_list(limit, wfile):
    cnx = mysql.connector.MySQLConnection(user='root', password=os.getenv('MYSQL_PASSWORD', None),
                                          host='127.0.0.1',
                                          database='distance')
    cursor = cnx.cursor()

    sql = ("SELECT distance, date_created FROM distance ORDER BY id DESC LIMIT %s" % (limit))

    # SELECT
    cursor.execute(sql)

    rows = cursor.fetchall()

    wfile.write(bytes("[\r\n", "utf-8"))
    first = True
    for r in rows:
        if not first:
            wfile.write(b',')
        else:
            first = False
        wfile.write(
            bytes("{\"distance\":%s,\"date_created\":\"%s\"}\r\n" % (r[0], r[1].strftime('%Y-%m-%d %H:%M:%S')),
                  "utf-8"))

    wfile.write(b']')
    wfile.flush()

    cursor.close()


class DistanceServer(BaseHTTPRequestHandler):
    def do_GET(self):
        # first we need to parse it
        parsed = urlparse(self.path)
        # get the request path, this new path does not have the query string
        path = parsed.path

        if path == "/api/v1/data":
            self.send_response(200)
            self.send_header("Content-type", "text/json")
            self.end_headers()

            shm = shared_memory.SharedMemory("tf_luna_reading")
            buffer = shm.buf
            distance_reading = buffer[0] + buffer[1] * 256  # distance in next two bytes
            if distance_reading > 220:
               distance_reading = 224

            strength = buffer[2] + buffer[3] * 256  # signal strength in next two bytes
            temperature = buffer[4] + buffer[5] * 256  # temp in next two bytes
            temperature = (temperature / 8.0) - 256.0  # temp scaling and offset

            self.wfile.write(bytes("{\"distance\":%s,\"strength\":%s,\"temperature\":%s}" % (distance_reading, strength, temperature), "utf-8"))
        else:
            if path == "/api/v1/list":
                limit = 100
                # get the query string
                query = parse_qs(parsed.query)
                try :
                    if "limit" in query:
                        limit = int(query["limit"][0])
                except ValueError:
                    limit = 100

                self.send_response(200)
                self.send_header("Content-type", "text/json")
                self.end_headers()

                get_distance_list(limit, self.wfile)

        self.wfile.close()


if __name__ == '__main__':
    # Start up the server to expose the metrics.
    p = Process(target=start_prometheus)
    print("Keep sensor reading")
    p.start()


    webServer = HTTPServer(("0.0.0.0", 8080), DistanceServer)
    print("Server started http://%s:%s" % ("0.0.0.0", 8080))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")

