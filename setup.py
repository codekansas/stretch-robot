#!/usr/bin/env python

from setuptools import setup

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="ml",
    version="0.0.1",
    description="Stretch robot project",
    author="Benjamin Bolte",
    url="https://github.com/codekansas/stretch-robot",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    install_requires=[
        "aiohttp",
        "aiortc",
        "opencv-python",
    ],
    python_requires=">=3.8",
    extras_require={
        "dev": {
            "black",
            "darglint",
            "flake8",
            "mypy-extensions",
            "mypy",
            "pylint",
            "pytest",
            "types-setuptools",
            "typing_extensions",
        },
    },
)
