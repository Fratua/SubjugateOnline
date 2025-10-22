#!/usr/bin/env python3
"""
Subjugate Online - Game Server Launcher
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.game_server.game_server import main
import asyncio

if __name__ == '__main__':
    print("=" * 60)
    print("SUBJUGATE ONLINE - GAME SERVER")
    print("=" * 60)
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGame server stopped.")
