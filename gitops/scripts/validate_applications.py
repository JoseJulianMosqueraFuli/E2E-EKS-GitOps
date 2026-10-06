import argparse
import subprocess
from pathlib import Path

import yaml
from application_config import GITOPS_ROOT, generate_applications

CLUSTER_KINDS = {
    "Namespace",
    "CustomResourceDefinition",
    "ClusterRole",
    "ClusterRoleBinding",
    "ClusterSecretStore",
    "ConstraintTemplate",
    "PriorityClass",
    "ClusterServingRuntime",
    "ValidatingWebhookConfiguration",
    "MutatingWebhookConfiguration",
}


def validate_applications(gitops_root=GITOPS_ROOT, environment=None):
    root = Path(gitops_root)
    project = yaml.safe_load(
        (root / "applications/projects/mlops-core.yaml").read_text()
    )["spec"]
    applications = generate_applications(root)
    errors = []
    names = set()
    count = 0
    for app in applications:
        metadata, spec = app["metadata"], app["spec"]
        if metadata["name"] in names:
            errors.append(f"Duplicate application: {metadata['name']}")
        names.add(metadata["name"])
        if environment and metadata["labels"]["environment"] != environment:
            continue
        count += 1
        source = spec["source"]
        if source["repoURL"] not in project["sourceRepos"]:
            errors.append(f"Unauthorized repository: {source['repoURL']}")
        destination = spec["destination"]
        if not isinstance(spec["syncPolicy"]["automated"]["prune"], bool):
            errors.append(f"Invalid prune type: {metadata['name']}")
        if type(spec["revisionHistoryLimit"]) is not int:
            errors.append(f"Invalid revision history type: {metadata['name']}")
        overlay = (root / Path(source["path"]).relative_to("gitops")).resolve()
        if (
            not overlay.is_relative_to(root.resolve())
            or not (overlay / "kustomization.yaml").is_file()
        ):
            errors.append(f"Missing canonical overlay: {source['path']}")
            continue
        result = subprocess.run(
            ["kustomize", "build", str(overlay)],
            text=True,
            capture_output=True,
            timeout=60,
        )
        if result.returncode:
            errors.append(f"{metadata['name']}: {result.stderr.strip()}")
            continue
        for resource in yaml.safe_load_all(result.stdout):
            if not resource:
                continue
            kind = resource["kind"]
            group = (
                resource["apiVersion"].split("/")[0]
                if "/" in resource["apiVersion"]
                else ""
            )
            namespace = resource["metadata"].get("namespace", destination["namespace"])
            if not any(
                d.get("name") == destination.get("name") and d["namespace"] == namespace
                for d in project["destinations"]
            ):
                errors.append(f"{metadata['name']}: unauthorized namespace {namespace}")
            whitelist = project[
                "clusterResourceWhitelist"
                if kind in CLUSTER_KINDS
                else "namespaceResourceWhitelist"
            ]
            if not any(
                rule["group"] == group and rule["kind"] in (kind, "*")
                for rule in whitelist
            ):
                errors.append(
                    f"{metadata['name']}: unauthorized resource {group}/{kind}"
                )
            if kind == "ExternalSecret" and "secretStoreRef" not in resource["spec"]:
                errors.append(f"{metadata['name']}: missing secret store reference")
    if count == 0:
        errors.append(f"No applications generated for {environment}")
    return count, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", choices=["dev", "staging", "production"])
    args = parser.parse_args()
    count, errors = validate_applications(environment=args.environment)
    if errors:
        for error in errors:
            print(error)
        raise SystemExit(1)
    print(f"Validated {count} application overlays and AppProject permissions")


if __name__ == "__main__":
    main()
