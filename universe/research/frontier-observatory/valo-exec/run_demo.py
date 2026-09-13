import json
import sys
from engine import evaluate

def run(path: str):
    with open(path) as f:
        request = json.load(f)

    print("INPUT:")
    print(json.dumps(request, indent=2))
    print()

    result = evaluate(request)

    print("VALO EXEC DECISION:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "agent_request_nordbank.json"
    run(path)
