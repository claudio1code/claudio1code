import os
from datetime import datetime

import requests
from jinja2 import Environment, FileSystemLoader

# Configuration
UID = os.environ.get("UID_42")
SECRET = os.environ.get("SECRET_42")
USER_LOGIN = os.environ.get("USER_42")

API_URL = "https://api.intra.42.fr"

# Base URL for project badges (Community maintained)
# Using a popular repo for badges: https://github.com/ayogun/42-project-badges
BADGE_BASE_URL = (
    "https://raw.githubusercontent.com/ayogun/42-project-badges/main/badges"
)


def get_token():
    if not UID or not SECRET:
        raise Exception("Credentials not found. Set UID_42 and SECRET_42.")

    token_url = f"{API_URL}/oauth/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": UID,
        "client_secret": SECRET,
    }
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]


def get_user_data(token, login):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_URL}/v2/users/{login}"
    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        raise Exception(f"User {login} not found.")
    response.raise_for_status()
    return response.json()


def get_projects(token, user_id):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_URL}/v2/users/{user_id}/projects_users?page[size]=100&sort=-updated_at"

    projects = []
    page = 1
    while True:
        paged_url = f"{url}&page[number]={page}"
        response = requests.get(paged_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        projects.extend(data)
        if page >= 5:  # Limit to avoid infinite loops
            break
        page += 1

    # Filter: Finished and Validated
    valid_projects = [
        p for p in projects if p["status"] == "finished" and p["validated?"] is True
    ]

    # Deduplicate keeping highest mark
    unique_projects = {}
    for p in valid_projects:
        slug = p["project"]["slug"]
        if slug not in unique_projects:
            unique_projects[slug] = p
        else:
            if p["final_mark"] > unique_projects[slug]["final_mark"]:
                unique_projects[slug] = p

    return list(unique_projects.values())


def generate_readme(user_data, projects):
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("README.md.j2")

    # Sort projects by date
    projects.sort(key=lambda x: x["marked_at"] if x["marked_at"] else "", reverse=True)

    # Process projects to add badge URL
    # We map common project names to the badge repository filenames
    processed_projects = []
    for p in projects:
        slug = p["project"]["slug"]
        # Basic mapping logic: most slugs match the filename in the repo
        # e.g. libft -> libftm, get_next_line -> get_next_linem
        # The repo 'ayogun/42-project-badges' usually appends 'e' or 'm' sometimes,
        # but let's try the direct slug first or standard mapping.
        # Actually, looking at the repo, they are usually just the slug.

        # We will pass the slug to the template and build the URL there or here.
        # Let's clean the slug if needed.
        p["badge_url"] = f"{BADGE_BASE_URL}/{slug}.png"
        processed_projects.append(p)

    cursus_42 = next(
        (c for c in user_data["cursus_users"] if c["cursus"]["id"] == 21), None
    )

    rendered_readme = template.render(
        user=user_data,
        cursus=cursus_42,
        projects=processed_projects,
        last_updated=datetime.now().strftime("%d/%m/%Y"),
    )

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(rendered_readme)


def main():
    try:
        if not USER_LOGIN:
            print("USER_42 not set.")
            exit(1)

        token = get_token()
        print(f"Fetching data for {USER_LOGIN}...")
        user_data = get_user_data(token, USER_LOGIN)
        projects = get_projects(token, user_data["id"])

        print(f"Found {len(projects)} projects. Generating README...")
        generate_readme(user_data, projects)
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
