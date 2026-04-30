import os
import re
import requests
import sys

# Configurações do usuário
LOGIN = "clados-s"
CLIENT_ID = os.environ.get("INTRA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("INTRA_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("Erro: Credenciais da API não encontradas nas variáveis de ambiente.")
    sys.exit(1)

def get_token():
    url = "https://api.intra.42.fr/oauth/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

def get_level(token):
    url = f"https://api.intra.42.fr/v2/users/{LOGIN}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    user_data = response.json()
    for cursus in user_data.get("cursus_users", []):
        if cursus["cursus"]["name"] == "42cursus":
            return cursus["level"]
    return None

def update_readme(level):
    with open("README.md", "r", encoding="utf-8") as file:
        content = file.read()

    # Regex para capturar e substituir apenas o número do level na badge
    pattern = r"(https://img\.shields\.io/badge/42_Level-)[0-9.]+(-00BABC)"
    replacement = rf"\g<1>{level:.2f}\g<2>"
    
    new_content = re.sub(pattern, replacement, content)

    if content != new_content:
        with open("README.md", "w", encoding="utf-8") as file:
            file.write(new_content)
        print(f"README atualizado com sucesso para o level {level:.2f}!")
        return True
    else:
        print("O level não mudou desde a última atualização.")
        return False

if __name__ == "__main__":
    try:
        token = get_token()
        level = get_level(token)
        
        if level is not None:
            print(f"Level atual na Intra: {level}")
            update_readme(level)
        else:
            print("Cursus '42cursus' não encontrado.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Falha na execução: {e}")
        sys.exit(1)
