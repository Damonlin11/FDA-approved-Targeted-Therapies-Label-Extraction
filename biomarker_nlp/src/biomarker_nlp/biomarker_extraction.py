#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import lxml.html
import re
import scispacy
import spacy
import en_ner_craft_md
import en_ner_jnlpba_md
import en_ner_bionlp13cg_md
nlp_craft = en_ner_craft_md.load()
nlp_jnlpha = en_ner_jnlpba_md.load()
nlp_bionlp13cg = en_ner_bionlp13cg_md.load()

def disease_content(dailyMedURL, disease, header = False):
  """Extract subsection for a particular disease from a drug's DailyMed 'INDICATIONS AND USAGE' section.

  Parse the URL link using the lxml library. Locate the subsection that discusses the disease in the 'INDICATIONS AND USAGE' section from the HTML's tree structure. 
  If the header argument is set to False, only the text content will be extracted. If the header argument is set to True, the whole subsection including the subheading and its text content will be extracted.

  Parameters
  ----------
  dailyMedURL : str
      An URL link to a drug's DailyMed information page and quoted ("") as a string.
  disease : str
      The name of a disease whose text information will be extracted from the 'INDICATIONS AND USAGE' section.
  header : bool, optional
      Extract the subheading, by default False. 
      If True, the subheading will be extracted. 
      If False, only the text content will be extracted.

  Returns
  -------
  None or str
      Return the subsection text with or without the subheading. 
      If no associated subsection of the disease is found, return None.

  Examples
  --------
  Import the module

  >>> from biomarker_nlp import biomarker_extraction
  
  Example (without subheading)

  >>> url = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=939b5d1f-9fb2-4499-80ef-0607aa6b114e"
  >>> disease = "Cervical Cancer"
  >>> biomarker_extraction.disease_content(dailyMedURL = url, disease = disease, header = False)
  '\\nAvastin, in combination with paclitaxel and cisplatin or paclitaxel and topotecan, is indicated for the treatment of patients with persistent, recurrent, or metastatic cervical cancer.'
  
  Example (with subheading)
  
  >>> url = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=939b5d1f-9fb2-4499-80ef-0607aa6b114e"
  >>> disease = "Cervical Cancer"
  >>> biomarker_extraction.disease_content(dailyMedURL = url, disease = disease, header = True)
  '1.5    Persistent, Recurrent, or Metastatic Cervical Cancer\\nAvastin, in combination with paclitaxel and cisplatin or paclitaxel and topotecan, is indicated for the treatment of patients with persistent, recurrent, or metastatic cervical cancer.'
  
  
  """
   
  # parse the drug information page's link
  dailyMedRp = requests.get(dailyMedURL)
  dailyMedPage = lxml.html.fromstring(dailyMedRp.text)

  # locate the 'INDICATIONS AND USAGE' section in DailyMed and extract the text content by certain cancer type. 
  usagePath = "//li[a[contains(text(),'INDICATIONS AND USAGE')]]/div/div[h2[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'" + disease.lower() + "')]]"
  dailyMedDisContent = dailyMedPage.xpath(usagePath)

  # extract text content of the matched disease
  if len(dailyMedDisContent)>0:
    dailyMedDisContentStr = ""                     
    for disContent in dailyMedDisContent:
      dailyMedDisContentStr = dailyMedDisContentStr + disContent.text_content() + ' '                              
    dailyMedDisContentStr = dailyMedDisContentStr.strip()


    if header == False:
      headerPath = "//li[a[contains(text(),'INDICATIONS AND USAGE')]]/div/div[h2[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'" + disease.lower() + "')]]//h2"
      headerContent = dailyMedPage.xpath(headerPath)
      dailyMedDisContentStr = dailyMedDisContentStr.replace(headerContent[0].text_content(), "")
      return dailyMedDisContentStr
    else: return dailyMedDisContentStr
  
  else: return None


