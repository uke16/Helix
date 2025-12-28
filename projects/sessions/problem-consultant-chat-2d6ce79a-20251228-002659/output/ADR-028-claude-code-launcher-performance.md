---
adr_id: "028"
title: "Claude Code Launcher Performance - Pre-warmed Instance Pool"
status: Proposed

project_type: helix_internal
component_type: SERVICE
classification: NEW
change_scope: major

domain: helix
language: python
skills:
  - helix
  - infrastructure

files:
  create:
    - src/helix/launcher/__init__.py
    - src/helix/launcher/pool_manager.py
    - src/helix/launcher/instance.py
    - src/helix/launcher/health_monitor.py
    - control/claude-pool-daemon.sh
    - config/launcher-pool.yaml
  modify:
    - src/helix/claude_runner.py
    - src/helix/api/routes/openai.py
    - control/claude-wrapper.sh
  docs:
    - docs/ARCHITECTURE-MODULES.md
    - skills/helix/launcher/SKILL.md

depends_on:
  - ADR-000
  - ADR-003
---

# ADR-028: Claude Code Launcher Performance - Pre-warmed Instance Pool

## Status
📋 Proposed

## Kontext

### Das Problem

Das Starten einer neuen Claude Code Instanz dauert **10-20 Sekunden**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE STARTUP TIMELINE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  t=0s     Node.js Runtime laden                          ~2-3s              │
│  t=3s     Claude CLI initialisieren                      ~2-3s              │
│  t=6s     API-Verbindung aufbauen                        ~1-2s              │
│  t=8s     CLAUDE.md parsen                               ~1-2s              │
│  t=10s    MCP Server starten (optional)                  ~2-3s              │
│  t=12s    Erste Antwort beginnt                          ~3-5s              │
│           ─────────────────────────────────────────────────────             │
│  Total:   10-20 Sekunden bis erste Antwort                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**User Experience Impact:**
- Open WebUI zeigt lange "Thinking..." Phase
- Bei kurzen Fragen dauert der Start länger als die Antwort
- Gefühlte Langsamkeit trotz schneller Claude-Antworten

### Analyse der Startup-Kosten

| Phase | Zeit | Beschreibung |
|-------|------|--------------|
| Node.js Bootstrap | 2-3s | V8 Engine, Module laden |
| CLI Initialization | 2-3s | Argument parsing, Config loading |
| API Connection | 1-2s | HTTPS Handshake, Auth |
| Context Loading | 1-2s | CLAUDE.md, Projekt-Kontext |
| MCP Servers | 2-3s | Optional: Filesystem, Git MCP |
| **First Token** | 3-5s | Tatsächliche LLM-Antwort |

**Key Insight:** 70% der Zeit ist Startup-Overhead, nur 30% ist LLM-Arbeit.

### Untersuchte Alternativen

| Option | Beschreibung | Bewertung |
|--------|--------------|-----------|
| **RAM-Disk** | Node Modules auf tmpfs | -30% Startup, aber nur ~1-2s Gewinn |
| **Node.js Preload** | `node --require` mit Cache | Kompliziert, begrenzte Wirkung |
| **Instance Pool** | Vorgestartete Instanzen | ✅ Best Option: 90% Startup-Reduktion |
| **Lazy Loading** | MCP Server erst bei Bedarf | Nur ~2-3s Gewinn, nicht genug |

## Entscheidung

Wir implementieren einen **Pre-warmed Instance Pool** für Claude Code:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INSTANCE POOL ARCHITEKTUR                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     PoolManager (Daemon)                             │   │
│   │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │   │
│   │  • Startet beim Boot / API-Start                                     │   │
│   │  • Hält N warme Instanzen bereit (default: 2)                        │   │
│   │  • Ersetzt genutzte Instanzen sofort                                 │   │
│   │  • Health-Checks alle 30s                                            │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                            │                                                 │
│                            ▼                                                 │
│   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│   │   Instance #1    │  │   Instance #2    │  │   Instance #3    │          │
│   │   ────────────   │  │   ────────────   │  │   ────────────   │          │
│   │   Status: WARM   │  │   Status: WARM   │  │   Status: COLD   │          │
│   │   Age: 45s       │  │   Age: 12s       │  │   Age: 0s        │          │
│   │   PID: 12345     │  │   PID: 12346     │  │   Starting...    │          │
│   └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│                                                                              │
│   Request kommt rein:                                                        │
│   ─────────────────────                                                      │
│   1. Nimm WARM Instanz #1 (sofort verfügbar)                                │
│   2. Setze Arbeitsverzeichnis (chdir)                                        │
│   3. Sende Prompt via STDIN                                                  │
│   4. Starte neue Instanz #3 im Hintergrund                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Warum Instance Pool?

