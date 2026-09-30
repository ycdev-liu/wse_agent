import os
import json
import urllib.request
import urllib.error

BASE_URL = os.environ["ANTHROPIC_BASE_URL"].rstrip("/")
TOKEN = os.environ["ANTHROPIC_AUTH_TOKEN"]
MODEL = os.environ["ANTHROPIC_MODEL"]

url = BASE_URL + "/v1/messages"

payload = {
    "model": MODEL,
    "max_tokens": 100,
    "messages": [
        {
            "role": "user",
            "content": "Reply with exactly: API OK"
        }
    ]
}

data = json.dumps(payload).encode("utf-8")

request = urllib.request.Request(
    url,
    data=data,
    method="POST",
    headers={
        "content-type": "application/json",
        "Authorization": f"Bearer {TOKEN}",
        "anthropic-version": "2023-06-01",
    },
)

try:
    with urllib.request.urlopen(
        request,
        timeout=60
    ) as response:

        result = json.loads(
            response.read().decode("utf-8")
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2
            )
        )

except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code)

    print(
        e.read().decode(
            "utf-8",
            errors="replace"
        )
    )

except Exception as e:
    print(type(e).__name__, str(e))
