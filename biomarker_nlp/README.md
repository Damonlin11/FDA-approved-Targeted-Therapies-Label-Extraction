# Biomarker_NLP

This package (biomarker_nlp) contains modules and functions supporting recognition and extraction of biomarkers for each FDA-approved targeted cancer therapy listed at [NIH National Cancer Institute (NCI)](https://www.cancer.gov/about-cancer/treatment/types/targeted-therapies/targeted-therapies-fact-sheet) from the biomedical text on its NCI webpage (eg https://www.cancer.gov/about-cancer/treatment/drugs/lanreotideacetate) and corresponding DailyMed webpage(s) (eg https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=6e4a41fd-a753-4362-87ee-8cc56ed3660d). The package can extract the following biomarkers: gene/protein; therapy; disease; drug label; NDC code; other drugs in approved combination therapies with selected drug; genes/proteins that, when altered, serve as biomarkers of resistance (via statements of negation, indicating that a drug should not be given for a specific biomarker); whether approval was accelerated (indicating lower evidence threshold and requirement for further confirmatory studies); whether the drug is indicated for first-line treatment; and whether the drug is indicated for metastatic disease.

The biomarker recognition tasks are based on the pre-trained named-entity recognition (NER) models from [scispacy](https://github.com/allenai/scispacy). The tasks for detecting negated biomarkers are based on two pre-trained negation models obtained from Aditya Khandelwal & Suraj Sawant's (2020) [NegBERT](https://github.com/adityak6798/Transformers-For-Negation-and-Speculation) program. The negation tasks include negation cue detection and negation scope extraction from sentences. The package also provides functions to detect key clinical terminology for specific drugs and diseases, such as first-line treatment, accelerated approval, and metastatic disease. 

## Installation
To install the library, run command (If you’re in a Colab notebook (or similar), add a ! at the beginning, e.g. !pip):
```bash
pip install biomarker_nlp
```

Some functions will require you to install scispacy pre-trained models. To install a model, run a command like:
```bash
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.3.0/en_ner_craft_md-0.3.0.tar.gz
```

Some functions will require pre-trained negation models. Download [negCue](https://www.dropbox.com/s/3b8zhldmrx9niv4/negCue.zip?dl=0) and [negScope](https://www.dropbox.com/s/7nn1uptrvw66mn2/negScope.zip?dl=0), then load them in script:
```python
>>> modelCue = torch.load('/path/to/the/model') # path to the location where the model file is placed
```

#### Example Usage (biomarkers detection)

Install necessary packages and pre-trained models:
```bash
pip install scispacy
pip install -U spacy==2.3.1 # may return incompatible ERROR, but it won't be a problem as long as the spacy-2.3.1 is successfully installed
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.3.0/en_ner_craft_md-0.3.0.tar.gz
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.3.0/en_ner_jnlpba_md-0.3.0.tar.gz
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.3.0/en_ner_bionlp13cg_md-0.3.0.tar.gz
```

```python
# Import the module
>>> from biomarker_nlp import biomarker_extraction

# Example URL link to a drug's DailyMed label information page:
>>> url = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=939b5d1f-9fb2-4499-80ef-0607aa6b114e"

# Extract drug label from DailyMed:
>>> biomarker_extraction.drug_brand_label(dailyMedURL = url)
'AVASTIN- bevacizumab injection, solution'

# Extract NDC codes from DailyMed:
>>> biomarker_extraction.ndc_code(dailyMedURL = url)
'50242-060-01, 50242-060-10, 50242-061-01, 50242-061-10'

# Extract a section of content from the drug's DailyMed information page excluding the section heading. For example, extract the "INDICATIONS AND USAGE" section:
>>> sectionHeader = "INDICATIONS AND USAGE"  
>>> biomarker_extraction.section_content(dailyMedURL = url, section = sectionHeader)
'1.1\tMetastatic Colorectal Cancer \nAvastin, in combination with intravenous fluorouracil-based chemotherapy, is indicated for the first-or second-line treatment of patients with metastatic colorectal cancer (mCRC).\nAvastin, in combination with fluoropyrimidine-irinotecan- or fluoropyrimidine-oxaliplatin-based chemotherapy, is indicated for the second-line treatment of patients with mCRC who have progressed on a first-line Avastin-containing regimen.\n\n\n\n\nLimitations of Use: Avastin is not indicated for adjuvant treatment of colon cancer [see Clinical Studies (14.2)].\n\n\n\n\n\n\n1.2   First-Line Non-Squamous Non–Small Cell Lung Cancer\nAvastin, in combination with carboplatin and paclitaxel, is indicated for the first-line treatment of patients with unresectable, locally advanced, recurrent or metastatic non–squamous non–small cell lung cancer (NSCLC).\n\n\n\n\n1.3   Recurrent Glioblastoma\nAvastin is indicated for the treatment of recurrent glioblastoma (GBM) in adults.\n\n\n\n\n1.4   Metastatic Renal Cell Carcinoma\nAvastin, in combination with interferon alfa, is indicated for the treatment of metastatic renal cell carcinoma (mRCC).\n\n\n\n\n1.5    Persistent, Recurrent, or Metastatic Cervical Cancer\nAvastin, in combination with paclitaxel and cisplatin or paclitaxel and topotecan, is indicated for the treatment of patients with persistent, recurrent, or metastatic cervical cancer.\n\n\n\n\n1.6   Epithelial Ovarian, Fallopian Tube, or Primary Peritoneal Cancer\nAvastin, in combination with carboplatin and paclitaxel, followed by Avastin as a single agent, is indicated for the treatment of patients with stage III or IV epithelial ovarian, fallopian tube, or primary peritoneal cancer following initial surgical resection. \t\t\t\t\t\t\t\t\nAvastin, in combination with paclitaxel, pegylated liposomal doxorubicin, or topotecan, is indicated for the treatment of patients with platinum-resistant recurrent epithelial ovarian, fallopian tube or primary peritoneal cancer who received no more than 2 prior chemotherapy regimens.\nAvastin, in combination with carboplatin and paclitaxel, or with carboplatin and gemcitabine, followed by Avastin as a single agent, is indicated for the treatment of patients with platinum-sensitive recurrent epithelial ovarian, fallopian tube, or primary peritoneal cancer.\n\n\n\n\n1.7 Hepatocellular Carcinoma\n\nAvastin, in combination with atezolizumab, is indicated for the treatment of patients with unresectable or metastatic hepatocellular carcinoma (HCC) who have not received prior systemic therapy.'

# Extract subsection for a particular disease from a drug's DailyMed 'INDICATIONS AND USAGE' section:
>>> disease = "Cervical Cancer"
# without subheading:
>>> biomarker_extraction.disease_content(dailyMedURL = url, disease = disease, header = False)
'\nAvastin, in combination with paclitaxel and cisplatin or paclitaxel and topotecan, is indicated for the treatment of patients with persistent, recurrent, or metastatic cervical cancer.'
# with subheading:
>>> biomarker_extraction.disease_content(dailyMedURL = url, disease = disease, header = True)
'1.5    Persistent, Recurrent, or Metastatic Cervical Cancer\nAvastin, in combination with paclitaxel and cisplatin or paclitaxel and topotecan, is indicated for the treatment of patients with persistent, recurrent, or metastatic cervical cancer.'

# Extract gene, protein, and drug labels from a string:
>>> txt = "Patients with EGFR or ALK genomic tumor aberrations should have disease progression on FDA-approved therapy for NSCLC harboring these aberrations prior to receiving TECENTRIQ."
>>> biomarker_extraction.gene_protein_chemical(text = txt, gene= 1, protein = 1, chemical = 1)
{'gene': ['EGFR', 'ALK genomic'], 'protein': ['EGFR', 'TECENTRIQ'], 'chemical': []}
>>> genProChe = biomarker_extraction.gene_protein_chemical(text = txt, gene= 1, protein = 1, chemical = 1)
# get genes
>>> genProChe.get("gene")
['EGFR', 'ALK genomic']
# get proteins
>>> genProChe.get("protein")
['EGFR', 'TECENTRIQ']
# only detect genes
>>> biomarker_extraction.gene_protein_chemical(text = txt, gene= 1, protein = 0, chemical = 0) 
{'gene': ['EGFR', 'ALK genomic']}

# Extract the subtree of the patterns 'in combination with' and 'used with':
>>> txt = "TECENTRIQ, in combination with cobimetinib and vemurafenib, is indicated for the treatment of patients with BRAF V600 mutation-positive unresectable or metastatic melanoma."
>>> biomarker_extraction.sent_subtree(text = txt)
['in combination with cobimetinib and vemurafenib']

# Detect if the metastatic disease is mentioned:
>>> txt = "TECENTRIQ, in combination with cobimetinib and vemurafenib, is indicated for the treatment of patients with BRAF V600 mutation-positive unresectable or metastatic melanoma."
>>> disease = "melanoma"
>>> biomarker_extraction.is_metastatic(text = txt, disease = disease)
True

```

#### Example Usage (negation detection)
The negation detection models require NVIDIA GPU, so either make sure your machine has an NVIDIA GPU, or turn the Hardware accelerator GPU on if using Google Colab. Download the two pre-trained models, [negCue](https://www.dropbox.com/s/3b8zhldmrx9niv4/negCue.zip?dl=0) and [negScope](https://www.dropbox.com/s/7nn1uptrvw66mn2/negScope.zip?dl=0), to your local computer from Dropbox. They are in zip format. You do not need to have a Dropbox account to download. 

Install necessary packages:
```bash
pip install biomarker_nlp
pip install transformers
pip install knockknock==0.1.7
pip install sentencepiece
```

Load the necessary packages and pre-trained models:
```python
>>> from biomarker_nlp import negation_cue_scope
>>> from biomarker_nlp.negation_negbert import * # This code MUST be run before loading the pre-trained negation models
>>> modelCue = torch.load('/path/to/negation/cue/detection/model') # path to the location where the model file is placed
>>> modelScope = torch.load('/path/to/negation/scope/detection/model') # path to the location where the model file is placed

>>> txt = "KEYTRUDA is not recommended for treatment of patients with PMBCL who require urgent cytoreductive therapy."
# detect negation cue
>>> negation_cue_scope.negation_detect(text = txt, modelCue = modelCue)
True
# extract the negation scope
>>> negation_cue_scope.negation_scope(text = txt, modelCue = modelCue, modelScope = modelScope)
['KEYTRUDA is', 'recommended for treatment of patients with PMBCL who']

```


## Copyright

Copyright 2021 Biomarker_NLP Project

Authors: Junxia Lin <jl2687@georgetown.edu>, Yuezheng He <yh694@georgetown.edu>, Subha Madhavan <subha.madhavan@georgetown.edu>, Chul Kim <chul.kim@gunet.georgetown.edu>, Simina M. Boca <smb310@georgetown.edu>
