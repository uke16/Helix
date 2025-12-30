"""MCP Hardware Server - Station control via FPGA + J-Link.

ADR-032: Phase 1 - Hardware Server

Provides MCP tools for controlling hardware test stations including:
- Station locking for exclusive access
- Connection management
- Debug operations (registers, memory, flash)
- Recovery from error states
"""
import asyncio
import sys
import time
from pathlib import Path

import httpx
import yaml
from fastmcp import FastMCP

from locking import locker
from audit import audit

mcp = FastMCP(
    name="helix-hardware",
    version="0.1.0",
)

_config = None


def load_config() -> dict:
    """Load station configuration from config.yaml."""
    global _config
    if _config is None:
        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path) as f:
            _config = yaml.safe_load(f)
    return _config


def get_station(name: str) -> dict:
    """Get configuration for a specific station.

    Args:
        name: Station name

    Returns:
        Station configuration dict

    Raises:
        ValueError: If station not found
    """
    config = load_config()
    station = config["stations"].get(name)
    if not station:
        available = list(config["stations"].keys())
        raise ValueError(f"Unknown station: {name}. Available: {available}")
    return station


# === Lock Tools ===

@mcp.tool
def station_acquire(station: str, session_id: str, timeout: int = 300) -> str:
    """Acquire exclusive access to a hardware test station.

    Args:
        station: Name of the station (e.g., 'station-alpha')
        session_id: Unique identifier for your session
        timeout: Lock timeout in seconds (default 300 = 5 minutes)

    Returns:
        Success message or lock conflict information
    """
    start = time.time()

    # Validate station exists
    try:
        get_station(station)
    except ValueError as e:
        return str(e)

    if locker.acquire(station, session_id, timeout):
        duration = int((time.time() - start) * 1000)
        audit.log(station, "acquire", session_id, "success", duration)
        return f"Lock acquired on {station} for {timeout}s"

    lock = locker.is_locked(station)
    if lock:
        return f"Station {station} locked by session {lock.session_id}"
    return f"Failed to acquire lock on {station}"


@mcp.tool
def station_release(station: str, session_id: str) -> str:
    """Release exclusive access to a hardware test station.

    Args:
        station: Name of the station
        session_id: Session that holds the lock

    Returns:
        Success or failure message
    """
    start = time.time()

    if locker.release(station, session_id):
        duration = int((time.time() - start) * 1000)
        audit.log(station, "release", session_id, "success", duration)
        return f"Lock released on {station}"

    lock = locker.is_locked(station)
    if lock:
        return f"Cannot release - locked by different session: {lock.session_id}"
    return f"Station {station} was not locked"


# === Station Tools ===

@mcp.tool
def list_stations() -> str:
    """List all available hardware test stations with their status.

    Returns:
        Formatted list of stations with descriptions and lock status
    """
    config = load_config()
    lines = ["Available stations:"]

    for name, station in config["stations"].items():
        lock = locker.is_locked(name)
        lock_status = f" [LOCKED by {lock.session_id}]" if lock else " [available]"
        desc = station.get("description", "No description")
        lines.append(f"  {name}: {desc}{lock_status}")

    return "\n".join(lines)


@mcp.tool
async def station_connect(station: str) -> str:
    """Connect to a station's debug target via J-Link.

    Args:
        station: Name of the station to connect to

    Returns:
        Connection status message
    """
    start = time.time()

    try:
        cfg = get_station(station)
    except ValueError as e:
        return str(e)

    fpga = cfg["fpga"]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"http://{fpga['host']}:{fpga['port']}/jlink/connect"
            )
            data = r.json()
    except httpx.TimeoutException:
        duration = int((time.time() - start) * 1000)
        audit.log(station, "connect", "unknown", "timeout", duration)
        return f"Timeout connecting to {station}"
    except httpx.ConnectError:
        duration = int((time.time() - start) * 1000)
        audit.log(station, "connect", "unknown", "network_error", duration)
        return f"Cannot reach {station} - check network/VPN"
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        audit.log(station, "connect", "unknown", "error", duration, {"error": str(e)})
        return f"Connection error: {e}"

    duration = int((time.time() - start) * 1000)
    stdout = data.get("stdout", "")

    if "Cortex-M33 identified" in stdout or "identified" in stdout.lower():
        audit.log(station, "connect", "unknown", "success", duration)
        return f"Connected to {station}"
    elif "0xFFFFFFFF" in stdout:
        audit.log(station, "connect", "unknown", "locked_target", duration)
        return f"Target locked. Use station_recover to power-cycle."

    audit.log(station, "connect", "unknown", "failed", duration)
    return f"Connection failed: {stdout[-300:]}"


