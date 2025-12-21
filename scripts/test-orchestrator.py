#!/usr/bin/env python3
"""Test script for HELIX Orchestrator with live output."""

import asyncio
import os
import sys
from pathlib import Path

# Set NVM path for Node.js and Claude
os.environ["PATH"] = "/home/aiuser01/.nvm/versions/node/v20.19.6/bin:" + os.environ.get("PATH", "")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from helix.orchestrator import Orchestrator
from helix.claude_runner import ClaudeRunner
from helix.phase_loader import PhaseLoader
from helix.observability import HelixLogger


async def on_output(stream: str, line: str) -> None:
    """Callback for live output."""
    prefix = "OUT" if stream == "stdout" else "ERR"
    print(f"[{prefix}] {line}", flush=True)


async def main():
    project_dir = Path("/home/aiuser01/helix-v4/projects/external/config-validator")
    
    print("=" * 60, flush=True)
    print("HELIX Orchestrator E2E Test", flush=True)
    print("=" * 60, flush=True)
    print(f"Project: {project_dir}", flush=True)
    print(flush=True)
    
    # Load phases
    loader = PhaseLoader()
    phases = loader.load_phases(project_dir)
    
    print(f"Phases to execute: {len(phases)}", flush=True)
    for p in phases:
        print(f"  - {p.id}: {p.name}", flush=True)
    print(flush=True)
    
    # Create runner with streaming
    runner = ClaudeRunner(use_stdbuf=True)
    
    # Check Claude availability
    available = await runner.check_availability()
    if not available:
        print("❌ Claude CLI not available!", flush=True)
        return 1
    print("✅ Claude CLI available", flush=True)
    print(flush=True)
    
    # Run each phase
    for phase in phases:
        print("=" * 60, flush=True)
        print(f"Starting Phase: {phase.id} - {phase.name}", flush=True)
        print("=" * 60, flush=True)
        
        phase_dir = project_dir / "phases" / phase.id
        
        # Check CLAUDE.md exists
        claude_md = phase_dir / "CLAUDE.md"
        if not claude_md.exists():
            print(f"❌ No CLAUDE.md in {phase_dir}", flush=True)
            continue
        
        print(f"Working directory: {phase_dir}", flush=True)
        print(flush=True)
        
        # Run with streaming
        result = await runner.run_phase_streaming(
            phase_dir=phase_dir,
            on_output=on_output,
            timeout=600,  # 10 minutes per phase
        )
        
        print(flush=True)
        print("-" * 40, flush=True)
        print(f"Phase {phase.id} Result:", flush=True)
        print(f"  Success: {result.success}", flush=True)
        print(f"  Exit code: {result.exit_code}", flush=True)
        print(f"  Duration: {result.duration_seconds:.1f}s", flush=True)
        
        if not result.success:
            print(f"  Error: {result.stderr[:500]}", flush=True)
            print(flush=True)
            print("❌ Phase failed, stopping", flush=True)
            return 1
        
        print(flush=True)
    
    print("=" * 60, flush=True)
    print("✅ All phases completed successfully!", flush=True)
    print("=" * 60, flush=True)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
