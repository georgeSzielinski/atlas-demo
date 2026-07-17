import os

from ai.openai_client import test_openai_connection

if os.environ.get("RUN_LIVE_OPENAI_TEST") != "1":
    print("OpenAI live test skipped. Set RUN_LIVE_OPENAI_TEST=1 to run it.")
    raise SystemExit(0)

if not os.environ.get("OPENAI_API_KEY"):
    print("OpenAI live test skipped. OPENAI_API_KEY is not set.")
    raise SystemExit(0)

message = test_openai_connection()

print(message)