def section_content(dailyMedURL, section):
  """Extract a whole section text content from the drug's DailyMed information page excluding the section heading.

  Parse the URL link using the lxml library. Locate the section using the section's heading from the HTML's tree structure. Extract the text content of the section excluding the heading.

  Parameters
  ----------
  dailyMedURL : str
      An URL link to a drug DailyMed information page and quoted ("") as a string.
  section : str
      The header of the section.

  Returns
  -------
  None or str
      Return section content. If no such a section is found, return None.

  Examples
  --------
  Import the module

  >>> from biomarker_nlp import biomarker_extraction
  
  Example
  
  >>> url = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=43a4d7f8-48ae-4a63-9108-2fa8e3ea9d9c&audience=consumer"
  >>> sectionHeader = "INDICATIONS AND USAGE"
  >>> biomarker_extraction.section_content(dailyMedURL = url, section = sectionHeader)
  '1.1	Gastrointestinal Stromal Tumor
  SUTENT is indicated for the treatment of adult patients with gastrointestinal stromal tumor (GIST) after disease progression on or intolerance to imatinib mesylate.
  1.2	Advanced Renal Cell Carcinoma
  SUTENT is indicated for the treatment of adult patients with advanced renal cell carcinoma (RCC).
  1.3	Adjuvant Treatment of Renal Cell Carcinoma
  SUTENT is indicated for the adjuvant treatment of adult patients at high risk of recurrent RCC following nephrectomy.
  1.4	Advanced Pancreatic Neuroendocrine Tumors
  SUTENT is indicated for the treatment of progressive, well-differentiated pancreatic neuroendocrine tumors (pNET) in adult patients with unresectable locally advanced or metastatic disease.'

  See Also
  --------
  disease_content
  """
  
  # parse the drug information page's link
  dailyMedRp = requests.get(dailyMedURL)
  dailyMedPage = lxml.html.fromstring(dailyMedRp.text)

  # locate the section in DailyMed and extract the text content. 
  usagePath = "//li[a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'" + section.lower() + "')]]/div"
  dailyMedSecContent = dailyMedPage.xpath(usagePath)

  # extract text content of the section
  if len(dailyMedSecContent)>0:
    dailyMedSecContentStr = ""                     
    for secContent in dailyMedSecContent:
      dailyMedSecContentStr = dailyMedSecContentStr + secContent.text_content() + ' '                              
    dailyMedSecContentStr = dailyMedSecContentStr.strip()

    return dailyMedSecContentStr

  else: return None


def drug_brand_label(dailyMedURL):
  """Extract drug label at the drug dailyMed label information page.

  Parse the URL link using the lxml library. Locate and extract the drug label from the HTML's tree structure. 

  Parameters
  ----------
  dailyMedURL : str
      An URL link to a drug DailyMed information page
      and quoted ("") as a string.

  Returns
  -------
  str
      Return drug label. 
      If no drug label is found, return a zero-length string (""). 

  Examples
  --------
  Import the module

  >>> from biomarker_nlp import biomarker_extraction
  
  Example
  
  >>> url = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=43a4d7f8-48ae-4a63-9108-2fa8e3ea9d9c&audience=consumer"
  >>> biomarker_extraction.drug_brand_label(dailyMedURL = url)
  'SUTENT- sunitinib malate capsule'

  See Also
  --------
  ndc_code
  """

  # parse the drug information page's link
  dailyMedRp = requests.get(dailyMedURL)
  dailyMedPage = lxml.html.fromstring(dailyMedRp.text)

  # extract the brand label
  therBrName = dailyMedPage.xpath("//span[@id='drug-label']/text()")
  if len(therBrName) > 0:
    drugLabel = therBrName[0]
  else: drugLabel = ""
  return drugLabel


def ndc_code(dailyMedURL):
  """Extract NDC code(s) from the drug dailyMed label information page.

  Parse the URL link using the lxml library. Locate and extract the NDC codes from the HTML's tree structure. It returns all the codes found in a string. The codes are separated by commas. 

  Parameters
  ----------
  dailyMedURL : str
      An URL link to a drug DailyMed information page
      and quoted ("") as a string.

  Returns
  -------
  str
      Return NDC codes(s) in a string. If more than one code is found, codes are separated by commas. 
  
  Examples
  --------
  Import the module

  >>> from biomarker_nlp import biomarker_extraction
  
  Example
  
  >>> url = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=43a4d7f8-48ae-4a63-9108-2fa8e3ea9d9c&audience=consumer"
  >>> biomarker_extraction.ndc_code(dailyMedURL = url)
  '0069-0550-38, 0069-0770-38, 0069-0830-38, 0069-0980-38'

  """

  # parse the drug information page's link
  dailyMedRp = requests.get(dailyMedURL)
  dailyMedPage = lxml.html.fromstring(dailyMedRp.text)

  # extract the NDC codes
  codeList = []
  NDCCode = dailyMedPage.xpath("//span[@id='item-code-s']/text()")
  if NDCCode:
    NDCCode = NDCCode[0]
    NDCCodeList = NDCCode.split(',')
    for c in range(len(NDCCodeList)):
      NDCCodeList[c] = NDCCodeList[c].replace('\n', '')
      NDCCodeList[c] = NDCCodeList[c].replace(' ', '')
    codeList.extend(NDCCodeList)

  # extract the NDC code (view more)
  NDCCodeMore = dailyMedPage.xpath("//span[@id='item-code-s']//div[@class = 'more-codes']/span/text()")
  if NDCCodeMore:
    NDCCodeMore = NDCCodeMore[0]
    NDCCodeMoreList = NDCCodeMore.split(',')
    for m in range(len(NDCCodeMoreList)):
      NDCCodeMoreList[m] = NDCCodeMoreList[m].replace('\n', '')
      NDCCodeMoreList[m] = NDCCodeMoreList[m].replace(' ', '')
    
    codeList.extend(NDCCodeMoreList)
  ndcCode = ', '.join(x for x in codeList if x)

  return ndcCode


