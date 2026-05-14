"""
Notification module for GitOps promotion pipeline.

Sends notifications to Slack, email, and updates documentation
when promotions occur.
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class PromotionEvent:
    """Represents a promotion event for notification."""
    source_env: str
    target_env: str
    status: str  # success, failure, pending
    changes: List[str]
    promoted_by: str = "Automated Pipeline"
    timestamp: Optional[str] = None
    pr_url: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class SlackNotifier:
    """Sends notifications to Slack."""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL", "")

    def send_promotion_notification(self, event: PromotionEvent) -> bool:
        """Send promotion notification to Slack."""
        if not self.webhook_url:
            return False

        color = {
            "success": "#36a64f",
            "failure": "#ff0000",
            "pending": "#ffaa00",
        }.get(event.status, "#808080")

        emoji = {
            "success": "✅",
            "failure": "❌",
            "pending": "⏳",
        }.get(event.status, "📋")

        changes_text = "\n".join(f"• {c}" for c in event.changes[:10])
        if len(event.changes) > 10:
            changes_text += f"\n• ... and {len(event.changes) - 10} more"

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"{emoji} GitOps Promotion: {event.source_env} → {event.target_env}",
                    "fields": [
                        {
                            "title": "Status",
                            "value": event.status.upper(),
                            "short": True,
                        },
                        {
                            "title": "Promoted By",
                            "value": event.promoted_by,
                            "short": True,
                        },
                        {
                            "title": "Timestamp",
                            "value": event.timestamp,
                            "short": True,
                        },
                    ],
                    "text": f"**Changes:**\n{changes_text}",
                    "footer": "MLOps GitOps Platform",
                }
            ]
        }

        if event.pr_url:
            payload["attachments"][0]["fields"].append({
                "title": "Pull Request",
                "value": event.pr_url,
                "short": False,
            })

        try:
            import urllib.request
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req) as response:
                return response.status == 200
        except Exception:
            return False


class DocumentationUpdater:
    """Updates deployment documentation after promotions."""

    def __init__(self, docs_path: Optional[Path] = None):
        self.docs_path = docs_path or Path(__file__).parent.parent.parent.parent / "docs"

    def update_deployment_log(self, event: PromotionEvent) -> str:
        """Update the deployment log with the promotion event."""
        log_file = self.docs_path / "deployment-log.md"

        entry = f"""
### {event.timestamp} - {event.source_env} → {event.target_env}

- **Status**: {event.status}
- **Promoted by**: {event.promoted_by}
- **Changes**: {len(event.changes)} files updated

"""
        if event.status == "success":
            entry += "✅ Promotion completed successfully.\n"
        elif event.status == "failure":
            entry += "❌ Promotion failed. Check CI/CD logs for details.\n"
        else:
            entry += "⏳ Promotion pending approval.\n"

        if not log_file.exists():
            log_file.parent.mkdir(parents=True, exist_ok=True)
            log_file.write_text("# Deployment Log\n\n")

        with open(log_file, "r") as f:
            existing = f.read()

        # Insert new entry after the header
        header_end = existing.find("\n\n", existing.find("# Deployment Log"))
        if header_end == -1:
            header_end = len(existing)

        updated = existing[:header_end] + entry + existing[header_end:]
        log_file.write_text(updated)

        return str(log_file)

    def update_status_dashboard(self, event: PromotionEvent) -> str:
        """Update the status dashboard with current environment state."""
        dashboard_file = self.docs_path / "environment-status.md"

        status_emoji = {
            "success": "🟢",
            "failure": "🔴",
            "pending": "🟡",
        }.get(event.status, "⚪")

        # Read existing dashboard or create new one
        if dashboard_file.exists():
            content = dashboard_file.read_text()
        else:
            content = """# Environment Status Dashboard

| Environment | Status | Last Updated | Last Promotion |
|-------------|--------|--------------|----------------|
| dev         | 🟢     | -            | -              |
| staging     | ⚪     | -            | -              |
| production  | ⚪     | -            | -              |

"""

        # Update the table row for the target environment
        timestamp = event.timestamp.split(" ")[0] if event.timestamp else "-"
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith(f"| {event.target_env}"):
                lines[i] = f"| {event.target_env} | {status_emoji} | {timestamp} | {event.source_env} → {event.target_env} |"
                break

        dashboard_file.write_text("\n".join(lines))
        return str(dashboard_file)


def notify_promotion(event: PromotionEvent) -> Dict[str, bool]:
    """Send all notifications for a promotion event."""
    results = {}

    # Slack notification
    slack = SlackNotifier()
    results["slack"] = slack.send_promotion_notification(event)

    # Documentation updates
    docs = DocumentationUpdater()
    results["deployment_log"] = bool(docs.update_deployment_log(event))
    results["status_dashboard"] = bool(docs.update_status_dashboard(event))

    return results


if __name__ == "__main__":
    # Example usage
    event = PromotionEvent(
        source_env="dev",
        target_env="staging",
        status="success",
        changes=[
            "Updated mlflow-staging ArgoCD Application",
            "Updated kubeflow-staging ArgoCD Application",
            "Updated kserve-staging ArgoCD Application",
            "Updated monitoring-staging ArgoCD Application",
        ],
    )

    results = notify_promotion(event)
    print("Notification results:")
    for channel, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {channel}")