1. **Sofortige Verfügbarkeit**: Warme Instanz = 0s Startup
2. **Konstante Latenz**: Jeder Request hat gleiche Startzeit
3. **Ressourcen-Effizienz**: Nur N Instanzen laufen, nicht pro Request
4. **Graceful Degradation**: Fallback auf Cold-Start wenn Pool leer

### Design-Prinzipien

1. **Unix-Socket Kommunikation**: Schneller als TCP für lokale IPC
2. **Arbeitsverzeichnis-Wechsel**: `chdir` statt neuer Prozess
3. **STDIN/STDOUT Protokoll**: Kompatibel mit bestehendem ClaudeRunner
4. **Session Reset**: Kontext zwischen Requests leeren

## Implementation

### 1. Pool Manager

`src/helix/launcher/pool_manager.py`:

```python
"""Pre-warmed Claude Code Instance Pool Manager."""

import asyncio
import os
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncGenerator

from .instance import ClaudeInstance, InstanceState


class PoolManager:
    """Manages a pool of pre-warmed Claude Code instances.

    The PoolManager keeps N instances ready to handle requests
    immediately, eliminating startup latency.

    Example:
        pool = PoolManager(pool_size=2)
        await pool.start()

        # Get warm instance (near-instant)
        instance = await pool.acquire()
        result = await instance.execute(prompt, working_dir)
        await pool.release(instance)
    """

    def __init__(
        self,
        pool_size: int = 2,
        max_instance_age: int = 300,  # 5 minutes
        health_check_interval: int = 30,
        socket_dir: Path | None = None,
    ) -> None:
        self.pool_size = pool_size
        self.max_instance_age = max_instance_age
        self.health_check_interval = health_check_interval
        self.socket_dir = socket_dir or Path("/tmp/helix-claude-pool")

        self._instances: list[ClaudeInstance] = []
        self._available: asyncio.Queue[ClaudeInstance] = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._running = False
        self._health_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the pool manager and warm up instances."""
        self.socket_dir.mkdir(parents=True, exist_ok=True)
        self._running = True

        # Start initial instances
        await asyncio.gather(*[
            self._spawn_instance() for _ in range(self.pool_size)
        ])

        # Start health check loop
        self._health_task = asyncio.create_task(self._health_loop())

    async def stop(self) -> None:
        """Stop all instances and cleanup."""
        self._running = False

        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

        # Terminate all instances
        for instance in self._instances:
            await instance.terminate()

        self._instances.clear()

    async def acquire(self, timeout: float = 5.0) -> ClaudeInstance:
        """Acquire a warm instance from the pool.

        Args:
            timeout: Max time to wait for available instance.

        Returns:
            A ready-to-use ClaudeInstance.

        Raises:
            TimeoutError: If no instance available within timeout.
        """
        try:
            instance = await asyncio.wait_for(
                self._available.get(),
                timeout=timeout
            )

            # Spawn replacement immediately
            asyncio.create_task(self._spawn_instance())

            return instance

        except asyncio.TimeoutError:
            # Fallback: create cold instance
            return await self._create_cold_instance()

    async def release(self, instance: ClaudeInstance) -> None:
        """Release an instance back to the pool or terminate it.

        Instances are terminated after use (stateless model).
        A fresh instance is spawned to replace it.
        """
        await instance.terminate()
        # Replacement already spawned in acquire()

    async def _spawn_instance(self) -> None:
        """Spawn a new pre-warmed instance."""
        instance = ClaudeInstance(
            socket_path=self.socket_dir / f"claude-{len(self._instances)}.sock"
        )

        await instance.start()
        await instance.wait_ready()

        async with self._lock:
            self._instances.append(instance)

        await self._available.put(instance)

    async def _create_cold_instance(self) -> ClaudeInstance:
        """Create a cold (non-pooled) instance as fallback."""
        instance = ClaudeInstance(
            socket_path=self.socket_dir / f"claude-cold-{os.getpid()}.sock"
        )
        await instance.start()
        await instance.wait_ready()
        return instance

    async def _health_loop(self) -> None:
        """Periodically check instance health and replace stale ones."""
        while self._running:
            await asyncio.sleep(self.health_check_interval)

            async with self._lock:
                for instance in self._instances[:]:
                    # Check if instance is too old
                    if instance.age > self.max_instance_age:
                        await self._replace_instance(instance)

                    # Check if instance is healthy
                    elif not await instance.health_check():
                        await self._replace_instance(instance)

    async def _replace_instance(self, old: ClaudeInstance) -> None:
        """Replace an unhealthy or stale instance."""
        self._instances.remove(old)
        await old.terminate()
        await self._spawn_instance()

    def get_stats(self) -> dict:
        """Get pool statistics."""
        return {
            "pool_size": self.pool_size,
            "total_instances": len(self._instances),
            "available": self._available.qsize(),
            "instances": [
                {
                    "pid": i.pid,
                    "state": i.state.value,
                    "age": i.age,
                }
                for i in self._instances
            ]
        }
```

