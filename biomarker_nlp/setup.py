import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="biomarker-nlp",
    version="0.1.7",
    author="Junxia Lin",
    author_email="damonlin11@gmail.com",
    description="NLP for detecting and extracting biomarkers from biomedical text",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Damonlin11/FDA-Target-Therapy-Label-Extraction",
    project_urls={
        "Bug Tracker": "https://github.com/Damonlin11/FDA-Target-Therapy-Label-Extraction/issues",
        "Documentation": "https://github.com/Damonlin11/FDA-Target-Therapy-Label-Extraction/blob/main/biomarker_nlp%20documentation%20v01.pdf",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)
