import os
import requests
from dotenv import load_dotenv

load_dotenv()

_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


def send_slack_message(message: str) -> None:
    """
    Post a message to the configured Slack webhook.
    Silently skips if SLACK_WEBHOOK_URL is not set (Slack is optional).
    """
    if not _WEBHOOK_URL:
        print("[Slack] SLACK_WEBHOOK_URL not set — skipping notification.")
        return

    try:
        response = requests.post(_WEBHOOK_URL, json={"text": message}, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        print(f"[Slack] Failed to send message: {exc}")