@mcp.tool
async def station_recover(station: str) -> str:
    """Recover a station from error state by power-cycling the target.

    Args:
        station: Name of the station to recover

    Returns:
        Recovery status message
    """
    start = time.time()

    try:
        cfg = get_station(station)
    except ValueError as e:
        return str(e)

    fpga = cfg["fpga"]
    voltage = fpga.get("voltage", 3.3)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Power cycle
            await client.post(
                f"http://{fpga['host']}:{fpga['port']}/jlink/power",
                json={"action": "cycle", "voltage": voltage}
            )

            # Wait for target to stabilize
            await asyncio.sleep(0.5)

            # Reconnect
            r = await client.post(
                f"http://{fpga['host']}:{fpga['port']}/jlink/connect"
            )
            data = r.json()
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        audit.log(station, "recover", "unknown", "error", duration, {"error": str(e)})
        return f"Recovery failed: {e}"

    duration = int((time.time() - start) * 1000)
    stdout = data.get("stdout", "")

    if "Cortex-M33 identified" in stdout or "identified" in stdout.lower():
        audit.log(station, "recover", "unknown", "success", duration)
        return f"Recovery successful! {station} reconnected."

    audit.log(station, "recover", "unknown", "failed", duration)
    return "Recovery failed - target not responding"


@mcp.tool
async def station_registers(station: str) -> str:
    """Read CPU registers from the station's target.

    Args:
        station: Name of the station

    Returns:
        Formatted register values or error message
    """
    start = time.time()

    try:
        cfg = get_station(station)
    except ValueError as e:
        return str(e)

    fpga = cfg["fpga"]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"http://{fpga['host']}:{fpga['port']}/jlink/registers"
            )
            data = r.json()
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        audit.log(station, "registers", "unknown", "error", duration)
        return f"Error: {e}"

    duration = int((time.time() - start) * 1000)

    if not data.get("success"):
        audit.log(station, "registers", "unknown", "failed", duration)
        return f"Failed: {data.get('error')}"

    audit.log(station, "registers", "unknown", "success", duration)
    regs = data.get("registers", {})
    lines = [f"Registers on {station}:"]

    for name in ["PC", "SP", "LR", "R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7"]:
        if name in regs:
            lines.append(f"  {name}: 0x{regs[name]:08X}")

    return "\n".join(lines)


@mcp.tool
async def station_halt(station: str) -> str:
    """Halt the CPU on the station's target.

    Args:
        station: Name of the station

    Returns:
        Halt status message
    """
    try:
        cfg = get_station(station)
    except ValueError as e:
        return str(e)

    fpga = cfg["fpga"]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"http://{fpga['host']}:{fpga['port']}/jlink/halt"
            )
            data = r.json()
    except Exception as e:
        return f"Error: {e}"

    if data.get("success"):
        return f"CPU halted on {station}"
    return f"Halt failed: {data.get('error')}"


@mcp.tool
async def station_go(station: str) -> str:
    """Resume CPU execution on the station's target.

    Args:
        station: Name of the station

    Returns:
        Resume status message
    """
    try:
        cfg = get_station(station)
    except ValueError as e:
        return str(e)

    fpga = cfg["fpga"]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"http://{fpga['host']}:{fpga['port']}/jlink/go"
            )
            data = r.json()
    except Exception as e:
        return f"Error: {e}"

    if data.get("success"):
        return f"CPU running on {station}"
    return f"Resume failed: {data.get('error')}"


