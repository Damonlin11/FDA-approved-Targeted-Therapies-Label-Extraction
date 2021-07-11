# Biomarker Extraction - NLP

This repository contains a program and a package of custom modules used to extract biomarkers of FDA-approved targeted therapies listed on [NIH National Cancer Institute (NCI)](https://www.cancer.gov/about-cancer/treatment/types/targeted-therapies/targeted-therapies-fact-sheet) from their NCI webpage and DailyMed webpage(s). 

The program extracts a variety of biomarkers, including target therapies' names, disease names, drug brand names, genes, proteins, and medications. The biomarker detection and extraction tasks are based on the named-entity recognition (NER) pre-training models from [scispacy](https://github.com/allenai/scispacy). In addition, the program can recognize negated biomarkers. The package includes functions to detect negation from sentences by using two pre-trained negation models obtained from Aditya Khandelwal & Suraj Sawant's (2020) [NegBERT](https://github.com/adityak6798/Transformers-For-Negation-and-Speculation) program. The negation tasks include negation cue detection and negation scope extraction from sentences. The package also provides functions to detect key biomedical words for specific drugs and diseases, such as first-line treatment, accelerated approval, and metastatic. 

## Instructions to run the targeted-therapies-biomarker-extraction program:
1. Download the program and upload it to your Google Drive, open it with Google Colaboratory (Colab). Use the .ipynb one for Colab.
	
	(a) Colab is highly recommended! If you are new to Colab, please see instructions [here](https://developers.google.com/earth-engine/guides/python_install-colab#existing-notebook). In general, upload this notebook to your Google Drive, right-click the notebook, and select "open with" "Google Colaboratory". You may need to install the Google Colaboratory extension before that. Even quicker, use this [link](https://colab.research.google.com) to upload or open your Colab notebook. 
  
	(b) If you are using other Python environments, such as Jupyter Notebook or local Python IDLE, please make sure your machine brings NVIDIA GPU as the program will require CUBA. Most of Apple Mac's machines do not use NVIDIA GPU, therefore, it could not work. 

2. Before running the program, make sure the Hardware accelerator is in GPU. Select the "Runtime" tag on the top left of the page. Then, select "change runtime type". It will show a Notebook settings window, under "Hardware accelerator", select "GPU" and Save.

3. Mount the Google drive, run the program from the top to the end. It will generate a data frame that contains all the biomarkers data of the therapies and diseases. 
  
	(a) At the beginning of the program, you will need to mount google drive. When you run the mount code (the first chunk of the code), you will see a link, click the link, then select your current google drive account and click "allow" on the following page. After that, it will show an authorization code. Copy it and paste it to the box in the program and hit "Enter". 

#### Instructions to load the two pre-trained negation models on Colab:
1. Download the two pre-trained models, [negCue](https://aihub.cloud.google.com/u/1/p/2c29e298-0c75-435a-ae83-da80188b7f7b) and [negScope](https://aihub.cloud.google.com/u/1/p/0147a6f3-ddf7-498c-823d-014c3d1f1def), to your local computer from the AI hub. They are in tar.gz format. Currently, they are shared with georgetwon.edu users. 

2. Unzip these two files. Each should yield one single file. They are negCue (1.31 GB) and negScope(1.4 GB). If you encounter unzip error on Mac, please see [here](https://discussions.apple.com/thread/8187518) for a possible solution.

3. Upload both of them to your Google drive. It may take a bit of time.

4. Get the path to the model for loading the models in section 4 of the program. One way to find the path: 
	
	(a) Find the "Files" sign on the very left of the notebook window.
	
	(b) Start from the "drive" folder and navigate to these two model files. 
	
	(c) Click the three dots on the right of the file and select "Copy path". 
	
	(d) Paste the paths to section 4 to load the model. 

## Copyright

Copyright 2021 Biomarker_NLP Project

Authors: Junxia Lin <jl2687@georgetown.edu>, Yuezheng He <yh694@georgetown.edu>, Chul Kim <chul.kim@gunet.georgetown.edu>, Simina Boca <smb310@georgetown.edu>
