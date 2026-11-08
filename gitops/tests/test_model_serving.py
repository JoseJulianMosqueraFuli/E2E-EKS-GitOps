import subprocess
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import pytest
import yaml

from .application_helpers import generate_applications

ROOT = Path(__file__).resolve().parents[2]
APPS = ROOT / "gitops/applications/apps"
KSERVE = APPS / "kserve"
MODEL_SERVING = APPS / "model-serving"
CERT_MANAGER = ROOT / "gitops/infrastructure/addons/cert-manager"
KSERVE_VERSION = "v0.21.0"
CERT_MANAGER_VERSION = "v1.21.3"
ALLOWED_KINDS = {"Namespace", "HelmRepository", "HelmRelease", "NetworkPolicy"}
ROLLOUT_ANNOTATION = "mlops-platform/model-version"


@lru_cache(maxsize=None)
def _render(path):
    output = subprocess.check_output(["kustomize", "build", path], text=True)
    return tuple(doc for doc in yaml.safe_load_all(output) if doc)


def render(path):
    return list(_render(str(path)))


PREFIXES = {"dev": "dev-", "staging": "staging-", "production": "prod-"}


def by_name(resources, kind, name):
    return next(r for r in resources if r["kind"] == kind and r["metadata"]["name"] == name)


@pytest.fixture(scope="module", params=sorted(PREFIXES))
def kserve(request):
    prefix = PREFIXES[request.param]
    resources = render(KSERVE / "overlays" / request.param)
    return lambda kind, name: by_name(resources, kind, prefix + name), resources, prefix


def test_kserve_is_installed_from_pinned_charts_only(kserve):
    get, resources, prefix = kserve
    assert {r["kind"] for r in resources} <= ALLOWED_KINDS
    assert get("HelmRepository", "kserve")["spec"] == {
        "type": "oci",
        "interval": "1h",
        "url": "oci://ghcr.io/kserve/charts",
    }
    charts = {
        name: get("HelmRelease", name)["spec"]["chart"]["spec"] for name in ("kserve-crd", "kserve")
    }
    assert charts["kserve-crd"]["chart"] == "kserve-crd"
    assert charts["kserve"]["chart"] == "kserve-resources"
    assert {chart["version"] for chart in charts.values()} == {KSERVE_VERSION}
    assert {chart["sourceRef"]["name"] for chart in charts.values()} == {prefix + "kserve"}


def test_kserve_uses_standard_mode_without_ingress(kserve):
    get, _, prefix = kserve
    release = get("HelmRelease", "kserve")
    controller = release["spec"]["values"]["kserve"]["controller"]
    assert controller["deploymentMode"] == "Standard"
    assert controller["gateway"]["disableIngressCreation"] is True
    assert {"name": prefix + "kserve-crd"} in release["spec"]["dependsOn"]
    assert {
        get("HelmRelease", name)["spec"]["releaseName"] for name in ("kserve-crd", "kserve")
    } == {
        "kserve-crd",
        "kserve",
    }


def test_kserve_waits_for_the_cert_manager_addon(kserve):
    get, _, _ = kserve
    addon = by_name(render(CERT_MANAGER), "HelmRelease", "cert-manager")
    dependency = {"name": addon["metadata"]["name"], "namespace": addon["metadata"]["namespace"]}
    assert dependency in get("HelmRelease", "kserve")["spec"]["dependsOn"]


def test_cert_manager_is_pinned_and_installs_its_crds():
    addon = by_name(render(CERT_MANAGER), "HelmRelease", "cert-manager")
    chart = addon["spec"]["chart"]["spec"]
    assert chart["version"] == CERT_MANAGER_VERSION
    assert addon["spec"]["values"]["crds"] == {"enabled": True, "keep": True}
    sources = yaml.safe_load_all(
        (ROOT / "gitops/infrastructure/sources/helm-repository.yaml").read_text()
    )
    names = {(s["metadata"]["name"], s["metadata"]["namespace"]) for s in sources if s}
    assert (chart["sourceRef"]["name"], chart["sourceRef"]["namespace"]) in names
    addons = yaml.safe_load((CERT_MANAGER.parent / "kustomization.yaml").read_text())
    assert "cert-manager" in addons["resources"]


@pytest.fixture(scope="module", params=sorted(PREFIXES))
def serving(request):
    env = request.param
    resources = render(MODEL_SERVING / "overlays" / env)
    service = by_name(resources, "InferenceService", "default-model")
    return env, resources, service


