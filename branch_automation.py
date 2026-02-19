
# import os
# import requests
# import sys
# from datetime import datetime

# # =====================================================
# # CONFIGURATION
# # =====================================================

# REPOS = ("web", "reports", "traceui2", "one-freight-ui")

# HOLIDAYS = {
#     "2026": {
#         "02": [],
#         "03": ["2026-03-04"],  # Add more holidays here
#         "04": []
#     }
# }

# ORG = os.getenv("GH_ORG")
# TOKEN = os.getenv("GH_TOKEN")
# QA_SLACK_WEBHOOK = os.getenv("QA_SLACK_WEBHOOK")

# if not ORG or not TOKEN:
#     print("❌ Missing GH_ORG or GH_TOKEN")
#     sys.exit(1)

# HEADERS = {
#     "Authorization": f"Bearer {TOKEN}",
#     "Accept": "application/vnd.github+json"
# }

# # =====================================================
# # DATE INFO
# # =====================================================

# today = datetime.now()
# today_str = today.strftime("%Y-%m-%d")
# weekday = today.strftime("%A")
# week_number = today.strftime("%Y-%W")

# # =====================================================
# # HELPER FUNCTIONS
# # =====================================================

# def is_holiday(date_str):
#     year = date_str[:4]
#     month = date_str[5:7]
#     return date_str in HOLIDAYS.get(year, {}).get(month, [])


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


# def branch_done_this_week(prefix):
#     for repo in REPOS:
#         branches = get_all_branches(repo)
#         for b in branches:
#             if b.startswith(prefix):
#                 try:
#                     date_part = b.split(prefix + "-")[1]
#                     d = datetime.strptime(date_part, "%Y-%m-%d")
#                     if d.strftime("%Y-%W") == week_number:
#                         return True
#                 except:
#                     continue
#     return False


# def delete_previous_uat(repo, current_branch):
#     branches = get_all_branches(repo)
#     uat_branches = sorted(
#         [b for b in branches if b.startswith("uat-release-") and b != current_branch],
#         reverse=True
#     )

#     if not uat_branches:
#         return "No previous UAT found"

#     previous = uat_branches[0]
#     resp = delete_branch(repo, previous)

#     if resp.status_code == 204:
#         return f"Deleted {previous}"
#     return f"Failed to delete {previous}"


# def send_slack(message):
#     if not QA_SLACK_WEBHOOK:
#         return
#     try:
#         requests.post(QA_SLACK_WEBHOOK, json={"text": message})
#     except Exception as e:
#         print(f"Slack error: {e}")


# # =====================================================
# # DECISION LOGIC
# # =====================================================

# if is_holiday(today_str):
#     print("📅 Holiday today. Skipping execution.")
#     sys.exit(0)

# staging_done = branch_done_this_week("staging")
# uat_done = branch_done_this_week("uat-release")

# action = None
# holiday_adjusted = False

# # Wednesday logic
# if weekday == "Wednesday":
#     action = "staging"

# # Thursday logic
# elif weekday == "Thursday":
#     if not staging_done:
#         action = "staging"
#         holiday_adjusted = True
#     elif not uat_done:
#         action = "uat"

# # Friday recovery logic
# elif weekday == "Friday":
#     if staging_done and not uat_done:
#         action = "uat"
#         holiday_adjusted = True

# if not action:
#     print("ℹ No branch action required today.")
#     sys.exit(0)

# branch_name = (
#     f"uat-release-{today_str}"
#     if action == "uat"
#     else f"staging-{today_str}"
# )

# # =====================================================
# # EXECUTION
# # =====================================================

# summary = []
# success = 0
# failed = 0
# deleted_count = 0

# for repo in REPOS:

#     if branch_exists(repo, branch_name):
#         summary.append(f"{repo}: Already exists")
#         continue

#     sha = get_main_sha(repo)
#     if not sha:
#         summary.append(f"{repo}: main branch not found")
#         failed += 1
#         continue

#     resp = create_branch(repo, branch_name, sha)

#     if resp.status_code == 201:
#         msg = f"{repo}: Created"
#         success += 1

#         if action == "uat":
#             delete_msg = delete_previous_uat(repo, branch_name)
#             if "Deleted" in delete_msg:
#                 deleted_count += 1
#             msg += f" | {delete_msg}"
#     else:
#         msg = f"{repo}: Failed"
#         failed += 1

