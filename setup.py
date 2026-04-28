from setuptools import setup, find_packages

setup(
    name="renderctl",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "typer[all]>=0.9.0",
        "openai>=1.0.0",
        "google-genai>=1.0.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "renderctl=renderctl.cli:app",
        ],
    },
    python_requires=">=3.9",
)