def gene_protein_chemical(text, gene= 1, protein = 1, chemical = 1):
  """Extract gene, protein, and drug labels from a string.

  The function uses three pre-trained NER models from scispacy. Please see https://allenai.github.io/scispacy/. We use en_ner_craft_md model to recognize genes. Entities labeled with "GGP" in this model are categorized as genes. We use the en_ner_jnlpba_md model to recognize proteins. Entities labeled with "PROTEIN" in this model are categorized as proteins. We use en_ner_bionlp13cg_md model to recognize drugs. Entities labeled with "SIMPLE_CHEMICAL" in this model are categorized as drugs.

  Parameters
  ----------
  text : str
      A single string. 
  gene : int, optional
      Extract genes, by default 1.
      0: do not extract genes. 1: extract genes. 
  protein : int, optional
      Extract proteins, by default 1.
      0: do not extract proteins. 1: extract proteins. 
  chemical : int, optional
      Extract simple chemicals, by default 1. 
      0: do not extract simple chemicals. 1: extract simple chemicals. 

  Returns
  -------
  dic
      Return a dictionary in which "gene", "proteins", or/and "chemical" are
      the keys, lists of genes, proteins, or/and chemicals are the values.
  
  Examples
  --------
  Install the necessary packages and pre-trained models
  
  >>> # If using Colab Notebook, use !pip
  $ pip install scispacy
  $ pip install -U spacy==2.3.1
  $ pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.3.0/en_ner_craft_md-0.3.0.tar.gz
  $ pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.3.0/en_ner_jnlpba_md-0.3.0.tar.gz
  $ pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.3.0/en_ner_bionlp13cg_md-0.3.0.tar.gz
  
  Import the module
  
  >>> from biomarker_nlp import biomarker_extraction
  
  Example (Recognize entities)
  
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
  # Only detect genes
  >>> biomarker_extraction.gene_protein_chemical(text = txt, gene= 1, protein = 0, chemical = 0) 
  {'gene': ['EGFR', 'ALK genomic']}
  
  """
  
  geneProteinChemicalDic = {}
  geneList = []
  proteinList = []
  chemicalList = []

  # extract genes
  if gene== 1:
    doc = nlp_craft(text)
    # filter gene and gene product
    for entity in doc.ents:
      if entity.label_=='GGP':
         #print(entity.text + " GGP")
         geneList.append(entity.text)
    geneProteinChemicalDic['gene'] = geneList

  # extract proteins
  if protein == 1:
    doc = nlp_jnlpha(text)
    # filter protein
    for entity in doc.ents:
      if entity.label_=='PROTEIN':
        #print(entity.text + " PROTEIN")
        proteinList.append(entity.text)
    geneProteinChemicalDic['protein'] = proteinList

  # extract drugs (SIMPLE_CHEMICAL)
  if chemical == 1:
    doc = nlp_bionlp13cg(text)
    # filter drug (SIMPLE_CHEMICAL)
    for entity in doc.ents:
      if entity.label_=='SIMPLE_CHEMICAL':
        #print(entity.text + " SIMPLE_CHEMICAL")
        chemicalList.append(entity.text)
    geneProteinChemicalDic['chemical'] = chemicalList

  return geneProteinChemicalDic


def sent_subtree(text):
  """Extract the subtree of the patterns 'in combination with' and 'used with' based on dependency parsing. 

  The function uses pattern match to recognize two patterns ('in combination with' and 'used with') from a sentence. Once such a pattern is recognized, the sentence is parsed as a dependency tree by scispacy's nlp_bionlp13cg model which is based on Stanford Dependency Converter. The "combination" or "used" is used as a headword to extract its subtree. 

  Parameters
  ----------
  text : str
      A single sentence.

  Returns
  -------
  list
      Return a list of subtree clauses in string. 
  
  Examples
  --------
  Install the necessary packages and pre-trained models

  >>> # If using Colab Notebook, use !pip
  $ pip install scispacy
  $ pip install -U spacy==2.3.1
  $ pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.3.0/en_ner_bionlp13cg_md-0.3.0.tar.gz
  
  Import the module
  
  >>> from biomarker_nlp import biomarker_extraction
  
  Example (extract the subtree)
  
  >>> txt = "TECENTRIQ, in combination with cobimetinib and vemurafenib, is indicated for the treatment of patients with BRAF V600 mutation-positive unresectable or metastatic melanoma."
  >>> biomarker_extraction.sent_subtree(text = txt)
  ['in combination with cobimetinib and vemurafenib']
  
  Another example
  
  >>> txt = "BAVENCIO in combination with axitinib is indicated for the first-line treatment of patients with advanced renal cell carcinoma (RCC)."
  >>> biomarker_extraction.sent_subtree(text = txt)
  ['in combination with axitinib']

  """

  # pattern match
  patterns = [r'\b(?i)'+'in combination with'+r'\b',
          r'\b(?i)'+'used with'+r'\b']

  subPatterns = ['combination', 'used']

  schemes = []
  doc = nlp_bionlp13cg(text)
  flag = 0
  # if no pattern present in sentence
  for pat in patterns:
      
      if re.search(pat, text) != None:
          flag = 1
          break

  if flag == 0:
      return schemes

  # iterating over sentence tokens
  for token in doc:

      for pat in subPatterns:
              
          # if we get a pattern match
          if re.search(pat, token.text) != None:

              subtree = [t.text for t in token.subtree]
              subtreeSent = ' '.join(word for word in subtree)
              schemes.append(subtreeSent)
  return schemes  