### 2. Claude Instance

`src/helix/launcher/instance.py`:

```python
"""Individual Claude Code Instance Management."""

import asyncio
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class InstanceState(Enum):
    """State of a Claude instance."""
    STARTING = "starting"
    WARM = "warm"
    BUSY = "busy"
    TERMINATED = "terminated"


@dataclass
class ExecutionResult:
    """Result from instance execution."""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration: float


class ClaudeInstance:
    """A single pre-warmed Claude Code instance.

    Uses a long-running Claude process that accepts commands
    via stdin and responds via stdout, avoiding startup overhead.
    """

    def __init__(
        self,
        socket_path: Path,
        claude_cmd: str = "/home/aiuser01/helix-v4/control/claude-wrapper.sh",
    ) -> None:
        self.socket_path = socket_path
        self.claude_cmd = claude_cmd

        self.state = InstanceState.STARTING
        self.pid: int | None = None
        self._process: asyncio.subprocess.Process | None = None
        self._created_at = time.time()

    @property
    def age(self) -> float:
        """Age of this instance in seconds."""
        return time.time() - self._created_at

    async def start(self) -> None:
        """Start the Claude process in warm-wait mode."""
        # Environment setup
        env = os.environ.copy()
        env["CLAUDE_POOL_MODE"] = "1"  # Signal to wrapper

        # Start process in interactive mode
        self._process = await asyncio.create_subprocess_exec(
            "stdbuf", "-oL", "-eL",
            self.claude_cmd,
            "--print",
            "--dangerously-skip-permissions",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        self.pid = self._process.pid

    async def wait_ready(self, timeout: float = 30.0) -> bool:
        """Wait for instance to become ready.

        The instance signals readiness by outputting a specific marker.
        """
        if not self._process or not self._process.stdout:
            return False

        try:
            # Wait for "READY" signal from Claude
            start = time.time()
            while time.time() - start < timeout:
                line = await asyncio.wait_for(
                    self._process.stdout.readline(),
                    timeout=1.0
                )
                if b"CLAUDE_READY" in line:
                    self.state = InstanceState.WARM
                    return True
        except asyncio.TimeoutError:
            pass

        return False

    async def execute(
        self,
        prompt: str,
        working_dir: Path,
        timeout: float = 600.0,
    ) -> ExecutionResult:
        """Execute a prompt in the given working directory.

        Args:
            prompt: The prompt to send to Claude.
            working_dir: Directory to execute in.
            timeout: Maximum execution time.

        Returns:
            ExecutionResult with output and status.
        """
        if not self._process or not self._process.stdin:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="Instance not started",
                exit_code=-1,
                duration=0,
            )

        self.state = InstanceState.BUSY
        start = time.time()

        # Send command with working directory
        command = f"CD:{working_dir}\nPROMPT:{prompt}\nEND_COMMAND\n"
        self._process.stdin.write(command.encode())
        await self._process.stdin.drain()

        # Collect output until END_RESPONSE marker
        stdout_lines = []
        stderr_lines = []

        try:
            while True:
                line = await asyncio.wait_for(
                    self._process.stdout.readline(),
                    timeout=timeout
                )

                if b"END_RESPONSE" in line:
                    break

                stdout_lines.append(line.decode("utf-8", errors="replace"))
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                stdout="".join(stdout_lines),
                stderr="Timeout",
                exit_code=-1,
                duration=time.time() - start,
            )

        self.state = InstanceState.WARM

        return ExecutionResult(
            success=True,
            stdout="".join(stdout_lines),
            stderr="".join(stderr_lines),
            exit_code=0,
            duration=time.time() - start,
        )

    async def health_check(self) -> bool:
        """Check if instance is still healthy."""
        if not self._process:
            return False

        return self._process.returncode is None

    async def terminate(self) -> None:
        """Terminate this instance."""
        self.state = InstanceState.TERMINATED

        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
```

