"""OPC-UA client. Reads/writes the Counter variable every 2 seconds."""
import asyncio, logging
from asyncua import Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [OPC-UA-HMI] %(message)s")
log = logging.getLogger("opcua-client")

async def try_connect():
    try:
        client = Client(url="opc.tcp://opcua-server:4840/otlab")
        await client.connect()
        return client
    except Exception as e:
        log.warning("connect failed: %s", e)
        return None

async def main():
    await asyncio.sleep(3)
    counter = 0
    while True:
        client = await try_connect()
        if client is None:
            log.warning("server not reachable, retrying in 3s")
            await asyncio.sleep(3)
            continue
        try:
            idx = await client.get_namespace_index("urn:otlab")
            obj = await client.nodes.objects.get_child([f"{idx}:PLC1"])
            var = await obj.get_child([f"{idx}:Counter"])

            counter = (counter + 1) % 1000
            await var.write_value(counter)
            read_back = await var.read_value()
            log.info("wrote Counter=%d, read back=%s", counter, read_back)
        except Exception as e:
            log.warning("operation failed: %s", e)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
