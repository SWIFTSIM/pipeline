import setuptools
from swiftpipeline import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="swiftpipeline",
    version=__version__,
    description="Pipeline for producing galaxy scaling relation plots.",
    url="https://github.com/SWIFTSIM/pipeline",
    author="Josh Borrow",
    author_email="josh@joshborrow.com",
    packages=setuptools.find_packages(),
    long_description=long_description,
    long_description_content_type="text/markdown",
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "astropy",
        "swiftsimio",
        "matplotlib",
        "jinja2",
        "velociraptor",
        "unyt",
        "tqdm",
        "p_tqdm",
    ],
    scripts=["swift-pipeline", "swift-image"],
    include_package_data=True,
)
