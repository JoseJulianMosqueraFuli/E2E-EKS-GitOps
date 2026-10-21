import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CHAOS = ROOT / "gitops/applications/apps/chaos"
SCRIPTS = CHAOS / "workflows/scripts"

FAKE_COMMAND = r"""
import json
import os
import sys
from pathlib import Path

path = Path(os.environ["FAKE_STATE"])
state = json.loads(path.read_text())
command = Path(sys.argv[0]).name
args = [arg for arg in sys.argv[1:] if not arg.startswith("--request-timeout=")]
status = 0
output = ""
state.setdefault("calls", []).append([command, *args])
if command == "date":
    output = str(state["time"])
elif command == "sleep":
    state["time"] += state.get("sleep_step", int(args[0]))
elif command == "curl":
    down = state.get("fail_from", 0) <= state["time"] < state.get("fail_until", 0)
    state["time"] += 2 if down else 1
    output, status = ("000", 28) if down else ("200", 0)
    if not down and any("/runs/get" in arg for arg in args):
        value = "lost" if state["time"] >= state.get("lose_canary_at", 99999) else "test-workflow"
        output = json.dumps({"run": {"data": {"params": [{"key": "canary", "value": value}]}}})
    elif not down and os.environ.get("PROBE_BODY"):
        output = json.dumps(state.get("prediction", {"predictions": [1]}))
elif command == "kubectl":
    action, kind = args[:2]
    if action == "create" and kind == "configmap":
        state["marker"] = True
    elif action == "delete" and kind == "configmap":
        state["marker"] = False
    elif action == "get" and kind == "configmap":
        output = "configmap/probe-ready" if state.get("marker") else ""
    elif action == "get" and kind == "chaosengine":
        if state.get("api_error"):
            status = 1
        elif "name" in args:
            output = "chaosengine/test-engine"
        else:
            complete = state.get("stopped") or state["time"] >= state["complete_at"]
            output = json.dumps({"items": [{
                "metadata": {"name": "test-engine"},
                "status": {"engineStatus": "completed" if complete else "initialized"},
                "spec": {"experiments": [{"spec": {"components": {"env": [
                    {"name": "TARGET_NODE", "value": "target-node"}
                ]}}}]}
            }]})
    elif action == "patch" and kind.startswith("chaosengine/"):
        if state.get("stop_error"):
            status = 1
        else:
            state["stopped"] = True
    elif action == "wait":
        status = 1 if state.get("stop_error") else 0
    elif action == "get" and kind == "node":
        output = json.dumps({"spec": {"taints": state.get("taints", [])}})
    elif action == "get" and kind == "nodes":
        output = json.dumps({"items": state.get("nodes", [])})
    elif action == "get" and kind == "pods":
        output = json.dumps({"items": state.get("pods" if "--all-namespaces" in args else "control_pods", [])})
    elif action == "patch" and kind == "node":
        state["node_patch"] = json.loads(args[args.index("-p") + 1])
    else:
        raise RuntimeError(f"Unexpected kubectl arguments: {args}")
path.write_text(json.dumps(state))
if output:
    print(output)
sys.exit(status)
"""


@pytest.fixture
def shell(tmp_path):
    if not shutil.which("jq"):
        pytest.skip("jq is required for the workflow scripts")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("date", "sleep", "curl", "kubectl"):
        command = bin_dir / name
        command.write_text(f"#!{sys.executable}\n{FAKE_COMMAND}")
        command.chmod(0o755)

    def run(script, state=None, **variables):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"time": 1000, "complete_at": 1045, **(state or {})}))
        env = {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "FAKE_STATE": str(state_path),
            "CHAOS_SCRIPTS_DIR": str(SCRIPTS),
            "WORKFLOW_NAME": "test-workflow",
            "CHAOS_DURATION": "3",
            "MAX_DOWNTIME_SECONDS": "5",
            "EXPECTED_ENGINES": "1",
            "PROBE_URL": "http://service.test/health",
            "DOWNTIME_FILE": str(tmp_path / "downtime"),
            "CHAOS_STATE_DIR": str(tmp_path),
            **variables,
        }
        result = subprocess.run(
            ["sh", str(script)], env=env, capture_output=True, text=True, timeout=30
        )
        return result, json.loads(state_path.read_text())

    return run


def test_monitor_covers_delayed_fault_completion(shell, tmp_path):
    result, state = shell(SCRIPTS / "monitor.sh")
    assert result.returncode == 0, result.stderr
    assert state["time"] >= state["complete_at"] > 1000 + 3 + 30
    assert (tmp_path / "downtime").read_text().strip() == "0"
    assert state["marker"]


def test_slow_failed_requests_count_as_elapsed_seconds_and_stop_chaos(shell, tmp_path):
    result, state = shell(SCRIPTS / "monitor.sh", {"fail_from": 1002, "fail_until": 1100})
    assert result.returncode != 0
    assert "exceeds" in result.stderr
    assert int((tmp_path / "downtime").read_text()) >= 6
    assert state["stopped"]


