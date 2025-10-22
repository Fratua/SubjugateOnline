#!/usr/bin/env python3
"""
Subjugate Online - Login Server Launcher
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.login_server.login_server import main
import asyncio

if __name__ == '__main__':
    print("=" * 60)
    print("SUBJUGATE ONLINE - LOGIN SERVER")
    print("=" * 60)
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nLogin server stopped.")
