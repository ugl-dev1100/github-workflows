# import os
# import requests
# import json
# from datetime import datetime, timedelta
# from getpass import getpass
# import sys

# # =========================
# # STATIC REPO LIST
# # =========================

# repos = ("web", "reports", "traceui2", "one-freight-ui")

# # =========================
# # HOLIDAYS (Extend anytime)
# # =========================

# HOLIDAYS = {
#     "2026": {
#         "02": [],
#         "03": ["2026-03-04"],  # Example holiday
#         "04": []
#     }
# }

# # =========================
# # ENV VARIABLES
# # =========================

# ORG = os.getenv("GH_ORG") or input("Enter GitHub Org: ").strip()
# TOKEN = os.getenv("GH_TOKEN") or getpass("Enter GitHub PAT: ").strip()
# QA_SLACK_WEBHOOK = os.getenv("QA_SLACK_WEBHOOK")

# if not TOKEN:
#     print("GitHub token required.")
#     sys.exit(1)

# headers = {
#     "Authorization": f"Bearer {TOKEN}",
#     "Accept": "application/vnd.github+json"
# }

# # =========================
# # DATE INFO
# # =========================

# today = datetime.now()
# today_str = today.strftime("%Y-%m-%d")
# year = today.strftime("%Y")
# month = today.strftime("%m")
# today_day = today.strftime("%A")
# week_number = today.strftime("%Y-%W")

# # =========================
# # HELPER FUNCTIONS
# # =========================

# def is_holiday(date_str):
#     return date_str in HOLIDAYS.get(year, {}).get(month, [])

# def branch_exists(repo, branch):
#     url = f"https://api.github.com/repos/{ORG}/{repo}/branches/{branch}"
#     r = requests.get(url, headers=headers)
#     return r.status_code == 200

# def get_sha(repo, source="main"):
#     url = f"https://api.github.com/repos/{ORG}/{repo}/branches/{source}"
#     r = requests.get(url, headers=headers)
#     if r.status_code != 200:
#         return None
#     return r.json()["commit"]["sha"]

# def create_branch(repo, branch_name, sha):
#     url = f"https://api.github.com/repos/{ORG}/{repo}/git/refs"
#     data = {
#         "ref": f"refs/heads/{branch_name}",
#         "sha": sha
#     }
#     return requests.post(url, headers=headers, json=data)

# def get_all_branches(repo):
#     branches = []
#     page = 1
#     while True:
#         url = f"https://api.github.com/repos/{ORG}/{repo}/branches?per_page=100&page={page}"
#         r = requests.get(url, headers=headers)
#         if r.status_code != 200:
#             break
#         data = r.json()
#         if not data:
#             break
#         branches.extend([b["name"] for b in data])
#         page += 1
#     return branches

# def delete_branch(repo, branch_name):
#     url = f"https://api.github.com/repos/{ORG}/{repo}/git/refs/heads/{branch_name}"
#     return requests.delete(url, headers=headers)

# def delete_previous_uat(repo, current_branch):
#     branches = get_all_branches(repo)
#     uat_branches = [
#         b for b in branches
#         if b.startswith("uat-release-") and b != current_branch
#     ]

#     if not uat_branches:
#         return "No previous UAT branch found"

#     uat_branches.sort(reverse=True)
#     previous_branch = uat_branches[0]

#     response = delete_branch(repo, previous_branch)

#     if response.status_code == 204:
#         return f"🗑 Deleted {previous_branch}"
#     else:
#         return f"⚠ Failed to delete {previous_branch}"

# def branch_created_this_week(prefix):
#     sample_repo = repos[0]
#     for i in range(7):
#         d = today - timedelta(days=i)
#         if d.strftime("%Y-%W") != week_number:
#             break
#         name = f"{prefix}-{d.strftime('%Y-%m-%d')}"
#         if branch_exists(sample_repo, name):
#             return True
#     return False