### 3. Integration in ClaudeRunner

`src/helix/claude_runner.py` - Erweiterung:

```python
# Add to ClaudeRunner class

async def run_phase_pooled(
    self,
    phase_dir: Path,
    pool: "PoolManager",
    **kwargs,
) -> ClaudeResult:
    """Run phase using a pooled instance for faster startup.

    This method uses pre-warmed instances from the pool,
    reducing startup latency to near-zero.

    Args:
        phase_dir: Path to the phase directory.
        pool: PoolManager instance.
        **kwargs: Additional arguments.

    Returns:
        ClaudeResult with execution details.
    """
    import time
    start_time = time.time()

    prompt = kwargs.get("prompt")
    if prompt is None:
        claude_md = phase_dir / "CLAUDE.md"
        if claude_md.exists():
            prompt = "Read CLAUDE.md and execute all tasks described there."
        else:
            prompt = "Execute the phase tasks as defined in the spec."

    # Acquire warm instance
    instance = await pool.acquire()

    try:
        result = await instance.execute(
            prompt=prompt,
            working_dir=phase_dir,
            timeout=kwargs.get("timeout", self.DEFAULT_TIMEOUT),
        )

        return ClaudeResult(
            success=result.success,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_seconds=result.duration,
        )
    finally:
        await pool.release(instance)
```

### 4. Pool Daemon

`control/claude-pool-daemon.sh`:

```bash
#!/bin/bash
# claude-pool-daemon.sh - Starts and manages the instance pool
#
# Usage:
#   ./claude-pool-daemon.sh start
#   ./claude-pool-daemon.sh stop
#   ./claude-pool-daemon.sh status

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="/tmp/helix-claude-pool.pid"
LOG_FILE="$PROJECT_ROOT/logs/pool-daemon.log"

case "${1:-status}" in
    start)
        if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "Pool daemon already running (PID: $(cat "$PID_FILE"))"
            exit 0
        fi

        echo "Starting Claude instance pool..."
        python -m helix.launcher.daemon >> "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        echo "Pool daemon started (PID: $!)"
        ;;

    stop)
        if [[ -f "$PID_FILE" ]]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                echo "Stopping pool daemon (PID: $PID)..."
                kill "$PID"
                rm -f "$PID_FILE"
            else
                echo "Pool daemon not running"
                rm -f "$PID_FILE"
            fi
        else
            echo "Pool daemon not running"
        fi
        ;;

    status)
        if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "Pool daemon running (PID: $(cat "$PID_FILE"))"
            curl -s http://localhost:8001/helix/pool/stats 2>/dev/null || true
        else
            echo "Pool daemon not running"
        fi
        ;;

    *)
        echo "Usage: $0 {start|stop|status}"
        exit 1
        ;;
esac
```

