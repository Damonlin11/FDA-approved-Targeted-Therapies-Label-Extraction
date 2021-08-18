# Biomarker Extraction - NLP

This repository contains a program and a package of custom modules used to extract biomarkers for each FDA-approved targeted cancer therapy listed at [NIH National Cancer Institute (NCI)](https://www.cancer.gov/about-cancer/treatment/types/targeted-therapies/targeted-therapies-fact-sheet) from its NCI webpage (eg https://www.cancer.gov/about-cancer/treatment/drugs/lanreotideacetate) and corresponding DailyMed webpage(s) (eg https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=6e4a41fd-a753-4362-87ee-8cc56ed3660d). 

The program extracts a variety of biomarkers, including: gene/protein; therapy; disease; drug label; NDC code; other drugs in approved combination therapies with selected drug; genes/proteins that, when altered, serve as biomarkers of resistance (via statements of negation, indicating that a drug should not be given for a specific biomarker); whether approval was accelerated (indicating lower evidence threshold and requirement for further confirmatory studies); whether the drug is indicated for first-line treatment; and whether the drug is indicated for metastatic disease. The biomarker detection and extraction tasks are based on the named-entity recognition (NER) pre-trained models from [scispacy](https://github.com/allenai/scispacy). In addition, the program can recognize negated biomarkers. The package includes functions to detect negation by using two pre-trained negation models obtained from Aditya Khandelwal & Suraj Sawant's (2020) [NegBERT](https://github.com/adityak6798/Transformers-For-Negation-and-Speculation) program. The negation tasks include negation cue detection and negation scope extraction from sentences. The package also provides functions to detect key clinical terminology for specific drugs and diseases, such as first-line treatment, accelerated approval, and metastatic disease. 

## Instructions to run the targeted-therapies-biomarker-extraction program:
1. Download the program and upload it to your Google Drive, open it with Google Colaboratory (Colab). Use the .ipynb file with Colab.
	
	(a) Colab is highly recommended! If you are new to Colab, please see instructions [here](https://developers.google.com/earth-engine/guides/python_install-colab#existing-notebook). In general, upload this notebook to your Google Drive, right-click the notebook, and select "open with" "Google Colaboratory". You may need to install the Google Colaboratory extension first. As a faster option, use this [link](https://colab.research.google.com) to upload or open your Colab notebook. 
  
	(b) If you are using other Python environments, such as Jupyter Notebook or local Python IDLE, please make sure your machine has an NVIDIA GPU as the program will require CUBA. Most of Apple Mac's machines do not use NVIDIA GPU, meaning that the program will not work on them. 

2. Before running the program, make sure the Hardware accelerator selected is the GPU. Select the "Runtime" tag on the top left of the page. Then, select "change runtime type". It will show a Notebook settings window; under "Hardware accelerator", select "GPU," then save.

3. Mount the Google drive and run the program from the beginning to the end. It will generate a data frame that contains all the biomarker data of the therapies and diseases. 
  
	(a) At the beginning of the program, you will need to mount the Google drive. When you run the mount code (the first chunk of the code), you will see a link. Click this link, then select your current google drive account and click "allow" on the following page. After that, it will show an authorization code. Copy it and paste it into the box in the program and hit "Enter". 

#### Instructions to load the two pre-trained negation models on Colab:
1. Download the two pre-trained models, [negCue](https://www.dropbox.com/s/3b8zhldmrx9niv4/negCue.zip?dl=0) and [negScope](https://www.dropbox.com/s/7nn1uptrvw66mn2/negScope.zip?dl=0), to your local computer from Dropbox. They are in zip format. You do not need to have a Dropbox account to download. 

	You also can download them using the following links:
	negCue: https://www.dropbox.com/s/3b8zhldmrx9niv4/negCue.zip?dl=0
	negScope: https://www.dropbox.com/s/7nn1uptrvw66mn2/negScope.zip?dl=0
	
2. Unzip these two files if they are zipped. Each should yield one single file. They are negCue (1.31 GB) and negScope(1.4 GB). If you encounter unzip errors on a Mac, please see [here](https://discussions.apple.com/thread/8187518) for a possible solution.

3. Upload both of them to your Google drive. This may take some time.

4. Get the path to the model for loading the models in section 4 of the program. One way to find the path is as follows: 
	
	(a) Find the "Files" sign on the very left of the notebook window.
	
	(b) Start from the "drive" folder and navigate to these two model files. 
	
	(c) Click the three dots to the right of the file and select "Copy path". 
	
	(d) Paste the paths to section 4 to load the model. 

## Copyright

Copyright 2021 Biomarker_NLP Project

Authors: Junxia Lin <jl2687@georgetown.edu>, Yuezheng He <yh694@georgetown.edu>, Subha Madhavan <subha.madhavan@georgetown.edu>, Chul Kim <chul.kim@gunet.georgetown.edu>, Simina M. Boca <smb310@georgetown.edu>
