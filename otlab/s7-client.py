import logging, time
import snap7

logging.basicConfig(level=logging.INFO, format="%(asctime)s [S7-HMI] %(message)s")
log = logging.getLogger("s7-client")

def try_connect():
    try:
        c = snap7.client.Client()
        c.connect("s7-plc", 0, 1, 102)
        return c
    except Exception as e:
        log.warning("connect failed: %s", e)
        return None

def main():
    time.sleep(3)
    counter = 0
    while True:
        client = try_connect()
        if client is None:
            log.warning("PLC not reachable, retrying in 3s")
            time.sleep(3)
            continue
        try:
            counter = (counter + 1) % 256
            payload = bytes([counter, counter ^ 0xFF])
            client.db_write(1, 4, payload)
            log.info("wrote DB1[4:6]=%s", payload.hex())
            data = client.db_read(1, 0, 6)
            log.info("read DB1[0:6]=%s", data.hex())
        except Exception as e:
            log.warning("operation failed: %s", e)
        finally:
            try:
                client.disconnect()
                client.destroy()
            except Exception:
                pass
        time.sleep(2)

if __name__ == "__main__":
    main()
