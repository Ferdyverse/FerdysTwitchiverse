#!/usr/bin/env python3

import argparse
import uvicorn
import os
import config

def startup():
    parser = argparse.ArgumentParser(description="Start the Ferdyverse API with optional modules disabled.")
    parser.add_argument("--disable-heat-api", action="store_true", help="Disable the Heat API module")
    parser.add_argument("--disable-firebot", action="store_true", help="Disable the Firebot module")
    parser.add_argument("--disable-printer", action="store_true", help="Disable the Printer module")
    parser.add_argument("--disable-twitch", action="store_true", help="Disable the Twitch module")
    parser.add_argument("--disable-obs", action="store_true", help="Disable the OBS module")
    args = parser.parse_args()

    os.environ["DISABLE_HEAT_API"] = "true" if args.disable_heat_api else "false"
    os.environ["DISABLE_FIREBOT"] = "true" if args.disable_firebot else "false"
    os.environ["DISABLE_PRINTER"] = "true" if args.disable_printer else "false"
    os.environ["DISABLE_TWITCH"] = "true" if args.disable_twitch else "false"
    os.environ["DISABLE_OBS"] = "true" if args.disable_obs else "false"

    print("🚀 Starting Ferdyverse API with:")
    print(f"   - Heat API: {'DISABLED' if args.disable_heat_api else 'ENABLED'}")
    print(f"   - Firebot API: {'DISABLED' if args.disable_firebot else 'ENABLED'}")
    print(f"   - Printer Module: {'DISABLED' if args.disable_printer else 'ENABLED'}")
    print(f"   - Twitch Module: {'DISABLED' if args.disable_twitch else 'ENABLED'}")
    print(f"   - OBS Module: {'DISABLED' if args.disable_obs else 'ENABLED'}")
    print("===============================================")

    # Debugging: Check if main.py is found
    if not os.path.exists("main.py"):
        print("❌ ERROR: main.py not found!")
        exit(1)

    # Debugging: Try to import main.py
    try:
        import main
    except Exception as e:
        print(f"❌ ERROR importing main.py: {e}")
        exit(1)

    # Debugging: Try running Uvicorn
    try:
        uvicorn.run("main:app", host=config.APP_HOST, port=config.APP_PORT, reload=True, log_level=config.APP_LOG_LEVEL)
    except Exception as e:
        print(f"❌ ERROR starting Uvicorn: {e}")
        exit(1)

if __name__ == "__main__":
    startup()
