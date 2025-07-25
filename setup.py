import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="datahub-api-connector",
    version="1.0",
    author="Verity",
    author_email="support@opinum.com",
    description="Package to interact with the Data Hub API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/opinum/datahub-api-connector",
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.10",
    install_requires=[
        'requests',
        'requests_oauthlib',
        'oauthlib',
        'concurrent.futures'
    ],
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
