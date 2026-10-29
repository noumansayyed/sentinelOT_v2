"""Modbus TCP client. Writes to the PLC every 2 seconds, and reads back."""
import asyncio, logging
from pymodbus.client import AsyncModbusTcpClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [HMI] %(message)s")
log = logging.getLogger("modbus-client")

async def main():
    await asyncio.sleep(3)
    counter = 0
    while True:
        client = AsyncModbusTcpClient("modbus-plc", port=502, timeout=3)
        ok = False
        try:
            ok = await client.connect()
        except Exception as e:
            log.warning("connect raised: %s", e)
        if not ok:
            log.warning("PLC not reachable, retrying in 3s")
            try:
                client.close()
            except Exception:
                pass
            await asyncio.sleep(3)
            continue
        try:
            counter = (counter + 1) % 1000
            await client.write_register(address=10, value=counter, slave=1)
            await client.write_coil(address=5, value=(counter % 2 == 0), slave=1)
            rr = await client.read_holding_registers(address=10, count=1, slave=1)
            value = rr.registers[0] if not rr.isError() else "ERR"
            log.info("wrote HR[10]=%d, CO[5]=%s, read back HR[10]=%s",
                     counter, counter % 2 == 0, value)
        except Exception as e:
            log.warning("operation failed: %s", e)
        finally:
            try:
                client.close()
            except Exception:
                pass
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
