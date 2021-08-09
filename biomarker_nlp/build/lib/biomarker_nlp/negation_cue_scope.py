#!/usr/bin/env python
# -*- coding: utf-8 -*-

from biomarker_nlp.negation_negbert import *

def negation_detect(text, modelCue):
  """Dectect if a sentence contains any negation cues.

  This function predicts if a sentence contains any negation words by using a pre-trianed negation dectection model that was pre-trained through Aditya and Suraj's (2020) NegBERT transfer learning program. 
  Please see the reference link: https://github.com/adityak6798/Transformers-For-Negation-and-Speculation. The model was trained using 'bioscope_abstracts' and 'bioscope_full_papers' corpora. 
  It was upload to a cloud repository and was freely-available. 

  Parameters
  ----------
  text : str
      a single sentence. 

  modelCue : torch model
      pre-trained negation cue detection model

  Returns
  -------
  bool
      True if any negation cues are detected. 
      False if no negation cues are detected.
  
  See Also
  --------
  negation_scope

  Notes
  -----
  NVIDIA GPU will be required. Make sure your machine brings NVIDIA GPU or set GPU as Hardware accelerator if using Colab notebook.
  
  Examples
  --------
  Install the necessary packages, and make sure turn GPU Hardware accelerator on. 
  
  >>> If using Colab Notebook, add ! before pip.
  $ pip install biomarker_nlp
  $ pip install transformers
  $ pip install knockknock==0.1.7
  $ pip install sentencepiece
  
  Load the necessary packages and pre-trained model

  >>> from biomarker_nlp import negation_cue_scope
  >>> from biomarker_nlp.negation_negbert import * # This code MUST be run before loading the pre-trained negation models
  >>> modelCue = torch.load('/path/to/negation/cue/detection/model') # path to the location where the model file is placed
 
  
  Examples (predict negation)
  
  >>> txt = "TECENTRIQ is not indicated for use in combination with paclitaxel for the treatment of adult patients with unresectable locally advanced or metastatic TNBC."
  >>> negation_cue_scope.negation_detect(text = txt, modelCue = modelCue)
  True
  >>> txt = "KEYTRUDA is not recommended for treatment of patients with PMBCL who require urgent cytoreductive therapy."
  >>> negation_cue_scope.negation_detect(text = txt, modelCue = modelCue)
  True
  >>> txt = "KEYTRUDA is indicated for the treatment of adult patients with relapsed or refractory classical Hodgkin lymphoma (cHL)."
  >>> negation_cue_scope.negation_detect(text = txt, modelCue = modelCue)
  False

  """

  # perform negation cue detection
  mydata = CustomData([text])
  dl = mydata.get_cue_dataloader()
  cueIndex = modelCue.predict(dl)

  # check if negation is detected.
  if 1 in cueIndex[0][0]:
    return True
  else: return False


def negation_scope(text, modelCue, modelScope):
  """Extract the scope of negation in a sentence.

  This function predicts the negation' cues and their scope in a sentence by using two pre-trianed negation models that were pre-trained through Aditya and Suraj's (2020) NegBERT transfer learning program. 
  Please see the reference link: https://github.com/adityak6798/Transformers-For-Negation-and-Speculation. The models were trained using 'bioscope_abstracts' and 'bioscope_full_papers' corpora.
  One of them is used to performed negation cue detection and negation scope resolution. Another one is used to performed negation scope resolution. They were upload to a cloud repository and was freely-available. 
  This function predicts negation cues first through the negation cue detection model. If any negation cues were predected, it predectes the scope of each negation cue, if there are more than one, through the negation scope resolution model.

  Parameters
  ----------
  text : str
      a single sentence.

  modelCue : torch model
      pre-trained negation cue prediction model

  modelScopre : torch model
      pre-trianed negation scope prediction model

  Returns
  -------
  list
      a list of negated clauses. Some sentences would contain more than one negation cues, in this case, all of their negated clauses will be extracted. If no negation is found, return an empty list.
  
  See Also
  --------
  negation_detect
  
  Notes
  -----
  The negation cue will not be extracted.
  NVIDIA GPU will be required. Make sure your machine brings NVIDIA GPU or set GPU as Hardware accelerator if using Colab notebook.
  
  Examples
  --------
  Install the necessary packages, and make sure turn GPU Hardware accelerator on. 
  
  >>> If using Colab Notebook, add ! before pip.
  $ pip install biomarker_nlp
  $ pip install transformers
  $ pip install knockknock==0.1.7
  $ pip install sentencepiece
  
  Load the necessary packages and pre-trained model

  >>> from biomarker_nlp import negation_cue_scope
  >>> from biomarker_nlp.negation_negbert import * # This code MUST be run before loading the pre-trained negation models
  >>> modelCue = torch.load('/path/to/negation/cue/detection/model') # path to the location where the model file is placed
  >>> modelScope = torch.load('/path/to/negation/scope/detection/model') # path to the location where the model file is placed
  
  Examples (predict negation scope)
  
  >>> txt = "TECENTRIQ is not indicated for use in combination with paclitaxel for the treatment of adult patients with unresectable locally advanced or metastatic TNBC."
  >>> negation_cue_scope.negation_scope(text = txt, modelCue = modelCue, modelScope = modelScope)
  ['TECENTRIQ is', 'indicated for use in combination with paclitaxel for']
  >>> txt = "KEYTRUDA is not recommended for treatment of patients with PMBCL who require urgent cytoreductive therapy."
  >>> negation_cue_scope.negation_scope(text = txt, modelCue = modelCue, modelScope = modelScope)
  ['KEYTRUDA is', 'recommended for treatment of patients with PMBCL who']

  """

  # perform negation cue detection
  mydata = CustomData([text])
  dl = mydata.get_cue_dataloader()
  cueIndex = modelCue.predict(dl)

  # string of the scope
  negationScope = []

  # check if negation is detected.
  if 1 in cueIndex[0][0]:
    
    # perform negation scope resolution
    mydata = CustomData([text], cues = cueIndex[0])
    dl = mydata.get_scope_dataloader()
    scopeIndex = modelScope.predict(dl)

    # extract the negated string of the scope
    if len(scopeIndex[0][0]) == len(text.split()):
      scopeSubstr = ''
      for i in range(len(text.split())):
        if scopeIndex[0][0][i] == 1 and i != len(text.split())-1:
          scopeSubstr += " " + text.split()[i]
        elif i == len(text.split())-1 and scopeIndex[0][0][i] == 1:
          scopeSubstr += " " + text.split()[i]
          negationScope.append(scopeSubstr.lstrip())
        else: 
          if len(scopeSubstr) > 0:
            negationScope.append(scopeSubstr.lstrip())
            scopeSubstr = ''
  
  return negationScope