def is_firstline(text, medicine, disease):
  """Detect if first-line treatment is mentioned with a medicine in a sentence.

  Use keyword matching to detect if the keywords "first-line treatment" or "first-or second-line treatment", medicine name, and disease name all appear in the sentence.

  Parameters
  ----------
  text : str
      A single sentence.
  medicine : str
      A medicine's name.

  Returns
  -------
  bool
      Return True if the medicine and first-line treatment are mentioned in the sentence, False otherwise. 
  
  Examples
  --------
  Import the module

  >>> from biomarker_nlp import biomarker_extraction
  
  Example
  
  >>> txt = "TECENTRIQ, in combination with carboplatin and etoposide, is indicated for the first-line treatment of adult patients with extensive-stage small cell lung cancer (ES-SCLC)."
  >>> medicine = "TECENTRIQ"
  >>> disease = "small cell lung cancer"
  >>> biomarker_extraction.is_firstline(text = txt, medicine = medicine, disease = disease)
  True

  """
  text = text.lower()
  medicine = medicine.lower()
  disease = disease.lower()
  if medicine in text and ('first-line treatment' in text or 'first-or second-line treatment' in text) and disease in text:
    return True
  else:
    return False


def is_accelerated_approval(text):
  """Detect if the drug is accelerated approval. 

  Use keyword matching to detect if the keyword "accelerated approval" appears in the sentence.

  Parameters
  ----------
  text : str
      A string. 

  Returns
  -------
  bool
      Return True if "accelerated approval" is mentioned in the string, False otherwise. 
  
  Examples
  --------
  Import the module

  >>> from biomarker_nlp import biomarker_extraction
  
  Example
  
  >>> txt = "This indication is approved under accelerated approval based on progression free survival."
  >>> biomarker_extraction.is_accelerated_approval(text = txt)
  True

  """

  text = text.lower()
  if 'accelerated approval' in text:
    return True
  else:
    return False


def is_accelerated_approval_rate(text):
  """Detect if the drug is accelerated approval based on response rate. 

  Use keyword matching to detect if the keywords "accelerated approval" and "response rate" appear in the sentence.

  Parameters
  ----------
  text : str
      A string.

  Returns
  -------
  bool
      Return True if "accelerated approval" and "response rate" are mentioned in the string, False otherwise. 
  
  Examples
  --------
  Import the module

  >>> from biomarker_nlp import biomarker_extraction
  
  Example
  
  >>> txt = "This indication is approved under accelerated approval based on tumor response rate and durability of response."
  >>> biomarker_extraction.is_accelerated_approval_rate(text = txt)
  True

  """

  text = text.lower()
  if 'accelerated approval' in text and 'response rate' in text:
    return True
  else:
    return False


def is_metastatic(text, disease):
  """Detect if the metastatic disease is mentioned.

  Use keyword matching to detect if the combination of keywords "metastatic" or "unresectable" with the disease's name appears in the sentence.

  Parameters
  ----------
  text : str
      A string or sentence
  disease : str
      A disease's name

  Returns
  -------
  bool
      Return True if "metastatic" or "unresectable" and the disease are mentioned together, False otherwise. 
  
  Examples
  --------
  Import the module

  >>> from biomarker_nlp import biomarker_extraction
  
  Example
  
  >>> txt = "TECENTRIQ, in combination with bevacizumab, is indicated for the treatment of patients with unresectable or metastatic hepatocellular carcinoma (HCC) who have not received prior systemic therapy."
  >>> disease = "hepatocellular carcinoma"
  >>> biomarker_extraction.is_metastatic(text = txt, disease = disease)
  True

  """

  text = text.lower()
  disease = disease.lower()
  if 'metastatic' + " " + disease in text or 'unresectable' + " " + disease in text:
    return True
  else:
    return False