# def send_qa_slack(message):
#     if not QA_SLACK_WEBHOOK:
#         print("QA Slack webhook not configured.")
#         return
#     try:
#         requests.post(
#             QA_SLACK_WEBHOOK,
#             json={"text": message},
#             headers={"Content-Type": "application/json"}
#         )
#     except Exception as e:
#         print(f"Slack notification failed: {e}")

# # =========================
# # DECISION LOGIC
# # =========================

# if is_holiday(today_str):
#     print("Holiday today. Skipping.")
#     sys.exit(0)

# create_staging = False
# create_uat = False
# holiday_recovery = False

# if today_day == "Wednesday":
#     create_staging = True
# elif today_day == "Thursday":
#     create_uat = True
# else:
#     staging_done = branch_created_this_week("staging")
#     uat_done = branch_created_this_week("uat-release")

#     if not staging_done:
#         create_staging = True
#         holiday_recovery = True
#     elif staging_done and not uat_done:
#         create_uat = True
#         holiday_recovery = True

# if not create_staging and not create_uat:
#     print("Nothing to create today.")
#     sys.exit(0)

# branch_type = "staging" if create_staging else "uat-release"
# branch_name = f"{branch_type}-{today_str}"

# # =========================
# # EXECUTION
# # =========================

# summary = []
# success = 0
# failed = 0
# deleted = 0

# for repo in repos:
#     if branch_exists(repo, branch_name):
#         summary.append(f"{repo}: ⚠ Already exists")
#         continue

#     sha = get_sha(repo)
#     if not sha:
#         summary.append(f"{repo}: ❌ Cannot find main branch")
#         failed += 1
#         continue

#     r = create_branch(repo, branch_name, sha)

#     if r.status_code == 201:
#         msg = f"{repo}: ✅ Created"
#         success += 1

#         if branch_type == "uat-release":
#             delete_msg = delete_previous_uat(repo, branch_name)
#             if "Deleted" in delete_msg:
#                 deleted += 1
#             msg += f" | {delete_msg}"
#     else:
#         msg = f"{repo}: ❌ Failed"
#         failed += 1

#     summary.append(msg)

# # =========================
# # SLACK MESSAGE
# # =========================

# slack_message = f"""
# 📦 *Weekly Branch Automation*

# 🌿 Branch: `{branch_name}`
# 📅 Date: {today_str}
# 🔁 Holiday Recovery: {'Yes' if holiday_recovery else 'No'}

# ✅ Success: {success}
# ❌ Failed: {failed}
# 🗑 Deleted Old UAT: {deleted}

# Details:
# """ + "\n".join(summary)

# send_qa_slack(slack_message)

# print("Completed successfully.")

import os
import requests
import sys
from datetime import datetime

# =====================================================
# CONFIGURATION
# =====================================================

REPOS = ("web", "reports", "traceui2", "one-freight-ui")

HOLIDAYS = {
    "2026": {
        "02": [],
        "03": ["2026-03-04"],  # Add more holidays here
        "04": []
    }
}

ORG = os.getenv("GH_ORG")
TOKEN = os.getenv("GH_TOKEN")
QA_SLACK_WEBHOOK = os.getenv("QA_SLACK_WEBHOOK")

if not ORG or not TOKEN:
    print("❌ Missing GH_ORG or GH_TOKEN")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json"
}

# =====================================================
# DATE INFO
# =====================================================

today = datetime.now()
today_str = today.strftime("%Y-%m-%d")
weekday = today.strftime("%A")
week_number = today.strftime("%Y-%W")

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def is_holiday(date_str):
    year = date_str[:4]
    month = date_str[5:7]
    return date_str in HOLIDAYS.get(year, {}).get(month, [])


def branch_exists(repo, branch):
    url = f"https://api.github.com/repos/{ORG}/{repo}/branches/{branch}"
    r = requests.get(url, headers=HEADERS)
    return r.status_code == 200


def get_main_sha(repo):
    url = f"https://api.github.com/repos/{ORG}/{repo}/branches/main"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return None
    return r.json()["commit"]["sha"]


