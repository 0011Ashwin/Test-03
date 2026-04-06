import os
import argparse
from google.adk.adk_api_server import ADKServer
from agent import root_agent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8005)
    parser.add_argument("--trace_to_cloud", action="store_true")
    parser.add_argument("--a2a", action="store_true")
    args = parser.parse_args()

    # The PORT env var is standard for Cloud Run deployments
    port = int(os.environ.get("PORT", args.port))

    server = ADKServer(
        agent=root_agent,
        host=args.host,
        port=port,
        trace_to_cloud=args.trace_to_cloud,
        a2a=args.a2a
    )
    server.run()

if __name__ == "__main__":
    main()
