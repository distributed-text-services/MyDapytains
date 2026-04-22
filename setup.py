from setuptools import setup, find_packages

# Read dependencies from requirements.txt
def read_requirements():
    with open("requirements.txt") as f:
        return f.read().splitlines()

setup(
    name="dapytains",
    version="1.0.0rc1",
    author="Thibault Clérice",
    author_email="thibault.clerice@inria.fr",
    description="A brief description of dapytains",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/distributed-text-services/MyDapytains",
    packages=find_packages(),
    install_requires=read_requirements(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    include_package_data=True,
)