@mcp.tool
async def station_reset(station: str) -> str:
    """Reset the target MCU on a station.

    Args:
        station: Name of the station

    Returns:
        Reset status message
    """
    try:
        cfg = get_station(station)
    except ValueError as e:
        return str(e)

    fpga = cfg["fpga"]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"http://{fpga['host']}:{fpga['port']}/jlink/reset"
            )
            data = r.json()
    except Exception as e:
        return f"Error: {e}"

    if data.get("success"):
        return f"Target reset on {station}"
    return f"Reset failed: {data.get('error')}"


@mcp.tool
async def station_memory_read(
    station: str,
    address: str,
    length: int = 64
) -> str:
    """Read memory from the station's target.

    Args:
        station: Name of the station
        address: Memory address (hex string like '0x20000000')
        length: Number of bytes to read (default 64)

    Returns:
        Hex dump of memory or error message
    """
    try:
        cfg = get_station(station)
    except ValueError as e:
        return str(e)

    fpga = cfg["fpga"]

    # Parse address
    try:
        addr = int(address, 16) if address.startswith("0x") else int(address)
    except ValueError:
        return f"Invalid address format: {address}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"http://{fpga['host']}:{fpga['port']}/jlink/memory",
                params={"address": addr, "length": length}
            )
            data = r.json()
    except Exception as e:
        return f"Error: {e}"

    if not data.get("success"):
        return f"Read failed: {data.get('error')}"

    # Format as hex dump
    memory = bytes.fromhex(data.get("data", ""))
    lines = [f"Memory at 0x{addr:08X} ({len(memory)} bytes):"]

    for i in range(0, len(memory), 16):
        chunk = memory[i:i + 16]
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"  {addr + i:08X}: {hex_str:<48} {ascii_str}")

    return "\n".join(lines)


@mcp.tool
async def station_flash(
    station: str,
    firmware_path: str,
    verify: bool = True
) -> str:
    """Flash firmware to the station's target.

    Args:
        station: Name of the station
        firmware_path: Path to firmware file (.hex or .bin)
        verify: Whether to verify after flashing (default True)

    Returns:
        Flash status message
    """
    start = time.time()

    try:
        cfg = get_station(station)
    except ValueError as e:
        return str(e)

    fpga = cfg["fpga"]

    # Check file exists
    fw_path = Path(firmware_path)
    if not fw_path.exists():
        return f"Firmware file not found: {firmware_path}"

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            with open(fw_path, "rb") as f:
                r = await client.post(
                    f"http://{fpga['host']}:{fpga['port']}/jlink/flash",
                    files={"firmware": (fw_path.name, f)},
                    data={"verify": str(verify).lower()}
                )
                data = r.json()
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        audit.log(station, "flash", "unknown", "error", duration, {"error": str(e)})
        return f"Flash error: {e}"

    duration = int((time.time() - start) * 1000)

    if data.get("success"):
        audit.log(station, "flash", "unknown", "success", duration, {
            "firmware": fw_path.name,
            "verified": verify
        })
        return f"Firmware flashed to {station} ({duration}ms)"

    audit.log(station, "flash", "unknown", "failed", duration)
    return f"Flash failed: {data.get('error')}"


@mcp.tool
def station_audit_history(station: str, limit: int = 20) -> str:
    """Get recent audit history for a station.

    Args:
        station: Name of the station
        limit: Maximum number of entries (default 20)

    Returns:
        Formatted audit history
    """
    entries = audit.get_station_history(station, limit)

    if not entries:
        return f"No audit history for {station}"

    lines = [f"Audit history for {station} (last {len(entries)} entries):"]

    for entry in entries:
        ts = entry.get("timestamp", "")[:19]  # Trim to readable format
        op = entry.get("operation", "?")
        result = entry.get("result", "?")
        duration = entry.get("duration_ms", 0)
        lines.append(f"  {ts} | {op:12} | {result:10} | {duration}ms")

    return "\n".join(lines)


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "sse":
        mcp.run(transport="sse", host="0.0.0.0", port=8000)
    elif transport == "http":
        mcp.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")
    else:
        print(f"Unknown transport: {transport}")
        print("Usage: python server.py [stdio|sse|http]")
        sys.exit(1)
