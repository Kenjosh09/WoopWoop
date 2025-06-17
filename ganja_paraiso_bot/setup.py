from setuptools import setup, find_packages

setup(
    name="ganja_paraiso_bot",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "python-telegram-bot>=20.0",
        "gspread",
        "google-auth",
        "google-api-python-client",
    ],
)