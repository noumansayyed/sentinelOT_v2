"""Minimal OPC-UA server. Listens on 0.0.0.0:4840, one writable variable."""
import asyncio, logging
from asyncua import Server

logging.basicConfig(level=logging.INFO, format="%(asctime)s [OPC-UA-SRV] %(message)s")
log = logging.getLogger("opcua-server")

async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/otlab")
    server.set_server_name("otlab OPC-UA PLC")

    idx = await server.register_namespace("urn:otlab")
    objects = server.nodes.objects
    plc = await objects.add_object(idx, "PLC1")
    counter_var = await plc.add_variable(idx, "Counter", 0)
    await counter_var.set_writable()

    log.info("OPC-UA server listening on opc.tcp://0.0.0.0:4840/otlab")
    async with server:
        while True:
            await asyncio.sleep(2)
            val = await counter_var.read_value()
            await counter_var.write_value((val + 1) % 1000)

if __name__ == "__main__":
    asyncio.run(main())
