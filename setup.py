#!/usr/bin/env python3
"""
Setup script for Subjugate Online
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="subjugate-online",
    version="1.0.0",
    author="Subjugate Online Development Team",
    description="A hardcore ironman 3D MMORPG with reincarnation mechanics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/subjugate-online",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment :: Role-Playing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "sqlalchemy>=2.0.0",
        "psycopg2-binary>=2.9.0",
        "pygame>=2.5.0",
        "PyOpenGL>=3.1.0",
    ],
    entry_points={
        "console_scripts": [
            "subjugate-login-server=subjugate_online.login_server.server:main",
            "subjugate-game-server=subjugate_online.game_server.server:main",
            "subjugate-client=subjugate_online.client.client:main",
        ],
    },
)