def targeted_therapy_url(url):
  """Extract the targeted therapies' link from NCI page.

  Use the lxml library to parse the URL link and xpath to find the therapy's link in the "what-targeted-therapies-have-been-approved-for-specific-types-of-cancer" section.

  Parameters
  ----------
  url : str
      An URL link to a targeted therapies fact sheet.

  Returns
  -------
  list
      Return a list of targeted therapies' URL links.

  Examples
  --------
  Import the module

  >>> from biomarker_nlp import biomarker_extraction
  
  Example
  
  >>> url_nci = "https://www.cancer.gov/about-cancer/treatment/types/targeted-therapies/targeted-therapies-fact-sheet"
  >>> biomarker_extraction.targeted_therapy_url(url = url_nci)
  ['/about-cancer/treatment/drugs/atezolizumab', '/about-cancer/treatment/drugs/nivolumab', '/about-cancer/treatment/drugs/avelumab', '/about-cancer/treatment/drugs/pembrolizumab', '/about-cancer/treatment/drugs/erdafitinib', 'https://www.cancer.gov/about-cancer/treatment/drugs/enfortumabvedotin-ejfv', '/about-cancer/treatment/drugs/sacituzumabgovitecan-hziy', '/about-cancer/treatment/drugs/bevacizumab', '/about-cancer/treatment/drugs/everolimus', '/about-cancer/treatment/drugs/everolimus', '/about-cancer/treatment/drugs/tamoxifencitrate', '/about-cancer/treatment/drugs/toremifene', '/about-cancer/treatment/drugs/trastuzumab', '/about-cancer/treatment/drugs/fulvestrant', '/about-cancer/treatment/drugs/anastrozole', '/about-cancer/treatment/drugs/exemestane', '/about-cancer/treatment/drugs/lapatinibditosylate', '/about-cancer/treatment/drugs/letrozole', '/about-cancer/treatment/drugs/pertuzumab', '/about-cancer/treatment/drugs/ado-trastuzumab-emtansine', '/about-cancer/treatment/drugs/palbociclib', '/about-cancer/treatment/drugs/ribociclib', '/about-cancer/treatment/drugs/neratinibmaleate', '/about-cancer/treatment/drugs/abemaciclib', '/about-cancer/treatment/drugs/olaparib', 'https://www.cancer.gov/about-cancer/treatment/drugs/talazoparibtosylate', '/about-cancer/treatment/drugs/atezolizumab', '/about-cancer/treatment/drugs/alpelisib', 'https://www.cancer.gov/about-cancer/treatment/drugs/famtrastuzumabderuxtecan-nxki', 'https://www.cancer.gov/about-cancer/treatment/drugs/tucatinib', 'https://www.cancer.gov/about-cancer/treatment/drugs/sacituzumabgovitecan-hziy', '/about-cancer/treatment/drugs/pertuzumabtrastuzumabandhyaluronidase-zzxf', '/about-cancer/treatment/drugs/pembrolizumab', '/about-cancer/treatment/drugs/margetuximab-cmkb', '/about-cancer/treatment/drugs/bevacizumab', '/about-cancer/treatment/drugs/pembrolizumab', '/about-cancer/treatment/drugs/cetuximab', '/about-cancer/treatment/drugs/panitumumab', '/about-cancer/treatment/drugs/bevacizumab', '/about-cancer/treatment/drugs/ziv-aflibercept', '/about-cancer/treatment/drugs/regorafenib', '/about-cancer/treatment/drugs/ramucirumab', '/about-cancer/treatment/drugs/nivolumab', '/about-cancer/treatment/drugs/ipilimumab', '/about-cancer/treatment/drugs/encorafenib', '/about-cancer/treatment/drugs/pembrolizumab', '/about-cancer/treatment/drugs/imatinibmesylate', '/about-cancer/treatment/drugs/lanreotideacetate', '/about-cancer/treatment/drugs/avelumab', '/about-cancer/treatment/drugs/lutetiumlu177-dotatate', '/about-cancer/treatment/drugs/iobenguanei131', '/about-cancer/treatment/drugs/pembrolizumab', '/about-cancer/treatment/drugs/lenvatinibmesylate', '/about-cancer/treatment/drugs/dostarlimab-gxly', '/about-cancer/treatment/drugs/trastuzumab', '/about-cancer/treatment/drugs/ramucirumab', '/about-cancer/treatment/drugs/pembrolizumab', '/about-cancer/treatment/drugs/nivolumab', '/about-cancer/treatment/drugs/famtrastuzumabderuxtecan-nxki', '/about-cancer/treatment/drugs/cetuximab', '/about-cancer/treatment/drugs/pembrolizumab', '/about-cancer/treatment/drugs/nivolumab', '/about-cancer/treatment/drugs/imatinibmesylate', '/about-cancer/treatment/drugs/sunitinibmalate', '/about-cancer/treatment/drugs/regorafenib', 'https://www.cancer.gov/about-cancer/treatment/drugs/avapritinib', '/about-cancer/treatment/drugs/ripretinib', '/about-cancer/treatment/drugs/denosumab', '/about-cancer/treatment/drugs/pexidartinib', '/about-cancer/treatment/drugs/bevacizumab', '/about-cancer/treatment/drugs/sorafenibtosylate', '/about-cancer/treatment/drugs/sunitinibmalate', '/about-cancer/treatment/drugs/pazopanibhydrochloride', '/about-cancer/treatment/drugs/temsirolimus', '/about-cancer/treatment/drugs/everolimus', '/about-cancer/treatment/drugs/axitinib', '/about-cancer/treatment/drugs/nivolumab', '/about-cancer/treatment/drugs/cabozantinib-s-malate', '/about-cancer/treatment/drugs/lenvatinibmesylate', '/about-cancer/treatment/drugs/ipilimumab', '/about-cancer/treatment/drugs/pembrolizumab', '/about-cancer/treatment/drugs/avelumab', '/about-cancer/treatment/drugs/tivozanibhydrochloride', '/publications/dictionaries/cancer-drug/def/tretinoin', '/about-cancer/treatment/drugs/imatinibmesylate', '/about-cancer/treatment/drugs/dasatinib', '/about-cancer/treatment/drugs/nilotinib', '/about-cancer/treatment/drugs/bosutinib', '/about-cancer/treatment/drugs/rituximab', '/about-cancer/treatment/drugs/alemtuzumab', '/about-cancer/treatment/drugs/ofatumumab', '/about-cancer/treatment/drugs/obinutuzumab', '/about-cancer/treatment/drugs/ibrutinib', '/about-cancer/treatment/drugs/idelalisib', '/about-cancer/treatment/drugs/blinatumomab', '/about-cancer/treatment/drugs/venetoclax', '/about-cancer/treatment/drugs/ponatinibhydrochloride', '/about-cancer/treatment/drugs/midostaurin', '/about-cancer/treatment/drugs/enasidenibmesylate', '/about-cancer/treatment/drugs/inotuzumabozogamicin', '/about-cancer/treatment/drugs/tisagenlecleucel', '/about-cancer/treatment/drugs/gemtuzumabozogamicin', '/about-cancer/treatment/drugs/rituximabandhyaluronidasehuman', '/about-cancer/treatment/drugs/ivosidenib', '/about-cancer/treatment/drugs/duvelisib', '/about-cancer/treatment/drugs/moxetumomabpasudotoxtdfk', '/about-cancer/treatment/drugs/glasdegibmaleate', '/about-cancer/treatment/drugs/gilteritinibfumarate', '/about-cancer/treatment/drugs/tagraxofusp-erzs', '/about-cancer/treatment/drugs/acalabrutinib', '/about-cancer/treatment/drugs/sorafenibtosylate', '/about-cancer/treatment/drugs/regorafenib', '/about-cancer/treatment/drugs/nivolumab', '/about-cancer/treatment/drugs/lenvatinibmesylate', '/about-cancer/treatment/drugs/pembrolizumab', '/about-cancer/treatment/drugs/cabozantinib-s-malate', '/about-cancer/treatment/drugs/ramucirumab', '/about-cancer/treatment/drugs/ipilimumab', 'https://www.cancer.gov/about-cancer/treatment/drugs/pemigatinib', '/about-cancer/treatment/drugs/atezolizumab', '/about-cancer/treatment/drugs/bevacizumab', '/about-cancer/treatment/drugs/bevacizumab', '/about-cancer/treatment/drugs/crizotinib', '/about-cancer/treatment/drugs/erlotinibhydrochloride', '/about-cancer/treatment/drugs/gefitinib', '/about-cancer/treatment/drugs/afatinibdimaleate', '/about-cancer/treatment/drugs/ceritinib', '/about-cancer/treatment/drugs/ramucirumab', '/about-cancer/treatment/drugs/nivolumab', '/about-cancer/treatment/drugs/pembrolizumab', '/about-cancer/treatment/drugs/osimertinib', '/about-cancer/treatment/drugs/necitumumab', '/about-cancer/treatment/drugs/alectinib', '/about-cancer/treatment/drugs/atezolizumab', '/about-cancer/treatment/drugs/brigatinib', '/about-cancer/treatment/drugs/trametinib', '/about-cancer/treatment/drugs/dabrafenib', '/about-cancer/treatment/drugs/durvalumab', '/about-cancer/treatment/drugs/dacomitinib', '/about-cancer/treatment/drugs/lorlatinib', 'https://www.cancer.gov/about-cancer/treatment/drugs/entrectinib', '/about-cancer/treatment/drugs/capmatinibhydrochloride', '/about-cancer/treatment/drugs/ipilimumab', '/about-cancer/treatment/drugs/selpercatinib', '/about-cancer/treatment/drugs/pralsetinib', '/about-cancer/treatment/drugs/cemiplimab-rwlc', '/about-cancer/treatment/drugs/tepotinibhydrochloride', '/about-cancer/treatment/drugs/ibritumomabtiuxetan', '/about-cancer/treatment/drugs/denileukindiftitox', '/about-cancer/treatment/drugs/brentuximabvedotin', '/about-cancer/treatment/drugs/rituximab', '/about-cancer/treatment/drugs/vorinostat', '/about-cancer/treatment/drugs/romidepsin', '/about-cancer/treatment/drugs/bexarotene', '/about-cancer/treatment/drugs/bortezomib', '/about-cancer/treatment/drugs/pralatrexate', '/about-cancer/treatment/drugs/ibrutinib', '/about-cancer/treatment/drugs/siltuximab', '/about-cancer/treatment/drugs/idelalisib', '/about-cancer/treatment/drugs/belinostat', '/about-cancer/treatment/drugs/obinutuzumab', '/about-cancer/treatment/drugs/nivolumab', '/about-cancer/treatment/drugs/pembrolizumab', '/about-cancer/treatment/drugs/rituximabandhyaluronidasehuman', '/about-cancer/treatment/drugs/copanlisibhydrochloride', '/about-cancer/treatment/drugs/axicabtageneciloleucel', '/about-cancer/treatment/drugs/acalabrutinib', '/about-cancer/treatment/drugs/tisagenlecleucel', '/about-cancer/treatment/drugs/venetoclax', '/about-cancer/treatment/drugs/mogamulizumabkpkc', '/about-cancer/treatment/drugs/duvelisib', '/about-cancer/treatment/drugs/polatuzumabvedotin-piiq', 'https://www.cancer.gov/about-cancer/treatment/drugs/zanubrutinib', '/about-cancer/treatment/drugs/tazemetostathydrobromide', '/about-cancer/treatment/drugs/selinexor', '/about-cancer/treatment/drugs/tafasitamab-cxix', '/about-cancer/treatment/drugs/brexucabtageneautoleucel', '/about-cancer/treatment/drugs/crizotinib', '/about-cancer/treatment/drugs/umbralisibtosylate', '/about-cancer/treatment/drugs/lisocabtagenemaraleucel', '/about-cancer/treatment/drugs/loncastuximabtesirine-lpyl', '/about-cancer/treatment/drugs/ipilimumab', '/about-cancer/treatment/drugs/nivolumab', '/about-cancer/treatment/drugs/pembrolizumab', '/about-cancer/treatment/drugs/bortezomib', '/about-cancer/treatment/drugs/carfilzomib', '/about-cancer/treatment/drugs/panobinostat', '/about-cancer/treatment/drugs/daratumumab', '/about-cancer/treatment/drugs/ixazomibcitrate', '/about-cancer/treatment/drugs/elotuzumab', '/about-cancer/treatment/drugs/selinexor', 'https://www.cancer.gov/about-cancer/treatment/drugs/isatuximab-irfc', 'https://www.cancer.gov/about-cancer/treatment/drugs/daratumumabandhyaluronidase-fihj', '/about-cancer/treatment/drugs/belantamabmafodotin-blmf', '/about-cancer/treatment/drugs/melphalanflufenamidehydrochloride', '/about-cancer/treatment/drugs/idecabtagenevicleucel', '/about-cancer/treatment/drugs/imatinibmesylate', '/about-cancer/treatment/drugs/ruxolitinibphosphate', 'https://www.cancer.gov/about-cancer/treatment/drugs/fedratinibhydrochloride', '/about-cancer/treatment/drugs/dinutuximab', '/about-cancer/treatment/drugs/naxitamab-gqgk', '/about-cancer/treatment/drugs/bevacizumab', '/about-cancer/treatment/drugs/olaparib', '/about-cancer/treatment/drugs/rucaparibcamsylate', '/about-cancer/treatment/drugs/niraparibtosylatemonohydrate', '/about-cancer/treatment/drugs/erlotinibhydrochloride', '/about-cancer/treatment/drugs/everolimus', '/about-cancer/treatment/drugs/sunitinibmalate', '/about-cancer/treatment/drugs/olaparib', 'https://www.cancer.gov/about-cancer/treatment/drugs/selumetinibsulfate', '/about-cancer/treatment/drugs/cabazitaxel', '/about-cancer/treatment/drugs/enzalutamide', '/about-cancer/treatment/drugs/abirateroneacetate', '/about-cancer/treatment/drugs/radium-223-dichloride', '/about-cancer/treatment/drugs/apalutamide', '/about-cancer/treatment/drugs/darolutamide', '/about-cancer/treatment/drugs/rucaparibcamsylate', '/about-cancer/treatment/drugs/rucaparibcamsylate', '/about-cancer/treatment/drugs/olaparib', '/about-cancer/treatment/drugs/vismodegib', '/about-cancer/treatment/drugs/sonidegib', '/about-cancer/treatment/drugs/ipilimumab', '/about-cancer/treatment/drugs/vemurafenib', '/about-cancer/treatment/drugs/trametinib', '/about-cancer/treatment/drugs/dabrafenib', '/about-cancer/treatment/drugs/pembrolizumab', '/about-cancer/treatment/drugs/nivolumab', '/about-cancer/treatment/drugs/cobimetinib', '/publications/dictionaries/cancer-drug/def/alitretinoin', '/about-cancer/treatment/drugs/avelumab', '/about-cancer/treatment/drugs/encorafenib', '/about-cancer/treatment/drugs/binimetinib', '/about-cancer/treatment/drugs/cemiplimab-rwlc', '/about-cancer/treatment/drugs/atezolizumab', '/about-cancer/treatment/drugs/pazopanibhydrochloride', '/publications/dictionaries/cancer-drug/def/alitretinoin', 'https://www.cancer.gov/about-cancer/treatment/drugs/tazemetostathydrobromide', '/about-cancer/treatment/drugs/pembrolizumab', 'https://www.cancer.gov/about-cancer/treatment/drugs/larotrectinibsulfate', 'https://www.cancer.gov/about-cancer/treatment/drugs/entrectinib', '/about-cancer/treatment/drugs/pembrolizumab', '/about-cancer/treatment/drugs/trastuzumab', '/about-cancer/treatment/drugs/ramucirumab', '/about-cancer/treatment/drugs/famtrastuzumabderuxtecan-nxki', '/about-cancer/treatment/drugs/nivolumab', '/about-cancer/treatment/drugs/imatinibmesylate', '/about-cancer/treatment/drugs/midostaurin', '/about-cancer/treatment/drugs/cabozantinib-s-malate', '/about-cancer/treatment/drugs/vandetanib', '/about-cancer/treatment/drugs/sorafenibtosylate', '/about-cancer/treatment/drugs/lenvatinibmesylate', '/about-cancer/treatment/drugs/trametinib', 'Dabrafenib Mesylate', '/about-cancer/treatment/drugs/selpercatinib', '/about-cancer/treatment/drugs/pralsetinib']

  """
  
  rp = requests.get(url)
  page = lxml.html.fromstring(rp.text)

  # get the links of FDA-approved targeted therapies
  therapy_links = page.xpath("//section[h2[@id = 'what-targeted-therapies-have-been-approved-for-specific-types-of-cancer']]//p//a/@href")

  return therapy_links