@pytest.mark.parametrize(
    "variables",
    [
        {"PROBE_URL": ""},
        {"CHAOS_DURATION": "301"},
        {"CHAOS_DURATION": "08"},
        {"CHAOS_DURATION": "-1"},
        {"MAX_DOWNTIME_SECONDS": "abc"},
    ],
)
def test_invalid_parameters_never_signal_ready(shell, variables):
    result, state = shell(SCRIPTS / "monitor.sh", **variables)
    assert result.returncode != 0
    assert not state.get("marker")


def test_failed_baseline_prevents_injection(shell):
    result, state = shell(SCRIPTS / "monitor.sh", {"fail_from": 999, "fail_until": 1100})
    assert result.returncode != 0
    assert "baseline" in result.stderr
    assert not state.get("marker")


@pytest.mark.parametrize("state", [{"api_error": True}, {"complete_at": 999}])
def test_missing_observation_or_api_failure_cannot_pass(shell, state):
    result, _ = shell(SCRIPTS / "monitor.sh", state)
    assert result.returncode != 0


def test_monitor_times_out_and_stops_unfinished_fault(shell):
    result, state = shell(SCRIPTS / "monitor.sh", {"complete_at": 9999, "sleep_step": 60})
    assert result.returncode != 0
    assert "monitoring deadline" in result.stderr
    assert state["stopped"]


def test_cleanup_only_removes_this_workflows_taint(shell):
    own = {
        "key": "chaos.litmuschaos.io/az-failure",
        "value": "test-workflow",
        "effect": "NoExecute",
    }
    other = {**own, "value": "another-workflow"}
    result, state = shell(
        SCRIPTS / "cleanup.sh", {"taints": [other, own]}, CLEANUP_NODE_TAINTS="true"
    )
    assert result.returncode == 0, result.stderr
    assert state["node_patch"] == [
        {"op": "test", "path": "/spec/taints/1", "value": own},
        {"op": "remove", "path": "/spec/taints/1"},
    ]
    assert not state["marker"]


def test_cleanup_surfaces_stop_errors_instead_of_removing_taints(shell):
    result, state = shell(SCRIPTS / "cleanup.sh", {"stop_error": True}, CLEANUP_NODE_TAINTS="true")
    assert result.returncode != 0
    assert "node_patch" not in state


def node(name, zone, ready=True, unschedulable=False):
    return {
        "metadata": {"name": name, "labels": {"topology.kubernetes.io/zone": zone}},
        "spec": {"unschedulable": unschedulable},
        "status": {
            "conditions": [{"type": "Ready", "status": "True" if ready else "False"}],
            "allocatable": {"cpu": "2", "memory": "4Gi"},
        },
    }


@pytest.mark.parametrize(
    "failure",
    [
        "unconfirmed",
        "unready",
        "cordoned",
        "control-pod",
        "pvc",
        "cpu",
        "memory",
        "gpu",
        "missing-capacity",
        None,
    ],
)
def test_az_preflight_rejects_unsafe_targets(shell, tmp_path, failure):
    workflow = yaml.safe_load((CHAOS / "workflows/az-failure-test.yaml").read_text())
    preflight = next(t for t in workflow["spec"]["templates"] if t["name"] == "select-nodes")
    script = tmp_path / "preflight.sh"
    source = preflight["script"]["source"].replace("/chaos/", f"{SCRIPTS}/")
    script.write_text(source.replace("/tmp/", f"{tmp_path}/"))
    state = {
        "nodes": [
            node("target-node", "zone-a"),
            node("spare", "zone-b", failure != "unready", failure == "cordoned"),
        ],
        "control_pods": [{"spec": {"nodeName": "target-node"}}] if failure == "control-pod" else [],
    }
    if failure in ("pvc", "cpu", "memory", "gpu"):
        state["pods"] = [
            {
                "spec": {
                    "nodeName": "target-node",
                    "containers": [
                        {
                            "resources": {
                                "requests": {
                                    "cpu": "3" if failure == "cpu" else "1",
                                    "memory": "5Gi" if failure == "memory" else "1Gi",
                                    "nvidia.com/gpu": "1" if failure == "gpu" else "0",
                                }
                            }
                        }
                    ],
                    "volumes": [{"persistentVolumeClaim": {"claimName": "database"}}]
                    if failure == "pvc"
                    else [],
                }
            }
        ]
    if failure == "missing-capacity":
        del state["nodes"][1]["status"]["allocatable"]
    result, _ = shell(
        script,
        state,
        ZONE="zone-a",
        PROBE_BODY='{"instances":[[1,2]]}',
        PROBE_RESPONSE_FILTER=".predictions | length == 1",
        CONFIRM_ZONE_FAILURE="false" if failure == "unconfirmed" else "true",
    )
    assert (result.returncode == 0) == (failure is None), result.stdout + result.stderr