#     summary.append(msg)

# # =====================================================
# # SLACK MESSAGE
# # =====================================================

# slack_message = f"""
# 📦 *Weekly Branch Automation*

# 🌿 Branch: {branch_name}
# 📅 Date: {today_str}
# 🔁 Holiday Adjusted: {'Yes' if holiday_adjusted else 'No'}

# ✅ Success: {success}
# ❌ Failed: {failed}
# 🗑 Deleted Previous UAT: {deleted_count}

# Details:
# """ + "\n".join(summary)

# send_slack(slack_message)

# print("✅ Completed successfully.")

import os
import requests
import sys
from datetime import datetime, timedelta

# =====================================================
# ENV VARIABLES FROM GITHUB ACTIONS
# =====================================================

ORG = os.getenv("GH_ORG")
TOKEN = os.getenv("GH_TOKEN")
QA_SLACK_WEBHOOK = os.getenv("QA_SLACK_WEBHOOK")
DEVOPS_SLACK_WEBHOOK = os.getenv("DEVOPS_SLACK_WEBHOOK")

ACTION_TYPE = os.getenv("ACTION_TYPE")  # staging or uat
REPO_LIST = os.getenv("REPO_LIST")
TRIGGERED_BY = os.getenv("TRIGGERED_BY", "DevOps Team")

if not ORG or not TOKEN or not ACTION_TYPE or not REPO_LIST:
    print("❌ Missing required environment variables")
    sys.exit(1)

REPOS = tuple(repo.strip() for repo in REPO_LIST.split(","))

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json"
}

today = datetime.now()
today_str = today.strftime("%Y-%m-%d")


# =====================================================
# DATE CALCULATION
# =====================================================

def get_next_wednesday():
    days_ahead = 2 - today.weekday()  # Wednesday = 2
    if days_ahead <= 0:
        days_ahead += 7
    next_wed = today + timedelta(days=days_ahead)
    return next_wed.strftime("%Y-%m-%d")


if ACTION_TYPE.lower() == "staging":
    branch_name = f"staging-{today_str}"

elif ACTION_TYPE.lower() == "uat":
    next_wed = get_next_wednesday()
    branch_name = f"uat-release-{next_wed}"

else:
    print("❌ Invalid ACTION_TYPE. Use staging or uat.")
    sys.exit(1)


# =====================================================
# GITHUB FUNCTIONS
# =====================================================

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


def get_all_branches(repo):
    url = f"https://api.github.com/repos/{ORG}/{repo}/branches?per_page=100"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return []
    return [b["name"] for b in r.json()]


def delete_branch(repo, branch):
    url = f"https://api.github.com/repos/{ORG}/{repo}/git/refs/heads/{branch}"
    return requests.delete(url, headers=HEADERS)


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


def send_slack(webhook, message):
    if not webhook:
        return
    try:
        requests.post(webhook, json={"text": message})
    except Exception as e:
        print(f"Slack error: {e}")


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

        if ACTION_TYPE.lower() == "uat":
            delete_msg = delete_previous_uat(repo, branch_name)
            if "Deleted" in delete_msg:
                deleted_count += 1
            msg += f" | {delete_msg}"
    else:
        msg = f"{repo}: Failed"
        failed += 1

    summary.append(msg)


# =====================================================
# SLACK MESSAGES
# =====================================================

# QA Channel Message
qa_message = f"""
Hi Team,
{branch_name} 🌿 has been successfully created for this week.

Regards,
{TRIGGERED_BY}
DevOps Team
"""

send_slack(QA_SLACK_WEBHOOK, qa_message)


# DevOps Detailed Report
devops_message = f"""
📦 *Branch Automation Report*

🎯 Action        : {ACTION_TYPE.upper()}
🌿 Branch        : {branch_name}
📅 Date          : {today_str}

----------------------------------------
✅ Success       : {success}
❌ Failed        : {failed}
🗑 Deleted UAT   : {deleted_count}
----------------------------------------

Triggered By     : {TRIGGERED_BY}

Details:
""" + "\n".join(summary)

send_slack(DEVOPS_SLACK_WEBHOOK, devops_message)

print("--------------------------------------------------")
print("✅ Completed.")
print("\n".join(summary))