def targeted_therapy_name(url):
  """Extract targeted therapy's name on its NCI page.

  Use the lxml library to parse the URL link and xpath to find the therapy's name from the parsed tree structure.

  Parameters
  ----------
  url : str
      An URL link to a targeted therapy's NCI page.

  Returns
  -------
  list
      Return the name of the targeted therapy appearing on its NCI page in a list.

  Examples
  --------
  Import the module

  >>> from biomarker_nlp import biomarker_extraction
  
  Example
  
  >>> url = "https://www.cancer.gov/about-cancer/treatment/drugs/atezolizumab"
  >>> biomarker_extraction.targeted_therapy_name(url = url)
  ['Atezolizumab']
  """


  # get the targeted therapy URL and parse it
  therRp = requests.get(url)
  therPage = lxml.html.fromstring(therRp.text)

  # extract the therapy's name
  therapy_name = therPage.xpath("//article/div/h1/text()")

  return therapy_name


def therapy_disease(url):
  """Extract the associated diseases (in bold text) on the therapy's NCI page.

  Extract the associated diseases in bold text on the therapy's NCI page through parsing the URL link. Remove punctuations around the text if there are any.

  Parameters
  ----------
  url : str
      An URL link to a targeted therapy's NCI page.

  Returns
  -------
  list
      Return a list of disease's name. 

  Examples
  --------
  Import the module

  >>> from biomarker_nlp import biomarker_extraction
  
  Example
  
  >>> url = "https://www.cancer.gov/about-cancer/treatment/drugs/atezolizumab"
  >>> biomarker_extraction.therapy_disease(url = url)
  ['Breast cancer', 'Urothelial carcinoma', 'Non-small cell lung cancer', 'Hepatocellular carcinoma', 'Melanoma', 'Small cell lung cancer']
  """
  
  # get the targeted therapy URL and parse it
  therRp = requests.get(url)
  therPage = lxml.html.fromstring(therRp.text)

  # extract the corresponding diseases (only for bold text, note that there are a few non-bold diseases left)
  diseases = therPage.xpath("//article//div[h2[contains(text(),'Use in Cancer')]]/ul/li/strong")

  # clear (remove punctuations)
  punc = '''!()-[]{};:'"\, <>./?@#$%^&*_~'''
  diseaseList = []

  for disease in diseases:
      
    # get the disease in string
    # remove punctuation at the end of the disease
    dis = str(disease.text_content())
    if dis[-1] in punc:
      dis = dis.replace(dis[-1], "")  
      
    # add the diseases to the list
    diseaseList.append(dis)
          
  # remove duplicates
  diseaseList = list(set(diseaseList))

  return diseaseList