@pytest.mark.parametrize("environment", ["dev", "staging", "production"])
def test_rendered_chaos_workflows_have_safety_dependencies(environment):
    output = subprocess.check_output(
        ["kustomize", "build", str(CHAOS / "overlays" / environment)], text=True
    )
    resources = list(yaml.safe_load_all(output))
    workflows = [r for r in resources if r["kind"] == "WorkflowTemplate"]
    assert len(workflows) == (0 if environment == "production" else 2)
    assert not any(r["kind"] in ("ChaosEngine", "CronWorkflow") for r in resources)
    for workflow in workflows:
        spec = workflow["spec"]
        assert spec["synchronization"]["mutexes"] == [{"name": "chaos-experiments"}]
        config = next(
            r
            for r in resources
            if r["kind"] == "ConfigMap"
            and r["metadata"]["name"] == spec["volumes"][0]["configMap"]["name"]
        )
        assert config["metadata"]["namespace"] == workflow["metadata"]["namespace"]
        assert set(config["data"]) == {"common.sh", "monitor.sh", "cleanup.sh", "az-safety.sh"}
        injector = next(
            t for t in spec["templates"] if t["name"] in ("run-pod-delete", "run-node-taint")
        )
        source = injector["script"]["source"]
        assert source.index("wait_for_probe") < source.index("kubectl --request-timeout=10s create")


def test_network_partition_is_disabled_pending_isolation_validation():
    path = CHAOS / "experiments/pod-network-partition-kserve-mlflow.yaml"
    experiment = yaml.safe_load(path.read_text())
    assert experiment["spec"]["engineState"] == "stop"
    assert "REPLACE_WITH_MODEL_NAME" in experiment["spec"]["appinfo"]["applabel"]


def test_helm_post_renderers_remove_cluster_secret_access(tmp_path):
    releases = list(yaml.safe_load_all((CHAOS / "base/litmus.yaml").read_text()))
    fixtures = {
        "litmus-core": [
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "ClusterRole",
                "metadata": {"name": "litmus"},
                "rules": [
                    {
                        "apiGroups": [""],
                        "resources": ["replicationcontrollers", "secrets"],
                        "verbs": ["get", "list"],
                    }
                ],
            }
        ],
        "kubernetes-chaos": [
            {
                "apiVersion": "v1" if kind == "ServiceAccount" else "rbac.authorization.k8s.io/v1",
                "kind": kind,
                "metadata": {"name": "k8s-chaos-admin"},
            }
            for kind in ("ClusterRole", "ClusterRoleBinding", "ServiceAccount")
        ],
    }
    for release in releases:
        if release["kind"] != "HelmRelease":
            continue
        name = release["metadata"]["name"]
        directory = tmp_path / name
        directory.mkdir()
        (directory / "resources.yaml").write_text(yaml.safe_dump_all(fixtures[name]))
        config = {
            "apiVersion": "kustomize.config.k8s.io/v1beta1",
            "kind": "Kustomization",
            "resources": ["resources.yaml"],
            **release["spec"]["postRenderers"][0]["kustomize"],
        }
        (directory / "kustomization.yaml").write_text(yaml.safe_dump(config))
        output = subprocess.check_output(["kustomize", "build", str(directory)], text=True)
        rendered = list(yaml.safe_load_all(output))
        if name == "kubernetes-chaos":
            assert not rendered
        else:
            assert all("secrets" not in rule["resources"] for rule in rendered[0]["rules"])


@pytest.mark.parametrize("kind", ["canary", "prediction"])
def test_functional_probe_checks_data_not_only_http(shell, kind):
    if kind == "canary":
        result, state = shell(SCRIPTS / "monitor.sh", {"lose_canary_at": 1004}, CANARY_RUN_ID="run")
    else:
        result, state = shell(
            SCRIPTS / "monitor.sh",
            {"prediction": {"metadata": "model"}},
            PROBE_BODY='{"instances":[[1]]}',
            PROBE_RESPONSE_FILTER=".predictions | length == 1",
        )
    assert result.returncode != 0
    assert state["stopped"]


def test_prediction_probe_requires_a_response_assertion(shell):
    result, state = shell(SCRIPTS / "monitor.sh", PROBE_BODY='{"instances":[[1]]}')
    assert result.returncode != 0
    assert not state.get("marker")


def test_rendered_fault_roles_are_scoped_to_their_target_namespaces():
    resources = list(
        yaml.safe_load_all(
            subprocess.check_output(["kustomize", "build", str(CHAOS / "overlays/dev")], text=True)
        )
    )
    for namespace in ("mlflow", "kserve", "argocd"):
        role = next(
            r
            for r in resources
            if r["kind"] == "Role" and r["metadata"]["name"] == f"litmus-pod-{namespace}"
        )
        assert role["metadata"]["namespace"] == namespace
        assert not any(
            "nodes" in rule["resources"] or "secrets" in rule["resources"] for rule in role["rules"]
        )
    for binding in (r for r in resources if r["kind"] == "ClusterRoleBinding"):
        assert not any(
            s["name"]
            in (
                "litmus-pod-mlflow",
                "litmus-pod-kserve",
                "litmus-pod-argocd",
                "chaos-workflow-mlflow",
            )
            for s in binding["subjects"]
        )
