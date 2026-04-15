import requests
import click
import os

BASE_URL = "http://127.0.0.1:8767"


def locate_server(context: dict) -> str:

    click.echo("+ Locating server...")

    response = requests.get(f"{BASE_URL}/health", timeout=2)
    response.raise_for_status()
    data = response.json()
    context['status'] = data['status']
    context['version'] = data['version']
    click.echo(
        f"  + Status: {context['status']}, Version {context['version']}")


def load_creds(context: dict) -> None:
    context['openai_api_key'] = os.getenv("OPENAI_API_KEY")
    context['openai_api_base'] = os.getenv("OPENAI_API_BASE")
    context['openai_api_model'] = os.getenv("OPENAI_API_MODEL")
    context['benchmark_user_email'] = os.getenv("BENCHMARK_USER_EMAIL")


def do_chat(context: dict, dir: str, prompt: str, run_index: int = 0) -> dict:
    model_label = context.get("model", "").replace("/", "--")
    api_session_id = f"{context['session_id']}-{model_label}-{run_index}"
    response = requests.post(
        f"{BASE_URL}/chat",
        json={
            "dir": dir,
            "prompt": prompt,
            "model": context.get("model"),
            "session_id": api_session_id,
            "openai_api_key": context['openai_api_key'],
            "openai_api_base": context['openai_api_base'],
            "openai_api_model": context['openai_api_model'],
            "user_email": context['benchmark_user_email'],
        },
        timeout=600,
    )

    try:
        res_json = response.json()
        if not res_json.get("success"):
            raise Exception(f"Chat failed: {res_json}")
    except Exception as e:
        raise Exception(f"Chat failed: {e}")
    return res_json["data"]
