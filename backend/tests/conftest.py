import os


# Keep tests deterministic and independent of a developer's local .env file.
os.environ["SECRET_KEY"] = "test-secret-key-with-at-least-thirty-two-bytes"
