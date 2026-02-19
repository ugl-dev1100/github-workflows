import os
import requests
import sys
import boto3
from datetime import datetime, timedelta

# =====================================================
# INPUTS FROM GITHUB ACTIONS
# =====================================================

ACTION_TYPE = os.getenv("ACTION_TYPE", "").lower()
REPO_INPUT = os.getenv("REPOS", "")
PIPELINE_INPUT = os.getenv("PIPELINES", "")

ORG = os.getenv("GH_ORG")
TOKEN = os.getenv("GH_TOKEN")
AWS_REGION = os.getenv("AWS_REGION")

if not ORG or not TOKEN:
    print("❌ Missing GH_ORG or GH_TOKEN")
    sys.exit(1)

if not ACTION_TYPE or ACTION_TYPE not in ["staging", "uat"]:
    print("❌ ACTION_TYPE must be 'staging' or 'uat'")
    sys.exit(1)

REPOS = [r.strip() for r in REPO_INPUT.split(",") if r.strip()]
PIPELINES = [p.strip() for p in PIPELINE_INPUT.split(",") if p.strip()]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json"
}

today = datetime.now()

# # =====================================================
# # DATE CALCULATION
# # =====================================================

# def get_next_wednesday():
#     days_ahead = 2 - today.weekday()  # Wednesday = 2
#     if days_ahead <= 0:
#         days_ahead += 7
#     return today + timedelta(days=days_ahead)

# if ACTION_TYPE == "staging":
#     branch_date = today.strftime("%Y-%m-%d")
#     branch_name = f"staging-{branch_date}"
# else:
#     next_wed = get_next_wednesday()
#     branch_date = next_wed.strftime("%Y-%m-%d")
#     branch_name = f"uat-release-{branch_date}"

# # =====================================================
# # GITHUB HELPERS
# # =====================================================

# def branch_exists(repo, branch):
#     url = f"https://api.github.com/repos/{ORG}/{repo}/branches/{branch}"
#     r = requests.get(url, headers=HEADERS)
#     return r.status_code == 200

# def get_main_sha(repo):
#     url = f"https://api.github.com/repos/{ORG}/{repo}/branches/main"
#     r = requests.get(url, headers=HEADERS)
#     if r.status_code != 200:
#         return None
#     return r.json()["commit"]["sha"]

# def create_branch(repo, branch_name, sha):
#     url = f"https://api.github.com/repos/{ORG}/{repo}/git/refs"
#     data = {"ref": f"refs/heads/{branch_name}", "sha": sha}
#     return requests.post(url, headers=HEADERS, json=data)

# def delete_branch(repo, branch):
#     url = f"https://api.github.com/repos/{ORG}/{repo}/git/refs/heads/{branch}"
#     return requests.delete(url, headers=HEADERS)

# def get_all_branches(repo):
#     url = f"https://api.github.com/repos/{ORG}/{repo}/branches?per_page=100"
#     r = requests.get(url, headers=HEADERS)
#     if r.status_code != 200:
#         return []
#     return [b["name"] for b in r.json()]

# def delete_previous_uat(repo, current_branch):
#     branches = get_all_branches(repo)
#     old_uat = sorted(
#         [b for b in branches if b.startswith("uat-release-") and b != current_branch],
#         reverse=True
#     )
#     if not old_uat:
#         return 0
#     deleted = 0
#     for branch in old_uat:
#         resp = delete_branch(repo, branch)
#         if resp.status_code == 204:
#             deleted += 1
#     return deleted

# =====================================================
# DATE CALCULATION
# =====================================================

def get_latest_uat_date(repo):
    branches = get_all_branches(repo)
    uat_branches = [
        b.replace("uat-release-", "")
        for b in branches
        if b.startswith("uat-release-")
    ]

    if not uat_branches:
        return None

    try:
        dates = sorted(
            [datetime.strptime(d, "%Y-%m-%d") for d in uat_branches],
            reverse=True
        )
        return dates[0]
    except:
        return None


if ACTION_TYPE == "staging":
    branch_date = today.strftime("%Y-%m-%d")
    branch_name = f"staging-{branch_date}"

else:
    # For testing → Always add +1 day from latest UAT
    sample_repo = REPOS[0]  # check from first repo
    latest_date = get_latest_uat_date(sample_repo)

    if latest_date:
        new_date = latest_date + timedelta(days=1)
    else:
        new_date = today

    branch_date = new_date.strftime("%Y-%m-%d")
    branch_name = f"uat-release-{branch_date}"

# =====================================================
# CODEPIPELINE UPDATE
# =====================================================

def update_codepipeline_branch(pipeline_name, new_branch):
    client = boto3.client("codepipeline", region_name=AWS_REGION)

    response = client.get_pipeline(name=pipeline_name)
    pipeline = response["pipeline"]

    for stage in pipeline["stages"]:
        if stage["name"].lower() == "source":
            for action in stage["actions"]:
                if "BranchName" in action["configuration"]:
                    action["configuration"]["BranchName"] = new_branch
                    print(f"🔄 {pipeline_name} updated → {new_branch}")

    client.update_pipeline(pipeline=pipeline)

# =====================================================
# EXECUTION
# =====================================================

print("--------------------------------------------------")
print(f"🎯 ACTION: {ACTION_TYPE.upper()}")
print(f"🌿 Branch: {branch_name}")
print("--------------------------------------------------")

success = 0
failed = 0
deleted_count = 0

for repo in REPOS:

    print(f"\n📦 Processing Repo: {repo}")

    if branch_exists(repo, branch_name):
        print("   ⚠ Branch already exists")
        continue

    sha = get_main_sha(repo)
    if not sha:
        print("   ❌ main branch not found")
        failed += 1
        continue

    resp = create_branch(repo, branch_name, sha)

    if resp.status_code == 201:
        print("   ✅ Branch created")
        success += 1

        if ACTION_TYPE == "uat":
            deleted = delete_previous_uat(repo, branch_name)
            deleted_count += deleted
            print(f"   🗑 Deleted old UAT branches: {deleted}")
    else:
        print("   ❌ Failed to create branch")
        failed += 1

# =====================================================
# UPDATE CODEPIPELINES (Only for UAT)
# =====================================================

if ACTION_TYPE == "uat" and PIPELINES:
    print("\n🚀 Updating CodePipelines...\n")
    for pipeline in PIPELINES:
        try:
            update_codepipeline_branch(pipeline, branch_name)
            print(f"   ✅ {pipeline} updated")
        except Exception as e:
            print(f"   ❌ Failed to update {pipeline}: {str(e)}")

print("\n--------------------------------------------------")
print("✅ Completed")
print(f"Success: {success}")
print(f"Failed: {failed}")
print(f"Deleted Old UAT: {deleted_count}")
print("--------------------------------------------------")
