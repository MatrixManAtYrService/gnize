from setuptools import setup

setup(
    name="gnize",
    version="0.1.0.dev1",
    description="cognize and recognize features in text",
    url="https://github.com/MatrixManAtYrService/gnize",
    author="Matt Rixman",
    author_email="gnize@matt.rixman.org",
    packages=["gnize"],
    python_requires=">=3.8",
    install_requires=["pyfinite", "prompt_toolkit", "sortedcontainers", "pyyaml", "dataclasses_json", "dacite", "py-multihash", "miniseq", "minineedle", "rich"],
    entry_points={
        "console_scripts": [
            "gn = gnize.cli:gn",
            "cog = gnize.cli:cog",
        ]
    },
)
