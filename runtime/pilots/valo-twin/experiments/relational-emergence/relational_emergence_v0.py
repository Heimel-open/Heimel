#!/usr/bin/env python3
"""Compatibility entrypoint.

v0 is deprecated because parser/interface failure could silently become a research zero.
This path now executes the self-validating v1.1 harness so old Colab commands fail safely.
"""
import relational_emergence_v1_1 as patched

if __name__ == "__main__":
    raise SystemExit(patched.base.main())
