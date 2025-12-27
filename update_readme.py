import os
from datetime import datetime

import requests
from jinja2 import Environment, FileSystemLoader

# Configuration
UID = os.environ.get("UID_42")
SECRET = os.environ.get("SECRET_42")
USER_LOGIN = os.environ.get("USER_42")

API_URL = "https://api.intra.42.fr"
# Base URL for the artistic badges
BADGE_BASE_URL = (
    "https://raw.githubusercontent.com/ayogun/42-project-badges/main/badges"
)

# Manual mapping for common projects to ensure correct image filenames
# Format: "project_slug": "image_filename_without_extension"
# The repo typically uses 'm' suffix for mandatory part badges
PROJECT_MAPPING = {
    "libft": "libftm",
    "get-next-line": "get_next_linem",
    "get_next_line": "get_next_linem",
    "ft-printf": "ft_printfm",
    "ft_printf": "ft_printfm",
    "born2beroot": "born2berootm",
    "push-swap": "push_swapm",
    "push_swap": "push_swapm",
    "minitalk": "minitalkm",
    "pipex": "pipexm",
    "so-long": "so_longm",
    "so_long": "so_longm",
    "fract-ol": "fract_olm",
    "fract_ol": "fract_olm",
    "philosophers": "philosophersm",
    "minishell": "minishellm",
    "cub3d": "cub3dm",
    "minirt": "minirtm",
    "netpractice": "netpracticem",
    "cpp-module-00": "cpp00m",
    "cpp-module-01": "cpp01m",
    "cpp-module-02": "cpp02m",
    "cpp-module-03": "cpp03m",
    "cpp-module-04": "cpp04m",
    "cpp-module-05": "cpp05m",
    "cpp-module-06": "cpp06m",
    "cpp-module-07": "cpp07m",
    "cpp-module-08": "cpp08m",
    "cpp-module-09": "cpp09m",
    "inception": "inceptionm",
    "webserv": "webservm",
    "ft-irc": "ft_ircm",
    "ft_irc": "ft_ircm",
    "ft-transcendence": "ft_transcendencem",
}


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

    # Filter strictly for Cursus 21 (42 Cursus/Cadet)
    url = f"{API_URL}/v2/users/{user_id}/projects_users?page[size]=100&sort=-updated_at&filter[cursus]=21"

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
        if page >= 5:
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

    # Sort projects by marked_at date (descending)
    projects.sort(key=lambda x: x["marked_at"] if x["marked_at"] else "", reverse=True)

    # Process projects to generate Image Badge URL
    processed_projects = []
    for p in projects:
        slug = p["project"]["slug"]

        # Determine image filename
        if slug in PROJECT_MAPPING:
            image_name = PROJECT_MAPPING[slug]
        else:
            # Fallback: try appending 'm' or just using slug
            # Most badges in that repo follow slug + 'm' pattern
            image_name = f"{slug}m"

        # Build URL
        p["badge_url"] = f"{BADGE_BASE_URL}/{image_name}.png"
        processed_projects.append(p)

    # Get Level for Cursus 21
    cursus_42 = next(
        (c for c in user_data["cursus_users"] if c["cursus"]["id"] == 21), None
    )

    level_badge = ""
    if cursus_42:
        lvl = cursus_42["level"]
        level_badge = f"https://img.shields.io/badge/Level-{lvl}-000000?style=for-the-badge&logo=42&logoColor=white"

    rendered_readme = template.render(
        user=user_data,
        cursus=cursus_42,
        level_badge=level_badge,
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

        print(f"Found {len(projects)} Cadet projects. Generating README...")
        generate_readme(user_data, projects)
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
