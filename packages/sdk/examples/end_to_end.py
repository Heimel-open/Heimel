"""Executable offline demo: python packages/sdk/examples/end_to_end.py"""

import json

from valo_sdk.demo import run_demo


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2, default=str))
