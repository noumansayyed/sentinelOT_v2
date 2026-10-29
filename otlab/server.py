"""Minimal Modbus TCP server. Listens on 0.0.0.0:502."""
import asyncio, logging
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.server import StartAsyncTcpServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [PLC] %(message)s")
log = logging.getLogger("modbus-plc")

async def main():
    # 100 holding registers, 100 coils, both starting at 0, initialized to 0
    block = ModbusSequentialDataBlock(0, [0] * 100)
    ctx = ModbusSlaveContext(hr=block, co=block, di=block, ir=block, zero_mode=True)
    server = ModbusServerContext(slaves=ctx, single=True)
    log.info("Modbus TCP server listening on 0.0.0.0:502")
    await StartAsyncTcpServer(context=server, address=("0.0.0.0", 502))

if __name__ == "__main__":
    asyncio.run(main())
