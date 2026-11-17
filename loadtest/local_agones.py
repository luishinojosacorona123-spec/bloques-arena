"""Mide reposición de la reserva de servidores en el clúster kind del laboratorio."""
import json
import subprocess
import sys
import time
from pathlib import Path


def main(config, evidence):
    def kubectl(*args):
        return subprocess.check_output(["kubectl", "--kubeconfig", config, *args], text=True)

    def snapshot(start):
        servers = json.loads(kubectl("get", "gameservers", "-o", "json"))["items"]
        states = [server["status"]["state"] for server in servers]
        return {
            "seconds": round(time.monotonic() - start, 2),
            "ready": states.count("Ready"),
            "allocated": states.count("Allocated"),
            "total": len(states),
        }

    root = Path(__file__).resolve().parents[1]
    kubectl("apply", "-f", str(root / "k8s/autoscaler.yaml"))
    start = time.monotonic()
    baseline = snapshot(start)
    rows = [baseline]
    for _ in range(baseline["ready"]):
        allocation = json.loads(kubectl("create", "-f", str(root / "k8s/allocation.yaml"), "-o", "json"))
        if allocation["status"]["state"] != "Allocated":
            raise RuntimeError(f"Asignación fallida: {allocation['status']['state']}")
    loaded = snapshot(start)
    rows.append(loaded)
    reaction = None
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        time.sleep(1)
        sample = snapshot(start)
        rows.append(sample)
        if sample["ready"] > loaded["ready"] or sample["ready"] and sample["total"] > baseline["total"]:
            reaction = round(sample["seconds"] - loaded["seconds"], 2)
            break
    result = {"scope": "Agones en kind, un nodo sin autoescalado de nodos",
              "seconds_until_new_ready_after_allocation_batch": reaction, "samples": rows}
    Path(evidence).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