def create_branch(repo, branch_name, sha):
    url = f"https://api.github.com/repos/{ORG}/{repo}/git/refs"
    data = {"ref": f"refs/heads/{branch_name}", "sha": sha}
    return requests.post(url, headers=HEADERS, json=data)


def delete_branch(repo, branch):
    url = f"https://api.github.com/repos/{ORG}/{repo}/git/refs/heads/{branch}"
    return requests.delete(url, headers=HEADERS)


def get_all_branches(repo):
    url = f"https://api.github.com/repos/{ORG}/{repo}/branches?per_page=100"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return []
    return [b["name"] for b in r.json()]


def branch_done_this_week(prefix):
    for repo in REPOS:
        branches = get_all_branches(repo)
        for b in branches:
            if b.startswith(prefix):
                try:
                    date_part = b.split(prefix + "-")[1]
                    d = datetime.strptime(date_part, "%Y-%m-%d")
                    if d.strftime("%Y-%W") == week_number:
                        return True
                except:
                    continue
    return False


def delete_previous_uat(repo, current_branch):
    branches = get_all_branches(repo)
    uat_branches = sorted(
        [b for b in branches if b.startswith("uat-release-") and b != current_branch],
        reverse=True
    )

    if not uat_branches:
        return "No previous UAT found"

    previous = uat_branches[0]
    resp = delete_branch(repo, previous)

    if resp.status_code == 204:
        return f"Deleted {previous}"
    return f"Failed to delete {previous}"


def send_slack(message):
    if not QA_SLACK_WEBHOOK:
        return
    try:
        requests.post(QA_SLACK_WEBHOOK, json={"text": message})
    except Exception as e:
        print(f"Slack error: {e}")


# =====================================================
# DECISION LOGIC
# =====================================================

if is_holiday(today_str):
    print("📅 Holiday today. Skipping execution.")
    sys.exit(0)

staging_done = branch_done_this_week("staging")
uat_done = branch_done_this_week("uat-release")

action = None
holiday_adjusted = False

# Wednesday logic
if weekday == "Wednesday":
    action = "staging"

# Thursday logic
elif weekday == "Thursday":
    if not staging_done:
        action = "staging"
        holiday_adjusted = True
    elif not uat_done:
        action = "uat"

# Friday recovery logic
elif weekday == "Friday":
    if staging_done and not uat_done:
        action = "uat"
        holiday_adjusted = True

if not action:
    print("ℹ No branch action required today.")
    sys.exit(0)

branch_name = (
    f"uat-release-{today_str}"
    if action == "uat"
    else f"staging-{today_str}"
)

# =====================================================
# EXECUTION
# =====================================================

summary = []
success = 0
failed = 0
deleted_count = 0

for repo in REPOS:

    if branch_exists(repo, branch_name):
        summary.append(f"{repo}: Already exists")
        continue

    sha = get_main_sha(repo)
    if not sha:
        summary.append(f"{repo}: main branch not found")
        failed += 1
        continue

    resp = create_branch(repo, branch_name, sha)

    if resp.status_code == 201:
        msg = f"{repo}: Created"
        success += 1

        if action == "uat":
            delete_msg = delete_previous_uat(repo, branch_name)
            if "Deleted" in delete_msg:
                deleted_count += 1
            msg += f" | {delete_msg}"
    else:
        msg = f"{repo}: Failed"
        failed += 1

    summary.append(msg)

# =====================================================
# SLACK MESSAGE
# =====================================================

slack_message = f"""
📦 *Weekly Branch Automation*

🌿 Branch: {branch_name}
📅 Date: {today_str}
🔁 Holiday Adjusted: {'Yes' if holiday_adjusted else 'No'}

✅ Success: {success}
❌ Failed: {failed}
🗑 Deleted Previous UAT: {deleted_count}

Details:
""" + "\n".join(summary)

send_slack(slack_message)

print("✅ Completed successfully.")
