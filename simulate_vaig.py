#!/usr/bin/env python3
"""Backward-compatibility shim. Use: python simulate.py --mode vaig"""
import subprocess, sys
sys.exit(subprocess.run(
    [sys.executable, "simulate.py", "--mode", "vaig"] + sys.argv[1:]
).returncode)