def predictor_container(service):
    (container,) = service["spec"]["predictor"]["containers"]
    return container


def workflow_template(env, name):
    return by_name(render(APPS / "argo-workflows/overlays" / env), "WorkflowTemplate", name)


def templates_of(workflow):
    return {t["name"]: t for t in workflow["spec"]["templates"]}


def test_model_serving_is_an_argocd_app_in_every_environment():
    applications = {
        a["metadata"]["name"]: a
        for a in generate_applications()
        if a["metadata"]["labels"]["app.kubernetes.io/name"] == "model-serving"
    }
    assert set(applications) == {f"model-serving-{env}" for env in PREFIXES}
    for application in applications.values():
        assert application["spec"]["destination"]["namespace"] == "models"


def test_inference_service_serves_the_champion_with_the_pipeline_image(serving):
    env, _, service = serving
    container = predictor_container(service)
    name = service["metadata"]["name"]
    assert service["metadata"]["namespace"] == "models"
    assert container["args"] == [
        "step",
        "serve",
        "--model-name",
        name,
        "--alias",
        "champion",
        "--port",
        "8080",
    ]
    training = templates_of(workflow_template(env, "model-training-template"))
    assert container["image"] == training["train-model-step"]["container"]["image"]
    assert "AWS_" not in container["image"]


def test_inference_service_tracks_the_environment_mlflow(serving):
    env, _, service = serving
    env_vars = {e["name"]: e["value"] for e in predictor_container(service)["env"]}
    tracking = urlparse(env_vars["MLFLOW_TRACKING_URI"])
    mlflow = next(
        r
        for r in render(APPS / "mlflow/overlays" / env)
        if r["kind"] == "Service" and r["metadata"]["name"] == PREFIXES[env] + "mlflow-server"
    )
    assert tracking.hostname == f"{mlflow['metadata']['name']}.{mlflow['metadata']['namespace']}"
    assert tracking.port in {port["port"] for port in mlflow["spec"]["ports"]}


def test_rollouts_keep_the_serving_replica_until_the_new_one_is_ready(serving):
    env, _, service = serving
    predictor = service["spec"]["predictor"]
    assert predictor["deploymentStrategy"] == {
        "type": "RollingUpdate",
        "rollingUpdate": {"maxUnavailable": 0, "maxSurge": 1},
    }
    assert predictor_container(service)["readinessProbe"]["httpGet"] == {
        "path": "/ping",
        "port": 8080,
    }
    assert predictor["minReplicas"] == (2 if env == "production" else 1)


def test_git_leaves_the_rollout_annotation_to_the_pipeline(serving):
    _, _, service = serving
    assert ROLLOUT_ANNOTATION not in service["spec"]["predictor"].get("annotations", {})
    assert ROLLOUT_ANNOTATION not in service["metadata"].get("annotations", {})


def test_predictor_container_is_restricted(serving):
    _, _, service = serving
    security = predictor_container(service)["securityContext"]
    assert security["runAsNonRoot"] is True
    assert security["readOnlyRootFilesystem"] is True
    assert security["allowPrivilegeEscalation"] is False
    assert security["capabilities"] == {"drop": ["ALL"]}
    assert security["seccompProfile"] == {"type": "RuntimeDefault"}


def test_predictors_run_without_api_credentials(serving):
    _, resources, service = serving
    account = by_name(
        resources, "ServiceAccount", service["spec"]["predictor"]["serviceAccountName"]
    )
    assert account["metadata"]["namespace"] == "models"
    assert account["automountServiceAccountToken"] is False
    assert not [r for r in resources if r["kind"] == "Secret"]


def namespace_selectors(policy):
    rules = policy["spec"].get("ingress", []) + policy["spec"].get("egress", [])
    for rule in rules:
        for peer in rule.get("from", []) + rule.get("to", []):
            if "namespaceSelector" in peer:
                yield peer["namespaceSelector"]["matchLabels"]


@pytest.mark.parametrize("app", [KSERVE, MODEL_SERVING], ids=["kserve", "model-serving"])
@pytest.mark.parametrize("env", sorted(PREFIXES))
def test_network_policies_select_namespaces_by_their_builtin_label(app, env):
    policies = [r for r in render(app / "overlays" / env) if r["kind"] == "NetworkPolicy"]
    assert policies
    for policy in policies:
        for labels in namespace_selectors(policy):
            assert list(labels) == ["kubernetes.io/metadata.name"], policy["metadata"]["name"]


