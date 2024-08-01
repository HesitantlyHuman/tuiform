import os
from setuptools import setup, find_packages

PACKAGE_ROOT = os.path.dirname(os.path.realpath(__file__))
README_FILE = open(os.path.join(PACKAGE_ROOT, "README.md"), "r").read()

if __name__ == "__main__":
    setup(
        name="tuiform",
        version="0.0.0",
        description="Event driven declarative terminal user interfaces, written in python. ",
        long_description=README_FILE,
        long_description_content_type="text/markdown",
        url="https://github.com/HesitantlyHuman/tuiform",
        author="HesitantlyHuman",
        author_email="tannersims@hesitantlyhuman.com",
        packages=find_packages(),
        package_data={},
        install_requires=[
            "clipman",
            "pyphen"
        ],
    )
