import json
import sys

NAMESPACES = ("mlflow", "argo-workflows")


def container_problems(container):
    state = container.get("state", {})
    last = container.get("lastState", {}).get("terminated", {})
    name = container["name"]
    if "waiting" in state:
        waiting = state["waiting"]
        return f"{name} waiting {waiting.get('reason')}: {waiting.get('message', '')[:200]}"
    terminated = state.get("terminated")
    if terminated and terminated.get("exitCode", 0) != 0:
        return f"{name} exited {terminated.get('exitCode')} {terminated.get('reason')}"
    if not container.get("ready") and container.get("restartCount", 0) > 0:
        return (
            f"{name} not ready, restarts={container['restartCount']}, "
            f"last exit={last.get('exitCode')} {last.get('reason')}"
        )
    return None


def main():
    lines = []
    for pod in json.load(sys.stdin)["items"]:
        meta, status = pod["metadata"], pod.get("status", {})
        if meta["namespace"] not in NAMESPACES:
            continue
        statuses = status.get("initContainerStatuses", []) + status.get("containerStatuses", [])
        problems = [p for p in map(container_problems, statuses) if p]
        for cond in status.get("conditions", []):
            if cond.get("type") == "PodScheduled" and cond.get("status") != "True":
                problems.append(f"unschedulable: {cond.get('message', '')[:200]}")
        if problems:
            lines.append(
                f"{meta['namespace']}/{meta['name']} ({status.get('phase')}): " + "; ".join(problems)
            )
    print("\n".join(lines) or "no unhealthy pods found")


if __name__ == "__main__":
    main()
