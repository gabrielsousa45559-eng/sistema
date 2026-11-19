"""Shard Cloud entry point for the NexoFlow Python web app."""
import os

import server


def main():
    os.environ.setdefault("HOST", "0.0.0.0")
    os.environ.setdefault("PORT", "80")
    server.init()
    host = os.environ["HOST"]
    port = int(os.environ["PORT"])
    print(f"NexoFlow listening on {host}:{port}", flush=True)
    server.ThreadingHTTPServer((host, port), server.Handler).serve_forever()


if __name__ == "__main__":
    main()