### 5. Konfiguration

`config/launcher-pool.yaml`:

```yaml
# Claude Code Instance Pool Configuration

pool:
  # Number of warm instances to maintain
  size: 2

  # Maximum age before instance refresh (seconds)
  max_age: 300

  # Health check interval (seconds)
  health_check: 30

  # Socket directory for IPC
  socket_dir: /tmp/helix-claude-pool

startup:
  # Start pool with API server
  auto_start: true

  # Timeout for instance warmup (seconds)
  warmup_timeout: 30

fallback:
  # If pool empty, create cold instance
  allow_cold_start: true

  # Max cold instances before queueing
  max_cold_instances: 3
```

## Dokumentation

| Dokument | Änderung |
|----------|----------|
| `docs/ARCHITECTURE-MODULES.md` | Neue helix.launcher Section |
| `skills/helix/launcher/SKILL.md` | Neuer Skill für Pool-Management |
| `CLAUDE.md` | Hinweis auf Pool-Startup |

## Akzeptanzkriterien

### Performance

- [ ] Erste Antwort unter 3 Sekunden (statt 10-20s)
- [ ] Pool warmup in unter 60 Sekunden
- [ ] 90% der Requests nutzen warme Instanzen
- [ ] Fallback auf Cold-Start funktioniert

### Funktionalität

- [ ] PoolManager kann N Instanzen verwalten
- [ ] Health-Check erkennt tote Instanzen
- [ ] Arbeitsverzeichnis-Wechsel funktioniert
- [ ] Session-Isolation zwischen Requests

### Integration

- [ ] ClaudeRunner.run_phase_pooled() funktioniert
- [ ] API nutzt Pool automatisch wenn verfügbar
- [ ] Daemon kann via Script gesteuert werden
- [ ] Stats-Endpoint zeigt Pool-Status

### Tests

- [ ] Unit Tests für PoolManager
- [ ] Unit Tests für ClaudeInstance
- [ ] Integration Test: Pool Startup/Shutdown
- [ ] E2E Test: Request mit Pool vs Cold-Start

### Dokumentation

- [ ] ARCHITECTURE-MODULES.md aktualisiert
- [ ] Neuer Skill dokumentiert
- [ ] README erwähnt Pool-Feature

## Konsequenzen

### Vorteile

| Vorteil | Beschreibung |
|---------|--------------|
| **90% schneller** | Startup von 10-20s auf <1s |
| **Konstante Latenz** | Jeder Request gleich schnell |
| **Bessere UX** | Keine lange "Thinking..." Phase |
| **Ressourcen-effizient** | Nur N Instanzen statt N pro Request |

### Nachteile

| Nachteil | Mitigation |
|----------|------------|
| RAM-Verbrauch | Pool-Size konfigurierbar (default: 2) |
| Daemon-Management | Auto-Start mit API-Server |
| Komplexität | Fallback auf Cold-Start wenn Pool-Probleme |
| Session-Isolation | Stateless Model, Instance nach Use terminiert |

### Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Instance-Leak | Niedrig | Mittel | Health-Monitor, Max-Age |
| Pool-Erschöpfung | Niedrig | Niedrig | Fallback auf Cold-Start |
| Zombie-Prozesse | Niedrig | Mittel | PID-Tracking, Cleanup |

## Alternative: Einfache Lösung ohne Pool

Falls der Pool zu komplex ist, hier eine einfachere Alternative:

```python
# In claude_runner.py - Pre-check before each run

async def warm_claude_cli(self) -> None:
    """Pre-warm Claude CLI by running --version."""
    try:
        process = await asyncio.create_subprocess_exec(
            self.claude_cmd,
            "--version",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(process.wait(), timeout=10.0)
    except:
        pass
```

Diese einfache Variante cached zumindest Node.js und Claude CLI im OS-Cache.

## Referenzen

- Claude Code CLI Dokumentation
- Node.js Worker Threads (Alternative für Zukunft)
- Unix Domain Sockets für IPC
- Process Pooling Patterns (Gunicorn, uWSGI)
