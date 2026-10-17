"""Builds and deploys seoul_trip_note to Cloudflare Pages (project: seoul-trip-note).

Usage: python deploy.py
"""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SECRETS = r"C:\TossApps\today\collector\secrets.json"
PROJECT = "seoul-trip-note"

if os.path.exists(SECRETS):
    sec = json.load(open(SECRETS, encoding="utf-8"))
    env = {**os.environ, "CLOUDFLARE_API_TOKEN": sec["cf_token"], "CLOUDFLARE_ACCOUNT_ID": sec["cf_account_id"]}
else:
    env = dict(os.environ)  # Mac: no secrets file, use the logged-in wrangler account

# 1. Build
print("Building Astro site...")
subprocess.run("npm run build", cwd=HERE, shell=True, check=True)

# 2. Deploy
print(f"Deploying to Cloudflare Pages ({PROJECT})...")
r = subprocess.run(
    f"npx --yes wrangler@3 pages deploy dist --project-name {PROJECT} --branch main --commit-dirty=true",
    cwd=HERE,
    shell=True,
    env=env,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
if r.returncode != 0:
    sys.exit(f"Deploy failed:\n{r.stderr}")

for line in r.stdout.splitlines():
    if "Deployment complete" in line or "Success" in line or "pages.dev" in line:
        print(line)
