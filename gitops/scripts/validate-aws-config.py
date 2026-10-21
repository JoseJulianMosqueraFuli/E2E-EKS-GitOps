import re
import sys
from pathlib import Path

values = dict(
    line.split('=', 1)
    for line in Path(sys.argv[1]).read_text().splitlines()
    if line.strip() and not line.startswith('#') and '=' in line
)
if set(values) != {'AWS_ACCOUNT_ID', 'AWS_REGION'}:
    sys.exit('AWS configuration must contain only AWS_ACCOUNT_ID and AWS_REGION')
if not re.fullmatch(r'\d{12}', values['AWS_ACCOUNT_ID']) or values['AWS_ACCOUNT_ID'] == '000000000000':
    sys.exit('A real AWS account is required to install the ArgoCD renderer')
if not re.fullmatch(r'[a-z]{2}(-[a-z]+)+-[0-9]+', values['AWS_REGION']):
    sys.exit('Invalid AWS region')
