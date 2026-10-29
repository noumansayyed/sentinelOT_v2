import logging, time
from snap7.server import Server
from snap7.type import SrvArea

logging.basicConfig(level=logging.INFO, format="%(asctime)s [S7-PLC] %(message)s")
log = logging.getLogger("s7-plc")

DB1 = bytearray(16)

def main():
    server = Server()
    server.register_area(SrvArea.DB, 1, DB1)
    server.create()
    server.start_to("0.0.0.0", 102)
    log.info("S7 server listening on 0.0.0.0:102, DB1 (16 bytes) registered")
    try:
        counter = 0
        while True:
            time.sleep(2)
            counter = (counter + 1) % 256
            DB1[0] = counter
            DB1[1] = counter ^ 0xFF
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        server.destroy()

if __name__ == "__main__":
    main()