def test_predictors_only_reach_mlflow_its_artifact_gateway_and_dns(serving):
    _, resources, _ = serving
    policy = by_name(resources, "NetworkPolicy", "model-predictors")
    assert policy["metadata"]["namespace"] == "models"
    assert policy["spec"]["podSelector"] == {
        "matchExpressions": [{"key": "serving.kserve.io/inferenceservice", "operator": "Exists"}]
    }
    egress = {
        (
            rule["to"][0]["namespaceSelector"]["matchLabels"]["kubernetes.io/metadata.name"],
            port["port"],
        )
        for rule in policy["spec"]["egress"]
        for port in rule["ports"]
    }
    assert egress == {("mlflow", 5000), ("mlflow", 9000), ("kube-system", 53)}
    ingress_ports = {port["port"] for rule in policy["spec"]["ingress"] for port in rule["ports"]}
    assert ingress_ports == {8080}


IN_CLUSTER_ARTIFACT_STORES = {
    "dev": APPS / "mlflow/overlays/dev",
    "staging": APPS / "mlflow/overlays/staging",
    "kind": ROOT / "scripts/e2e/kind/mlflow",
}


@pytest.mark.parametrize("store", sorted(IN_CLUSTER_ARTIFACT_STORES))
def test_predictors_reach_the_gateway_mlflow_signs_download_urls_for(store):
    env = "dev" if store == "kind" else store
    prefix = PREFIXES[env]
    mlflow = render(IN_CLUSTER_ARTIFACT_STORES[store])
    config = by_name(mlflow, "ConfigMap", prefix + "mlflow-config")
    endpoint = urlparse(config["data"]["s3_endpoint_url"])
    service_name, namespace = endpoint.hostname.split(".")[:2]
    service = by_name(mlflow, "Service", service_name)
    (target,) = [p["targetPort"] for p in service["spec"]["ports"] if p["port"] == endpoint.port]
    gateway = next(
        r
        for r in mlflow
        if r["kind"] == "Deployment"
        and service["spec"]["selector"].items()
        <= r["spec"]["template"]["metadata"]["labels"].items()
    )
    pod_labels = gateway["spec"]["template"]["metadata"]["labels"]
    (port,) = [
        p["containerPort"]
        for c in gateway["spec"]["template"]["spec"]["containers"]
        for p in c.get("ports", [])
        if target in (p.get("name"), p["containerPort"])
    ]

    predictors = by_name(
        render(MODEL_SERVING / "overlays" / env), "NetworkPolicy", "model-predictors"
    )
    assert any(
        {"protocol": "TCP", "port": port} in rule["ports"]
        and any(
            peer["namespaceSelector"]["matchLabels"] == {"kubernetes.io/metadata.name": namespace}
            and peer.get("podSelector", {}).get("matchLabels", {}).items() <= pod_labels.items()
            for peer in rule["to"]
        )
        for rule in predictors["spec"]["egress"]
    )

    gateway_policy = by_name(mlflow, "NetworkPolicy", prefix + "mlflow-network-policy")
    assert gateway_policy["spec"]["podSelector"]["matchLabels"].items() <= pod_labels.items()
    from_models = {"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "models"}}}
    assert any(
        {"protocol": "TCP", "port": port} in rule["ports"] and from_models in rule["from"]
        for rule in gateway_policy["spec"]["ingress"]
    )


@pytest.fixture(scope="module", params=sorted(PREFIXES))
def deployment(request):
    workflow = workflow_template(request.param, "model-deployment-template")
    templates = templates_of(workflow)
    tasks = {t["name"]: t for t in templates["model-deployment"]["dag"]["tasks"]}
    return workflow, templates, tasks


def arguments(task):
    return {p["name"]: p["value"] for p in task["arguments"]["parameters"]}


def test_pipeline_defaults_target_the_declared_inference_service(deployment):
    workflow, _, _ = deployment
    declared = by_name(render(MODEL_SERVING / "base"), "InferenceService", "default-model")
    defaults = {p["name"]: p["value"] for p in workflow["spec"]["arguments"]["parameters"]}
    assert defaults["model-name"] == declared["metadata"]["name"]
    assert defaults["deployment-namespace"] == declared["metadata"]["namespace"]
    assert defaults["previous-version"] == ""


def test_roll_out_patches_the_version_annotation_without_building_images(deployment):
    _, templates, tasks = deployment
    step = templates["roll-out-step"]
    assert step["resource"]["action"] == "patch"
    assert step["resource"]["mergeStrategy"] == "merge"
    patch = yaml.safe_load(step["resource"]["manifest"])
    assert patch["kind"] == "InferenceService"
    assert patch["metadata"] == {
        "name": "{{inputs.parameters.model-name}}",
        "namespace": "{{inputs.parameters.deployment-namespace}}",
    }
    assert patch["spec"] == {
        "predictor": {"annotations": {ROLLOUT_ANNOTATION: "{{inputs.parameters.model-version}}"}}
    }
    assert arguments(tasks["roll-out"])["model-version"] == "{{inputs.parameters.model-version}}"
    assert not any("initContainers" in t for t in templates.values())


def test_verification_requires_the_rolled_out_version_and_registry_parity(deployment):
    _, templates, tasks = deployment
    args = templates["validate-deployment-step"]["container"]["args"]
    options = dict(zip(args[2::2], args[3::2]))
    url = urlparse(options["--url"])
    assert url.hostname == (
        "{{inputs.parameters.model-name}}-predictor."
        "{{inputs.parameters.deployment-namespace}}.svc.cluster.local"
    )
    assert url.path == "/invocations"
    assert options["--expected-version"] == "{{inputs.parameters.model-version}}"
    assert options["--model-uri"] == (
        "models:/{{inputs.parameters.model-name}}/{{inputs.parameters.model-version}}"
    )
    assert options["--timeout"] == "{{inputs.parameters.timeout}}"
    for name in ("verify", "verify-rollback"):
        assert arguments(tasks[name])["timeout"] == "{{inputs.parameters.verification-timeout}}"
    assert tasks["verify"]["depends"] == "roll-out"


def test_failed_gate_restores_the_previous_champion_and_fails(deployment):
    _, templates, tasks = deployment
    assert templates["model-deployment"]["dag"]["failFast"] is False
    restore = tasks["restore-champion"]
    assert set(restore["depends"].split(" || ")) == {
        "roll-out.Failed",
        "roll-out.Errored",
        "verify.Failed",
        "verify.Errored",
    }
    assert restore["template"] == "set-alias-step"
    assert arguments(restore)["version"] == "{{inputs.parameters.previous-version}}"
    for name in ("roll-back", "verify-rollback"):
        assert arguments(tasks[name])["model-version"] == "{{inputs.parameters.previous-version}}"
        assert tasks[name]["when"] == "'{{inputs.parameters.previous-version}}' != ''"
    assert tasks["roll-back"]["depends"] == "restore-champion"
    assert tasks["verify-rollback"]["depends"] == "roll-back"
    assert tasks["reject-candidate"]["depends"].startswith("restore-champion.Succeeded")
    assert templates["reject-candidate-step"]["container"]["args"][0].endswith("exit 1")


def test_training_hands_the_replaced_champion_to_deployment():
    for env in PREFIXES:
        training = templates_of(workflow_template(env, "model-training-template"))
        register = training["register-model-step"]["outputs"]["parameters"]
        assert {
            "name": "previous-version",
            "valueFrom": {
                "path": "/tmp/previous-version.txt",
                "default": "",
            },
        } in register
        outputs = {p["name"] for p in training["model-training"]["outputs"]["parameters"]}
        assert "previous-version" in outputs
        pipeline = templates_of(workflow_template(env, "ml-pipeline-template"))
        deploy = next(
            t for t in pipeline["ml-pipeline"]["dag"]["tasks"] if t["name"] == "model-deployment"
        )
        assert arguments(deploy)["previous-version"] == (
            "{{tasks.model-training.outputs.parameters.previous-version}}"
        )


def test_pipeline_may_only_read_and_patch_inference_services():
    roles = [
        r
        for r in render(APPS / "argo-workflows/overlays/dev")
        if r["kind"] == "Role" and r["metadata"]["namespace"] == "models"
    ]
    assert [rule for role in roles for rule in role["rules"]] == [
        {
            "apiGroups": ["serving.kserve.io"],
            "resources": ["inferenceservices"],
            "verbs": ["get", "patch"],
        }
    ]
