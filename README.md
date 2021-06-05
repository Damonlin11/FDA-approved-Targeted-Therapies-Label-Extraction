# Biomarker Extraction - NLP

Authors: Junxia Lin, Yuezheng He, Chul Kim, Siminar Boca

This repository contains a program and a package of custom modules used to automatically extract biomarkers of FDA-approved targeted therapies listed on [NIH National Cancer Institue (NCI)](https://www.cancer.gov/about-cancer/treatment/types/targeted-therapies/targeted-therapies-fact-sheet) from their NCI webpage and DailyMed webpage(s). 

The program extracts a variaty of biomarkers, including target therapies' name, disease name, drug brand name, gene, protein, and medication. These biomarker detection and extraction tasks are based on the named-entity recognition (NER) pre-training models from [scispacy](https://github.com/allenai/scispacy). In addition, the program is able to recognize negated biomarkers. The package includes functions to detect negation from sentences by using two pre-trained negation models obtained from Aditya Khandelwal & Suraj Sawant's [NegBERT](https://github.com/adityak6798/Transformers-For-Negation-and-Speculation) program. The negation tasks include negation cue detection and negation scope extraction from sentences. The package also provides function to detect a few other relations between the drug and disease, such as first-line treatment, accerelated approval, and metastatics. 

## Instructions to run the targeted-therapies-biomarker-extraction program:
1. Download the script and upload it to your Google Colaboratory (Colab). 
	
	(a). Colab is highly recommended! If you are new to Colab, please see instructions [here](https://developers.google.com/earth-engine/guides/python_install-colab#existing-notebook). In general, upload this notebook to your Google drive, right click the notebook, and select "open with" "Google Colaboratory". 
  
	(b). If you are using other interprater, such as Jupyter Notebook or local Python IDLE, please make sure your machine brings NVIDIA GPU as the program will require CUBA. Most of Apple Mac's machines do not use NVIDIA GPU, therefore, it could not work. 

2. On Colab, before runing the program, make sure the Hardware accelerator is in GPU. Select "Runtime" tag on the top-left of the page. Then, select "change runtime type". You will Notebook settings, under "Hardware accelerator", select "GPU" and Save.

3. Run the program from the top and all the way to the end. It will generate a dataframe that contains all the biomarkers data corresponding the therapies and diseases. 
  
	(a). At the begining of the program, you will need to mount the google drive. When you run the mount code (the first code block), you will see a link, click the link, then select your current google drive account and click "allow" in the following page. After that, it will show a authorization code. Copy it and paste it to the box in the script and hit "Enter". 
