#!/usr/bin/env python3
"""
Subjugate Online - Game Client Launcher
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.login_client import main

if __name__ == '__main__':
    print("=" * 60)
    print("SUBJUGATE ONLINE - GAME CLIENT")
    print("Hardcore Ironman 3D MMORPG")
    print("=" * 60)
    print()

    try:
        main()
    except KeyboardInterrupt:
        print("\nClient closed.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
