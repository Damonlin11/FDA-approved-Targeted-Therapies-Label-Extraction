import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="biomarker-nlp",
    version="0.0.4",
    author="Junxia Lin",
    author_email="damonlin11@gmail.com",
    description="NLP for detecting and extracting biomarkers from biomedical text",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Damonlin11/FDA-approved-Targeted-Therapies-Label-Extraction/tree/main/biomarker_nlp",
    project_urls={
        "Bug Tracker": "https://github.com/Damonlin11/FDA-approved-Targeted-Therapies-Label-Extraction/issues",
        "Documentation": "https://github.com/Damonlin11/FDA-approved-Targeted-Therapies-Label-Extraction/blob/main/biomarker_nlp/docs/_build/latex/biomarker_nlp.pdf",
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
