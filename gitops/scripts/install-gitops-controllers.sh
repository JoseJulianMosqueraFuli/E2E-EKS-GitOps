#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GITOPS_DIR="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${ENVIRONMENT:-dev}"
case "$ENVIRONMENT" in
  dev|staging|production) ;;
  prod) ENVIRONMENT=production ;;
  *) echo "Unsupported environment: $ENVIRONMENT" >&2; exit 1 ;;
esac

kc() {
  if [ -n "${KUBE_CONTEXT:-}" ]; then
    kubectl --context "$KUBE_CONTEXT" "$@"
  else
    kubectl "$@"
  fi
}

install_flux() {
  kc apply --server-side -k "$GITOPS_DIR/infrastructure/controllers/flux-system"
  for crd in gitrepositories.source.toolkit.fluxcd.io helmrepositories.source.toolkit.fluxcd.io helmreleases.helm.toolkit.fluxcd.io kustomizations.kustomize.toolkit.fluxcd.io; do
    kc wait --for=condition=Established "crd/$crd" --timeout=120s
  done
  for controller in source-controller kustomize-controller helm-controller notification-controller; do
    kc -n flux-system rollout status "deployment/$controller" --timeout=300s
  done
}

install_argocd() {
  kc apply --server-side -k "$GITOPS_DIR/infrastructure/controllers/argocd"
  for crd in applications.argoproj.io applicationsets.argoproj.io appprojects.argoproj.io; do
    kc wait --for=condition=Established "crd/$crd" --timeout=120s
  done
  for controller in argocd-server argocd-repo-server argocd-dex-server argocd-applicationset-controller; do
    kc -n argocd rollout status "deployment/$controller" --timeout=300s
  done
  kc -n argocd rollout status statefulset/argocd-application-controller --timeout=300s
}

verify_installation() {
  for controller in source-controller kustomize-controller helm-controller notification-controller; do
    kc -n flux-system rollout status "deployment/$controller" --timeout=60s
  done
  for controller in argocd-server argocd-repo-server argocd-dex-server argocd-applicationset-controller; do
    kc -n argocd rollout status "deployment/$controller" --timeout=60s
  done
  kc -n argocd rollout status statefulset/argocd-application-controller --timeout=60s
}

case "${1:-install}" in
  install)
    install_flux
    install_argocd
    verify_installation
    echo "Controllers ready. Configure cluster values, then run: ENVIRONMENT=$ENVIRONMENT $0 reconcile"
    ;;
  flux) install_flux ;;
  argocd) install_argocd ;;
  reconcile)
    kc -n flux-system get configmap platform-runtime-config >/dev/null
    kc apply -k "$GITOPS_DIR/infrastructure/clusters/$ENVIRONMENT/flux-system"
    kc -n flux-system wait --for=condition=Ready gitrepository/flux-system --timeout=180s
    kc -n flux-system wait --for=condition=Ready kustomization/flux-system --timeout=900s
    ;;
  verify) verify_installation ;;
  *) echo "Usage: $0 [install|flux|argocd|reconcile|verify]" >&2; exit 1 ;;
esac
