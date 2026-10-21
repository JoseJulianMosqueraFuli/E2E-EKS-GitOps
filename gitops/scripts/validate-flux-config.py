import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
expected = {
    line.split("=", 1)[0]
    for line in (root / "platform/flux.env.example").read_text().splitlines()
    if "=" in line
}
if sys.argv[1:] == ["--json"]:
    values = json.load(sys.stdin)["data"]
else:
    values = dict(
        line.split("=", 1) for line in Path(sys.argv[1]).read_text().splitlines() if "=" in line
    )
missing = expected - values.keys()
invalid = {
    key for key, value in values.items() if not value or "REPLACE_" in value or "${" in value
}
if missing or invalid:
    sys.exit(
        f"Incomplete Flux configuration: missing={sorted(missing)}, unresolved={sorted(invalid)}"
    )
if (
    not re.fullmatch(r"\d{12}", values["aws_account_id"])
    or values["aws_account_id"] == "000000000000"
):
    sys.exit("A real AWS account ID is required for reconciliation")