def drug_search_url(url):
  """Extract the URL link about the search outcome of drug label information. DailyMed URL link (drug information vs multiple research results).

  Extract the URL link of "FDA label information for this drug is available at DailyMed." on the therapy's NCI page. The URL link could be either a DailyMed link to drug label information or a DailyMed link showing multiple search results of the drug. 

  Parameters
  ----------
  url : str
      An URL link to a targeted therapy's NCI page.

  Returns
  -------
  list
      Return a DailyMed URL link in a list.

  Examples
  --------
  Import the module

  >>> from biomarker_nlp import biomarker_extraction
  
  Example
  
  >>> url = "https://www.cancer.gov/about-cancer/treatment/drugs/atezolizumab"
  >>> biomarker_extraction.drug_search_url(url = url)
  ['https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=6fa682c9-a312-4932-9831-f286908660ee&audience=consumer']
  >>> url = "https://www.cancer.gov/about-cancer/treatment/drugs/bevacizumab"
  >>> biomarker_extraction.drug_search_url(url = url)
  ['https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query=BEVACIZUMAB&pagesize=20&page=1']
  """

  # get the targeted therapy URL and parse it
  therRp = requests.get(url)
  therPage = lxml.html.fromstring(therRp.text)

  # obtain DailyMed link
  dailyMed = therPage.xpath("//article//div/p/a[text() = 'FDA label information for this drug is available at DailyMed.']/@href")

  return dailyMed