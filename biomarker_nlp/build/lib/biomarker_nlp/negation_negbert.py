"""
This is part of Aditya Khandelwal & Suraj Sawant's (2020) NegBERT program, it is necessary to run the negation cue detection (modelCue) and negation scope resolution (modelScope) models.
For more information about NegBERT program, please see: https://github.com/adityak6798/Transformers-For-Negation-and-Speculation. 
"""
import os, re, torch, html, tempfile, copy, json, math, shutil, tarfile, tempfile, sys, random, pickle
from torch import nn
from torch.nn import functional as F
from torch.nn import CrossEntropyLoss, ReLU
from torch.optim import Adam
from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
from keras.preprocessing.sequence import pad_sequences
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, classification_report
from transformers import RobertaTokenizer, BertForTokenClassification, BertTokenizer, BertConfig, BertModel, WordpieceTokenizer, XLNetTokenizer
from transformers.file_utils import cached_path
import numpy as np
import pandas as pd
from tqdm import tqdm
import matplotlib.pyplot as plt
from scipy import stats
from knockknock import email_sender, telegram_sender

MAX_LEN = 128
bs = 8
EPOCHS = 60
PATIENCE = 6
INITIAL_LEARNING_RATE = 3e-5
NUM_RUNS = 1 #Number of times to run the training and evaluation code

CUE_MODEL = 'bert-base-uncased'
SCOPE_MODEL = 'xlnet-base-cased'
SCOPE_METHOD = 'augment' # Options: augment, replace
F1_METHOD = 'average' # Options: average, first_token
TASK = 'negation' # Options: negation, speculation
SUBTASK = 'scope_resolution' # Options: cue_detection, scope_resolution
TRAIN_DATASETS = ['bioscope_abstracts','bioscope_full_papers']
TEST_DATASETS = ['bioscope_full_papers','bioscope_abstracts']


BERT_PRETRAINED_CONFIG_ARCHIVE_MAP = {
    'bert-base-uncased': "https://s3.amazonaws.com/models.huggingface.co/bert/bert-base-uncased-config.json"
}

BERT_PRETRAINED_MODEL_ARCHIVE_MAP = {
    'bert-base-uncased': "https://s3.amazonaws.com/models.huggingface.co/bert/bert-base-uncased-pytorch_model.bin"
}

ROBERTA_PRETRAINED_MODEL_ARCHIVE_MAP = {
    'roberta-base': "https://s3.amazonaws.com/models.huggingface.co/bert/roberta-base-pytorch_model.bin"
}

ROBERTA_PRETRAINED_CONFIG_ARCHIVE_MAP = {
    'roberta-base': "https://s3.amazonaws.com/models.huggingface.co/bert/roberta-base-config.json"
}

XLNET_PRETRAINED_CONFIG_ARCHIVE_MAP = {
    'xlnet-base-cased': "https://s3.amazonaws.com/models.huggingface.co/bert/xlnet-base-cased-config.json"
}

XLNET_PRETRAINED_MODEL_ARCHIVE_MAP = {
    'xlnet-base-cased': "https://s3.amazonaws.com/models.huggingface.co/bert/xlnet-base-cased-pytorch_model.bin"
}

TF_WEIGHTS_NAME = 'model.ckpt'
CONFIG_NAME = "config.json"
WEIGHTS_NAME = "pytorch_model.bin"

device = torch.device("cuda")
n_gpu = torch.cuda.device_count()

class Data:
    def __init__(self, file, dataset_name = 'sfu', frac_no_cue_sents = 1.0):
        '''
        file: The path of the data file.
        dataset_name: The name of the dataset to be preprocessed. Values supported: sfu, bioscope, starsem.
        frac_no_cue_sents: The fraction of sentences to be included in the data object which have no negation/speculation cues.
        '''
        def starsem(f_path, cue_sents_only=False, frac_no_cue_sents = 1.0):
            raw_data = open(f_path)
            sentence = []
            labels = []
            label = []
            scope_sents = []
            data_scope = []
            scope = []
            scope_cues = []
            data = []
            cue_only_data = []
            
            for line in raw_data:
                label = []
                sentence = []
                tokens = line.strip().split()
                if len(tokens)==8: #This line has no cues
                        sentence.append(tokens[3])
                        label.append(3) #Not a cue
                        for line in raw_data:
                            tokens = line.strip().split()
                            if len(tokens)==0:
                                break
                            else:
                                sentence.append(tokens[3])
                                label.append(3)
                        cue_only_data.append([sentence, label])
                        
                    
                else: #The line has 1 or more cues
                    num_cues = (len(tokens)-7)//3
                    #cue_count+=num_cues
                    scope = [[] for i in range(num_cues)]
                    label = [[],[]] #First list is the real labels, second list is to modify if it is a multi-word cue.
                    label[0].append(3) #Generally not a cue, if it is will be set ahead.
                    label[1].append(-1) #Since not a cue, for now.
                    for i in range(num_cues):
                        if tokens[7+3*i] != '_': #Cue field is active
                            if tokens[8+3*i] != '_': #Check for affix
                                label[0][-1] = 0 #Affix
                                affix_list.append(tokens[7+3*i])
                                label[1][-1] = i #Cue number
                                #sentence.append(tokens[7+3*i])
                                #new_word = '##'+tokens[8+3*i]
                            else:
                                label[0][-1] = 1 #Maybe a normal or multiword cue. The next few words will determine which.
                                label[1][-1] = i #Which cue field, for multiword cue altering.
                                
                        if tokens[8+3*i] != '_':
                            scope[i].append(1)
                        else:
                            scope[i].append(0)
                    sentence.append(tokens[3])
                    for line in raw_data:
                        tokens = line.strip().split()
                        if len(tokens)==0:
                            break
                        else:
                            sentence.append(tokens[3])
                            label[0].append(3) #Generally not a cue, if it is will be set ahead.
                            label[1].append(-1) #Since not a cue, for now.   
                            for i in range(num_cues):
                                if tokens[7+3*i] != '_': #Cue field is active
                                    if tokens[8+3*i] != '_': #Check for affix
                                        label[0][-1] = 0 #Affix
                                        label[1][-1] = i #Cue number
                                    else:
                                        label[0][-1] = 1 #Maybe a normal or multiword cue. The next few words will determine which.
                                        label[1][-1] = i #Which cue field, for multiword cue altering.
                                if tokens[8+3*i] != '_':
                                    scope[i].append(1)
                                else:
                                    scope[i].append(0)
                    for i in range(num_cues):
                        indices = [index for index,j in enumerate(label[1]) if i==j]
                        count = len(indices)
                        if count>1:
                            for j in indices:
                                label[0][j] = 2
                    for i in range(num_cues):
                        sc = []
                        for a,b in zip(label[0],label[1]):
                            if i==b:
                                sc.append(a)
                            else:
                                sc.append(3)
                        scope_cues.append(sc)
                        scope_sents.append(sentence)
                        data_scope.append(scope[i])
                    labels.append(label[0])
                    data.append(sentence)
            cue_only_samples = random.sample(cue_only_data, k=int(frac_no_cue_sents*len(cue_only_data)))
            cue_only_sents = [i[0] for i in cue_only_samples]
            cue_only_cues = [i[1] for i in cue_only_samples]
            starsem_cues = (data+cue_only_sents,labels+cue_only_cues)
            starsem_scopes = (scope_sents, scope_cues, data_scope)
            return [starsem_cues, starsem_scopes]
            
        def bioscope(f_path, cue_sents_only=False, frac_no_cue_sents = 1.0):
            file = open(f_path, encoding = 'utf-8')
            sentences = []
            for s in file:
                sentences+=re.split("(<.*?>)", html.unescape(s))
            cue_sentence = []
            cue_cues = []
            cue_only_data = []
            scope_cues = []
            scope_scopes = []
            scope_sentence = []
            sentence = []
            cue = {}
            scope = {}
            in_scope = []
            in_cue = []
            word_num = 0
            c_idx = []
            s_idx = []
            in_sentence = 0
            for token in sentences:
                if token == '':
                    continue
                elif '<sentence' in token:
                    in_sentence = 1
                elif '<cue' in token:
                    if TASK in token:
                        in_cue.append(str(re.split('(ref=".*?")',token)[1][4:]))
                        c_idx.append(str(re.split('(ref=".*?")',token)[1][4:]))
                        if c_idx[-1] not in cue.keys():
                            cue[c_idx[-1]] = []
                elif '</cue' in token:
                    in_cue = in_cue[:-1]
                elif '<xcope' in token:
                    #print(re.split('(id=".*?")',token)[1][3:])
                    in_scope.append(str(re.split('(id=".*?")',token)[1][3:]))
                    s_idx.append(str(re.split('(id=".*?")',token)[1][3:]))
                    scope[s_idx[-1]] = []
                elif '</xcope' in token:
                    in_scope = in_scope[:-1]
                elif '</sentence' in token:
                    #print(cue, scope)
                    if len(cue.keys())==0:
                        cue_only_data.append([sentence, [3]*len(sentence)])
                    else:
                        cue_sentence.append(sentence)
                        cue_cues.append([3]*len(sentence))
                        for i in cue.keys():
                            scope_sentence.append(sentence)
                            scope_cues.append([3]*len(sentence))
                            if len(cue[i])==1:
                                cue_cues[-1][cue[i][0]] = 1
                                scope_cues[-1][cue[i][0]] = 1
                            else:
                                for c in cue[i]:
                                    cue_cues[-1][c] = 2
                                    scope_cues[-1][c] = 2
                            scope_scopes.append([0]*len(sentence))

                            if i in scope.keys():
                                for s in scope[i]:
                                    scope_scopes[-1][s] = 1

                    sentence = []
                    cue = {}
                    scope = {}
                    in_scope = []
                    in_cue = []
                    word_num = 0
                    in_sentence = 0
                    c_idx = []
                    s_idx = []
                elif '<' not in token:
                    if in_sentence==1:
                        words = token.split()
                        sentence+=words
                        if len(in_cue)!=0:
                            for i in in_cue:
                                cue[i]+=[word_num+i for i in range(len(words))]
                        elif len(in_scope)!=0:
                            for i in in_scope:
                                scope[i]+=[word_num+i for i in range(len(words))]
                        word_num+=len(words)
            cue_only_samples = random.sample(cue_only_data, k=int(frac_no_cue_sents*len(cue_only_data)))
            cue_only_sents = [i[0] for i in cue_only_samples]
            cue_only_cues = [i[1] for i in cue_only_samples]
            return [(cue_sentence+cue_only_sents, cue_cues+cue_only_cues),(scope_sentence, scope_cues, scope_scopes)]
        
        def sfu_review(f_path, cue_sents_only=False, frac_no_cue_sents = 1.0):
            file = open(f_path, encoding = 'utf-8')
            sentences = []
            for s in file:
                sentences+=re.split("(<.*?>)", html.unescape(s))
            cue_sentence = []
            cue_cues = []
            scope_cues = []
            scope_scopes = []
            scope_sentence = []
            sentence = []
            cue = {}
            scope = {}
            in_scope = []
            in_cue = []
            word_num = 0
            c_idx = []
            cue_only_data = []
            s_idx = []
            in_word = 0
            for token in sentences:
                if token == '':
                    continue
                elif token == '<W>':
                    in_word = 1
                elif token == '</W>':
                    in_word = 0
                    word_num += 1
                elif '<cue' in token:
                    if TASK in token:
                        in_cue.append(int(re.split('(ID=".*?")',token)[1][4:-1]))
                        c_idx.append(int(re.split('(ID=".*?")',token)[1][4:-1]))
                        if c_idx[-1] not in cue.keys():
                            cue[c_idx[-1]] = []
                elif '</cue' in token:
                    in_cue = in_cue[:-1]
                elif '<xcope' in token:
                    continue
                elif '</xcope' in token:
                    in_scope = in_scope[:-1]
                elif '<ref' in token:
                    in_scope.append([int(i) for i in re.split('(SRC=".*?")',token)[1][5:-1].split(' ')])
                    s_idx.append([int(i) for i in re.split('(SRC=".*?")',token)[1][5:-1].split(' ')])
                    for i in s_idx[-1]:
                        scope[i] = []
                elif '</SENTENCE' in token:
                    if len(cue.keys())==0:
                        cue_only_data.append([sentence, [3]*len(sentence)])
                    else:
                        cue_sentence.append(sentence)
                        cue_cues.append([3]*len(sentence))
                        for i in cue.keys():
                            scope_sentence.append(sentence)
                            scope_cues.append([3]*len(sentence))
                            if len(cue[i])==1:
                                cue_cues[-1][cue[i][0]] = 1
                                scope_cues[-1][cue[i][0]] = 1
                            else:
                                for c in cue[i]:
                                    cue_cues[-1][c] = 2
                                    scope_cues[-1][c] = 2
                            scope_scopes.append([0]*len(sentence))
                            if i in scope.keys():
                                for s in scope[i]:
                                    scope_scopes[-1][s] = 1
                    sentence = []
                    cue = {}
                    scope = {}
                    in_scope = []
                    in_cue = []
                    word_num = 0
                    in_word = 0
                    c_idx = []
                    s_idx = []
                elif '<' not in token:
                    if in_word == 1:
                        if len(in_cue)!=0:
                            for i in in_cue:
                                cue[i].append(word_num)
                        if len(in_scope)!=0:
                            for i in in_scope:
                                for j in i:
                                    scope[j].append(word_num)
                        sentence.append(token)
            cue_only_samples = random.sample(cue_only_data, k=int(frac_no_cue_sents*len(cue_only_data)))
            cue_only_sents = [i[0] for i in cue_only_samples]
            cue_only_cues = [i[1] for i in cue_only_samples]
            return [(cue_sentence+cue_only_sents, cue_cues+cue_only_cues),(scope_sentence, scope_cues, scope_scopes)]
        
        
        if dataset_name == 'bioscope':
            ret_val = bioscope(file, frac_no_cue_sents=frac_no_cue_sents)
            self.cue_data = Cues(ret_val[0])
            self.scope_data = Scopes(ret_val[1])
        elif dataset_name == 'sfu':
            sfu_cues = [[], []]
            sfu_scopes = [[], [], []]
            for dir_name in os.listdir(file):
                if '.' not in dir_name:
                    for f_name in os.listdir(file+"//"+dir_name):
                        r_val = sfu_review(file+"//"+dir_name+'//'+f_name, frac_no_cue_sents=frac_no_cue_sents)
                        sfu_cues = [a+b for a,b in zip(sfu_cues, r_val[0])]
                        sfu_scopes = [a+b for a,b in zip(sfu_scopes, r_val[1])]
            self.cue_data = Cues(sfu_cues)
            self.scope_data = Scopes(sfu_scopes)
        elif dataset_name == 'starsem':
            if TASK == 'negation':
                ret_val = starsem(file, frac_no_cue_sents=frac_no_cue_sents)
                self.cue_data = Cues(ret_val[0])
                self.scope_data = Scopes(ret_val[1])
            else:
                raise ValueError("Starsem 2012 dataset only supports negation annotations")
        else:
            raise ValueError("Supported Dataset types are:\n\tbioscope\n\tsfu\n\tconll_cue")
    
    def get_cue_dataloader(self, val_size = 0.15, test_size = 0.15, other_datasets = []):
        '''
        This function returns the dataloader for the cue detection.
        val_size: The size of the validation dataset (Fraction between 0 to 1)
        test_size: The size of the test dataset (Fraction between 0 to 1)
        other_datasets: Other datasets to use to get one combined train dataloader
        Returns: train_dataloader, list of validation dataloaders, list of test dataloaders
        '''
        do_lower_case = True
        if 'uncased' not in CUE_MODEL:
            do_lower_case = False
        if 'xlnet' in CUE_MODEL:
            tokenizer = XLNetTokenizer.from_pretrained(CUE_MODEL, do_lower_case=do_lower_case, cache_dir='xlnet_tokenizer')
        elif 'roberta' in CUE_MODEL:
            tokenizer = RobertaTokenizer.from_pretrained(CUE_MODEL, do_lower_case=do_lower_case, cache_dir='roberta_tokenizer')
        elif 'bert' in CUE_MODEL:
            tokenizer = BertTokenizer.from_pretrained(CUE_MODEL, do_lower_case=do_lower_case, cache_dir='bert_tokenizer')
        def preprocess_data(obj, tokenizer):
            dl_sents = obj.cue_data.sentences
            dl_cues = obj.cue_data.cues
                
            sentences = [" ".join(sent) for sent in dl_sents]

            mytexts = []
            mylabels = []
            mymasks = []
            if do_lower_case == True:
                sentences_clean = [sent.lower() for sent in sentences]
            else:
                sentences_clean = sentences
            for sent, tags in zip(sentences_clean,dl_cues):
                new_tags = []
                new_text = []
                new_masks = []
                for word, tag in zip(sent.split(),tags):
                    sub_words = tokenizer._tokenize(word)
                    for count, sub_word in enumerate(sub_words):
                        if type(tag)!=int:
                            raise ValueError(tag)
                        mask = 1
                        if count > 0:
                            mask = 0
                        new_masks.append(mask)
                        new_tags.append(tag)
                        new_text.append(sub_word)
                mymasks.append(new_masks)
                mytexts.append(new_text)
                mylabels.append(new_tags)

            
            input_ids = pad_sequences([[tokenizer._convert_token_to_id(word) for word in txt] for txt in mytexts],
                                      maxlen=MAX_LEN, dtype="long", truncating="post", padding="post").tolist()

            tags = pad_sequences(mylabels,
                                maxlen=MAX_LEN, value=4, padding="post",
                                dtype="long", truncating="post").tolist()
            
            mymasks = pad_sequences(mymasks, maxlen=MAX_LEN, value=0, padding='post', dtype='long', truncating='post').tolist()
            
            attention_masks = [[float(i>0) for i in ii] for ii in input_ids]
            
            random_state = np.random.randint(1,2019)

            tra_inputs, test_inputs, tra_tags, test_tags = train_test_split(input_ids, tags, test_size=test_size, random_state = random_state)
            tra_masks, test_masks, _, _ = train_test_split(attention_masks, input_ids, test_size=test_size, random_state = random_state)
            tra_mymasks, test_mymasks, _, _ = train_test_split(mymasks, input_ids, test_size=test_size, random_state = random_state)
            
            random_state_2 = np.random.randint(1,2019)

            tr_inputs, val_inputs, tr_tags, val_tags = train_test_split(tra_inputs, tra_tags, test_size=(val_size/(1-test_size)), random_state = random_state_2)
            tr_masks, val_masks, _, _ = train_test_split(tra_masks, tra_inputs, test_size=(val_size/(1-test_size)), random_state = random_state_2)
            tr_mymasks, val_mymasks, _, _ = train_test_split(tra_mymasks, tra_inputs, test_size=(val_size/(1-test_size)), random_state = random_state_2)
            return [tr_inputs, tr_tags, tr_masks, tr_mymasks], [val_inputs, val_tags, val_masks, val_mymasks], [test_inputs, test_tags, test_masks, test_mymasks]

        tr_inputs = []
        tr_tags = []
        tr_masks = []
        tr_mymasks = []
        val_inputs = [[] for i in range(len(other_datasets)+1)]
        test_inputs = [[] for i in range(len(other_datasets)+1)]

        train_ret_val, val_ret_val, test_ret_val = preprocess_data(self, tokenizer)
        tr_inputs+=train_ret_val[0]
        tr_tags+=train_ret_val[1]
        tr_masks+=train_ret_val[2]
        tr_mymasks+=train_ret_val[3]
        val_inputs[0].append(val_ret_val[0])
        val_inputs[0].append(val_ret_val[1])
        val_inputs[0].append(val_ret_val[2])
        val_inputs[0].append(val_ret_val[3])
        test_inputs[0].append(test_ret_val[0])
        test_inputs[0].append(test_ret_val[1])
        test_inputs[0].append(test_ret_val[2])
        test_inputs[0].append(test_ret_val[3])
        
        for idx, arg in enumerate(other_datasets, 1):
            train_ret_val, val_ret_val, test_ret_val = preprocess_data(arg, tokenizer)
            tr_inputs+=train_ret_val[0]
            tr_tags+=train_ret_val[1]
            tr_masks+=train_ret_val[2]
            tr_mymasks+=train_ret_val[3]
            val_inputs[idx].append(val_ret_val[0])
            val_inputs[idx].append(val_ret_val[1])
            val_inputs[idx].append(val_ret_val[2])
            val_inputs[idx].append(val_ret_val[3])
            test_inputs[idx].append(test_ret_val[0])
            test_inputs[idx].append(test_ret_val[1])
            test_inputs[idx].append(test_ret_val[2])
            test_inputs[idx].append(test_ret_val[3])
        
        tr_inputs = torch.LongTensor(tr_inputs)
        tr_tags = torch.LongTensor(tr_tags)
        tr_masks = torch.LongTensor(tr_masks)
        tr_mymasks = torch.LongTensor(tr_mymasks)
        val_inputs = [[torch.LongTensor(i) for i in j] for j in val_inputs]
        test_inputs = [[torch.LongTensor(i) for i in j] for j in test_inputs]

        train_data = TensorDataset(tr_inputs, tr_masks, tr_tags, tr_mymasks)
        train_sampler = RandomSampler(train_data)
        train_dataloader = DataLoader(train_data, sampler=train_sampler, batch_size=bs)

        val_dataloaders = []
        for i,j,k,l in val_inputs:
            val_data = TensorDataset(i, k, j, l)
            val_sampler = RandomSampler(val_data)
            val_dataloaders.append(DataLoader(val_data, sampler=val_sampler, batch_size=bs))

        test_dataloaders = []
        for i,j,k,l in test_inputs:
            test_data = TensorDataset(i, k, j, l)
            test_sampler = RandomSampler(test_data)
            test_dataloaders.append(DataLoader(test_data, sampler=test_sampler, batch_size=bs))

        return train_dataloader, val_dataloaders, test_dataloaders

    def get_scope_dataloader(self, val_size = 0.15, test_size=0.15, other_datasets = []):
        '''
        This function returns the dataloader for the cue detection.
        val_size: The size of the validation dataset (Fraction between 0 to 1)
        test_size: The size of the test dataset (Fraction between 0 to 1)
        other_datasets: Other datasets to use to get one combined train dataloader
        Returns: train_dataloader, list of validation dataloaders, list of test dataloaders
        '''
        method = SCOPE_METHOD
        do_lower_case = True
        if 'uncased' not in SCOPE_MODEL:
            do_lower_case = False
        if 'xlnet' in SCOPE_MODEL:
            tokenizer = XLNetTokenizer.from_pretrained(SCOPE_MODEL, do_lower_case=do_lower_case, cache_dir='xlnet_tokenizer')
        elif 'roberta' in SCOPE_MODEL:
            tokenizer = RobertaTokenizer.from_pretrained(SCOPE_MODEL, do_lower_case=do_lower_case, cache_dir='roberta_tokenizer')
        elif 'bert' in SCOPE_MODEL:
            tokenizer = BertTokenizer.from_pretrained(SCOPE_MODEL, do_lower_case=do_lower_case, cache_dir='bert_tokenizer')
        def preprocess_data(obj, tokenizer_obj):
            dl_sents = obj.scope_data.sentences
            dl_cues = obj.scope_data.cues
            dl_scopes = obj.scope_data.scopes
            
            sentences = [" ".join([s for s in sent]) for sent in dl_sents]
            mytexts = []
            mylabels = []
            mycues = []
            mymasks = []
            if do_lower_case == True:
                sentences_clean = [sent.lower() for sent in sentences]
            else:
                sentences_clean = sentences
            
            for sent, tags, cues in zip(sentences_clean,dl_scopes, dl_cues):
                new_tags = []
                new_text = []
                new_cues = []
                new_masks = []
                for word, tag, cue in zip(sent.split(),tags,cues):
                    sub_words = tokenizer_obj._tokenize(word)
                    for count, sub_word in enumerate(sub_words):
                        mask = 1
                        if count > 0:
                            mask = 0
                        new_masks.append(mask)
                        new_tags.append(tag)
                        new_cues.append(cue)
                        new_text.append(sub_word)
                mymasks.append(new_masks)
                mytexts.append(new_text)
                mylabels.append(new_tags)
                mycues.append(new_cues)
            final_sentences = []
            final_labels = []
            final_masks = []
            if method == 'replace':
                for sent,cues in zip(mytexts, mycues):
                    temp_sent = []
                    for token,cue in zip(sent,cues):
                        if cue==3:
                            temp_sent.append(token)
                        else:
                            temp_sent.append(f'[unused{cue+1}]')
                    final_sentences.append(temp_sent)
                final_labels = mylabels
                final_masks = mymasks
            elif method == 'augment':
                for sent,cues,labels,masks in zip(mytexts, mycues, mylabels, mymasks):
                    temp_sent = []
                    temp_label = []
                    temp_masks = []
                    first_part = 0
                    for token,cue,label,mask in zip(sent,cues,labels,masks):
                        if cue!=3:
                            if first_part == 0:
                                first_part = 1
                                temp_sent.append(f'[unused{cue+1}]')
                                temp_masks.append(1)
                                temp_label.append(label)
                                temp_sent.append(token)
                                temp_masks.append(0)
                                temp_label.append(label)
                                continue
                            temp_sent.append(f'[unused{cue+1}]')
                            temp_masks.append(0)
                            temp_label.append(label)
                        else:
                            first_part = 0
                        temp_masks.append(mask)
                        temp_sent.append(token)
                        temp_label.append(label)
                    final_sentences.append(temp_sent)
                    final_labels.append(temp_label)
                    final_masks.append(temp_masks)
            else:
                raise ValueError("Supported methods for scope detection are:\nreplace\naugment")
            input_ids = pad_sequences([[tokenizer_obj._convert_token_to_id(word) for word in txt] for txt in final_sentences],
                                      maxlen=MAX_LEN, dtype="long", truncating="post", padding="post").tolist()

            tags = pad_sequences(final_labels,
                                maxlen=MAX_LEN, value=0, padding="post",
                                dtype="long", truncating="post").tolist()
            
            final_masks = pad_sequences(final_masks,
                                maxlen=MAX_LEN, value=0, padding="post",
                                dtype="long", truncating="post").tolist()

            attention_masks = [[float(i>0) for i in ii] for ii in input_ids]
            
            random_state = np.random.randint(1,2019)

            tra_inputs, test_inputs, tra_tags, test_tags = train_test_split(input_ids, tags, test_size=test_size, random_state = random_state)
            tra_masks, test_masks, _, _ = train_test_split(attention_masks, input_ids, test_size=test_size, random_state = random_state)
            tra_mymasks, test_mymasks, _, _ = train_test_split(final_masks, input_ids, test_size=test_size, random_state = random_state)
            
            random_state_2 = np.random.randint(1,2019)

            tr_inputs, val_inputs, tr_tags, val_tags = train_test_split(tra_inputs, tra_tags, test_size=(val_size/(1-test_size)), random_state = random_state_2)
            tr_masks, val_masks, _, _ = train_test_split(tra_masks, tra_inputs, test_size=(val_size/(1-test_size)), random_state = random_state_2)
            tr_mymasks, val_mymasks, _, _ = train_test_split(tra_mymasks, tra_inputs, test_size=(val_size/(1-test_size)), random_state = random_state_2)

            return [tr_inputs, tr_tags, tr_masks, tr_mymasks], [val_inputs, val_tags, val_masks, val_mymasks], [test_inputs, test_tags, test_masks, test_mymasks]

        tr_inputs = []
        tr_tags = []
        tr_masks = []
        tr_mymasks = []
        val_inputs = [[] for i in range(len(other_datasets)+1)]
        test_inputs = [[] for i in range(len(other_datasets)+1)]

        train_ret_val, val_ret_val, test_ret_val = preprocess_data(self, tokenizer)
        tr_inputs+=train_ret_val[0]
        tr_tags+=train_ret_val[1]
        tr_masks+=train_ret_val[2]
        tr_mymasks+=train_ret_val[3]
        val_inputs[0].append(val_ret_val[0])
        val_inputs[0].append(val_ret_val[1])
        val_inputs[0].append(val_ret_val[2])
        val_inputs[0].append(val_ret_val[3])
        test_inputs[0].append(test_ret_val[0])
        test_inputs[0].append(test_ret_val[1])
        test_inputs[0].append(test_ret_val[2])
        test_inputs[0].append(test_ret_val[3])
        
        for idx, arg in enumerate(other_datasets, 1):
            train_ret_val, val_ret_val, test_ret_val = preprocess_data(arg, tokenizer)
            tr_inputs+=train_ret_val[0]
            tr_tags+=train_ret_val[1]
            tr_masks+=train_ret_val[2]
            tr_mymasks+=train_ret_val[3]
            val_inputs[idx].append(val_ret_val[0])
            val_inputs[idx].append(val_ret_val[1])
            val_inputs[idx].append(val_ret_val[2])
            val_inputs[idx].append(val_ret_val[3])
            test_inputs[idx].append(test_ret_val[0])
            test_inputs[idx].append(test_ret_val[1])
            test_inputs[idx].append(test_ret_val[2])
            test_inputs[idx].append(test_ret_val[3])

        tr_inputs = torch.LongTensor(tr_inputs)
        tr_tags = torch.LongTensor(tr_tags)
        tr_masks = torch.LongTensor(tr_masks)
        tr_mymasks = torch.LongTensor(tr_mymasks)
        val_inputs = [[torch.LongTensor(i) for i in j] for j in val_inputs]
        test_inputs = [[torch.LongTensor(i) for i in j] for j in test_inputs]

        train_data = TensorDataset(tr_inputs, tr_masks, tr_tags, tr_mymasks)
        train_sampler = RandomSampler(train_data)
        train_dataloader = DataLoader(train_data, sampler=train_sampler, batch_size=bs)

        val_dataloaders = []
        for i,j,k,l in val_inputs:
            val_data = TensorDataset(i, k, j, l)
            val_sampler = RandomSampler(val_data)
            val_dataloaders.append(DataLoader(val_data, sampler=val_sampler, batch_size=bs))

        test_dataloaders = []
        for i,j,k,l in test_inputs:
            test_data = TensorDataset(i, k, j, l)
            test_sampler = RandomSampler(test_data)
            test_dataloaders.append(DataLoader(test_data, sampler=test_sampler, batch_size=bs))

        return train_dataloader, val_dataloaders, test_dataloaders

class CustomData:
    def __init__(self, sentences, cues = None):
        self.sentences = sentences
        self.cues = cues
    def get_cue_dataloader(self):
        do_lower_case = True
        if 'uncased' not in CUE_MODEL:
            do_lower_case = False
        if 'xlnet' in CUE_MODEL:
            tokenizer = XLNetTokenizer.from_pretrained(CUE_MODEL, do_lower_case=do_lower_case, cache_dir='xlnet_tokenizer')
        elif 'roberta' in CUE_MODEL:
            tokenizer = RobertaTokenizer.from_pretrained(CUE_MODEL, do_lower_case=do_lower_case, cache_dir='roberta_tokenizer')
        elif 'bert' in CUE_MODEL:
            tokenizer = BertTokenizer.from_pretrained(CUE_MODEL, do_lower_case=do_lower_case, cache_dir='bert_tokenizer')
        
        dl_sents = self.sentences    
        sentences = dl_sents # sentences = [" ".join(sent) for sent in dl_sents]

        mytexts = []
        mylabels = []
        mymasks = []
        if do_lower_case == True:
            sentences_clean = [sent.lower() for sent in sentences]
        else:
            sentences_clean = sentences
        for sent in sentences_clean:
            new_text = []
            new_masks = []
            for word in sent.split():
                sub_words = tokenizer._tokenize(word)
                for count, sub_word in enumerate(sub_words):
                    mask = 1
                    if count > 0:
                        mask = 0
                    new_masks.append(mask)
                    new_text.append(sub_word)
            mymasks.append(new_masks)
            mytexts.append(new_text)
            
        input_ids = pad_sequences([tokenizer.convert_tokens_to_ids(txt) for txt in mytexts],
                                  maxlen=MAX_LEN, dtype="long", truncating="post", padding="post")

        mymasks = pad_sequences(mymasks, maxlen=MAX_LEN, value=0, padding='post', dtype='long', truncating='post').tolist()

        attention_masks = [[float(i>0) for i in ii] for ii in input_ids]

        inputs = torch.LongTensor(input_ids)
        masks = torch.LongTensor(attention_masks)
        mymasks = torch.LongTensor(mymasks)

        data = TensorDataset(inputs, masks, mymasks)
        dataloader = DataLoader(data, batch_size=bs)

        return dataloader
    
    def get_scope_dataloader(self, cues = None):
        if cues != None:
            self.cues = cues
        if self.cues == None:
            raise ValueError("Need Cues Data to Generate the Scope Dataloader")
        method = SCOPE_METHOD
        do_lower_case = True
        if 'uncased' not in SCOPE_MODEL:
            do_lower_case = False
        if 'xlnet' in SCOPE_MODEL:
            tokenizer = XLNetTokenizer.from_pretrained(SCOPE_MODEL, do_lower_case=do_lower_case, cache_dir='xlnet_tokenizer')
        elif 'roberta' in SCOPE_MODEL:
            tokenizer = RobertaTokenizer.from_pretrained(SCOPE_MODEL, do_lower_case=do_lower_case, cache_dir='roberta_tokenizer')
        elif 'bert' in SCOPE_MODEL:
            tokenizer = BertTokenizer.from_pretrained(SCOPE_MODEL, do_lower_case=do_lower_case, cache_dir='bert_tokenizer')
        dl_sents = self.sentences
        dl_cues = self.cues
        
        sentences = dl_sents
        mytexts = []
        mycues = []
        mymasks = []
        if do_lower_case == True:
            sentences_clean = [sent.lower() for sent in sentences]
        else:
            sentences_clean = sentences
        
        for sent, cues in zip(sentences_clean, dl_cues):
            new_text = []
            new_cues = []
            new_masks = []
            for word, cue in zip(sent.split(), cues):
                sub_words = tokenizer._tokenize(word)
                for count, sub_word in enumerate(sub_words):
                    mask = 1
                    if count > 0:
                        mask = 0
                    new_masks.append(mask)
                    new_cues.append(cue)
                    new_text.append(sub_word)
            mymasks.append(new_masks)
            mytexts.append(new_text)
            mycues.append(new_cues)
        final_sentences = []
        final_masks = []
        if method == 'replace':
            for sent,cues in zip(mytexts, mycues):
                temp_sent = []
                for token,cue in zip(sent,cues):
                    if cue==3:
                        temp_sent.append(token)
                    else:
                        temp_sent.append(f'[unused{cue+1}]')
                final_sentences.append(temp_sent)
            final_masks = mymasks
        elif method == 'augment':
            for sent,cues,masks in zip(mytexts, mycues, mymasks):
                temp_sent = []
                temp_masks = []
                first_part = 0
                for token,cue,mask in zip(sent,cues,masks):
                    if cue!=3:
                        if first_part == 0:
                            first_part = 1
                            temp_sent.append(f'[unused{cue+1}]')
                            temp_masks.append(1)
                            #temp_label.append(label)
                            temp_sent.append(token)
                            temp_masks.append(0)
                            #temp_label.append(label)
                            continue
                        temp_sent.append(f'[unused{cue+1}]')
                        temp_masks.append(0)
                        #temp_label.append(label)
                    else:
                        first_part = 0
                    temp_masks.append(mask)
                    temp_sent.append(token)
                final_sentences.append(temp_sent)
                final_masks.append(temp_masks)
        else:
            raise ValueError("Supported methods for scope detection are:\nreplace\naugment")
    
        input_ids = pad_sequences([tokenizer.convert_tokens_to_ids(txt) for txt in final_sentences],
                                  maxlen=MAX_LEN, dtype="long", truncating="post", padding="post")
        
        final_masks = pad_sequences(final_masks,
                                maxlen=MAX_LEN, value=0, padding="post",
                                dtype="long", truncating="post").tolist()

        attention_masks = [[float(i>0) for i in ii] for ii in input_ids]

        inputs = torch.LongTensor(input_ids)
        masks = torch.LongTensor(attention_masks)
        final_masks = torch.LongTensor(final_masks)

        data = TensorDataset(inputs, masks, final_masks)
        dataloader = DataLoader(data, batch_size=bs)
        #print(final_sentences, mycues)

        return dataloader

def load_tf_weights_in_bert(model, config, tf_checkpoint_path):
    """ Load tf checkpoints in a pytorch model.
    """
    import re
    import tensorflow as tf
    tf_path = os.path.abspath(tf_checkpoint_path)
    # Load weights from TF model
    init_vars = tf.train.list_variables(tf_path)
    names = []
    arrays = []
    for name, shape in init_vars:
        array = tf.train.load_variable(tf_path, name)
        names.append(name)
        arrays.append(array)

    for name, array in zip(names, arrays):
        name = name.split('/')
        # adam_v and adam_m are variables used in AdamWeightDecayOptimizer to calculated m and v
        # which are not required for using pretrained model
        if any(n in ["adam_v", "adam_m", "global_step"] for n in name):
            continue
        pointer = model
        for m_name in name:
            if re.fullmatch(r'[A-Za-z]+_\d+', m_name):
                l = re.split(r'_(\d+)', m_name)
            else:
                l = [m_name]
            if l[0] == 'kernel' or l[0] == 'gamma':
                pointer = getattr(pointer, 'weight')
            elif l[0] == 'output_bias' or l[0] == 'beta':
                pointer = getattr(pointer, 'bias')
            elif l[0] == 'output_weights':
                pointer = getattr(pointer, 'weight')
            elif l[0] == 'squad':
                pointer = getattr(pointer, 'classifier')
            else:
                try:
                    pointer = getattr(pointer, l[0])
                except AttributeError:
                    continue
            if len(l) >= 2:
                num = int(l[1])
                pointer = pointer[num]
        if m_name[-11:] == '_embeddings':
            pointer = getattr(pointer, 'weight')
        elif m_name == 'kernel':
            array = np.transpose(array)
        try:
            assert pointer.shape == array.shape
        except AssertionError as e:
            e.args += (pointer.shape, array.shape)
            raise
        pointer.data = torch.from_numpy(array)
    return model

def load_tf_weights_in_xlnet(model, config, tf_path):
    """ Load tf checkpoints in a pytorch model
    """
    import numpy as np
    import tensorflow as tf
    # Load weights from TF model
    init_vars = tf.train.list_variables(tf_path)
    tf_weights = {}
    for name, shape in init_vars:
        array = tf.train.load_variable(tf_path, name)
        tf_weights[name] = array

    # Build TF to PyTorch weights loading map
    tf_to_pt_map = build_tf_xlnet_to_pytorch_map(model, config, tf_weights)

    for name, pointer in tf_to_pt_map.items():
        if name not in tf_weights:
            continue
        array = tf_weights[name]
        # adam_v and adam_m are variables used in AdamWeightDecayOptimizer to calculated m and v
        # which are not required for using pretrained model
        if 'kernel' in name and ('ff' in name or 'summary' in name or 'logit' in name):
            array = np.transpose(array)
        if isinstance(pointer, list):
            # Here we will split the TF weigths
            assert len(pointer) == array.shape[0]
            for i, p_i in enumerate(pointer):
                arr_i = array[i, ...]
                try:
                    assert p_i.shape == arr_i.shape
                except AssertionError as e:
                    e.args += (p_i.shape, arr_i.shape)
                    raise
                p_i.data = torch.from_numpy(arr_i)
        else:
            try:
                assert pointer.shape == array.shape
            except AssertionError as e:
                e.args += (pointer.shape, array.shape)
                raise
            pointer.data = torch.from_numpy(array)
        tf_weights.pop(name, None)
        tf_weights.pop(name + '/Adam', None)
        tf_weights.pop(name + '/Adam_1', None)

    return model

def gelu(x):
    """ Original Implementation of the gelu activation function in Google Bert repo when initially created.
        For information: OpenAI GPT's gelu is slightly different (and gives slightly different results):
        0.5 * x * (1 + torch.tanh(math.sqrt(2 / math.pi) * (x + 0.044715 * torch.pow(x, 3))))
        Also see https://arxiv.org/abs/1606.08415
    """
    return x * 0.5 * (1.0 + torch.erf(x / math.sqrt(2.0)))

def gelu_new(x):
    """ Implementation of the gelu activation function currently in Google Bert repo (identical to OpenAI GPT).
        Also see https://arxiv.org/abs/1606.08415
    """
    return 0.5 * x * (1 + torch.tanh(math.sqrt(2 / math.pi) * (x + 0.044715 * torch.pow(x, 3))))

def swish(x):
    return x * torch.sigmoid(x)

ACT2FN = {"gelu": gelu, "relu": torch.nn.functional.relu, "swish": swish, "gelu_new": gelu_new}

class PretrainedConfig(object):
    r""" Base class for all configuration classes.
        Handles a few parameters common to all models' configurations as well as methods for loading/downloading/saving configurations.
        Note:
            A configuration file can be loaded and saved to disk. Loading the configuration file and using this file to initialize a model does **not** load the model weights.
            It only affects the model's configuration.
        Class attributes (overridden by derived classes):
            - ``pretrained_config_archive_map``: a python ``dict`` of with `short-cut-names` (string) as keys and `url` (string) of associated pretrained model configurations as values.
        Parameters:
            ``finetuning_task``: string, default `None`. Name of the task used to fine-tune the model. This can be used when converting from an original (TensorFlow or PyTorch) checkpoint.
            ``num_labels``: integer, default `2`. Number of classes to use when the model is a classification model (sequences/tokens)
            ``output_attentions``: boolean, default `False`. Should the model returns attentions weights.
            ``output_hidden_states``: string, default `False`. Should the model returns all hidden-states.
            ``torchscript``: string, default `False`. Is the model used with Torchscript.
    """
    pretrained_config_archive_map = {}

    def __init__(self, **kwargs):
        self.finetuning_task = kwargs.pop('finetuning_task', None)
        self.num_labels = kwargs.pop('num_labels', 2)
        self.output_attentions = kwargs.pop('output_attentions', False)
        self.output_hidden_states = kwargs.pop('output_hidden_states', False)
        self.output_past = kwargs.pop('output_past', True)  # Not used by all models
        self.torchscript = kwargs.pop('torchscript', False)  # Only used by PyTorch models
        self.use_bfloat16 = kwargs.pop('use_bfloat16', False)
        self.pruned_heads = kwargs.pop('pruned_heads', {})

    def save_pretrained(self, save_directory):
        """ Save a configuration object to the directory `save_directory`, so that it
            can be re-loaded using the :func:`~transformers.PretrainedConfig.from_pretrained` class method.
        """
        assert os.path.isdir(save_directory), "Saving path should be a directory where the model and configuration can be saved"

        # If we save using the predefined names, we can load using `from_pretrained`
        output_config_file = os.path.join(save_directory, CONFIG_NAME)

        self.to_json_file(output_config_file)
        
    @classmethod
    def from_pretrained(cls, pretrained_model_name_or_path, **kwargs):
        r""" Instantiate a :class:`~transformers.PretrainedConfig` (or a derived class) from a pre-trained model configuration.
        Parameters:
            pretrained_model_name_or_path: either:
                - a string with the `shortcut name` of a pre-trained model configuration to load from cache or download, e.g.: ``bert-base-uncased``.
                - a path to a `directory` containing a configuration file saved using the :func:`~transformers.PretrainedConfig.save_pretrained` method, e.g.: ``./my_model_directory/``.
                - a path or url to a saved configuration JSON `file`, e.g.: ``./my_model_directory/configuration.json``.
            cache_dir: (`optional`) string:
                Path to a directory in which a downloaded pre-trained model
                configuration should be cached if the standard cache should not be used.
            kwargs: (`optional`) dict: key/value pairs with which to update the configuration object after loading.
                - The values in kwargs of any keys which are configuration attributes will be used to override the loaded values.
                - Behavior concerning key/value pairs whose keys are *not* configuration attributes is controlled by the `return_unused_kwargs` keyword parameter.
            force_download: (`optional`) boolean, default False:
                Force to (re-)download the model weights and configuration files and override the cached versions if they exists.
            proxies: (`optional`) dict, default None:
                A dictionary of proxy servers to use by protocol or endpoint, e.g.: {'http': 'foo.bar:3128', 'http://hostname': 'foo.bar:4012'}.
                The proxies are used on each request.
            return_unused_kwargs: (`optional`) bool:
                - If False, then this function returns just the final configuration object.
                - If True, then this functions returns a tuple `(config, unused_kwargs)` where `unused_kwargs` is a dictionary consisting of the key/value pairs whose keys are not configuration attributes: ie the part of kwargs which has not been used to update `config` and is otherwise ignored.
        Examples::
            # We can't instantiate directly the base class `PretrainedConfig` so let's show the examples on a
            # derived class: BertConfig
            config = BertConfig.from_pretrained('bert-base-uncased')    # Download configuration from S3 and cache.
            config = BertConfig.from_pretrained('./test/saved_model/')  # E.g. config (or model) was saved using `save_pretrained('./test/saved_model/')`
            config = BertConfig.from_pretrained('./test/saved_model/my_configuration.json')
            config = BertConfig.from_pretrained('bert-base-uncased', output_attention=True, foo=False)
            assert config.output_attention == True
            config, unused_kwargs = BertConfig.from_pretrained('bert-base-uncased', output_attention=True,
                                                               foo=False, return_unused_kwargs=True)
            assert config.output_attention == True
            assert unused_kwargs == {'foo': False}
        """
        cache_dir = kwargs.pop('cache_dir', None)
        force_download = kwargs.pop('force_download', False)
        proxies = kwargs.pop('proxies', None)
        return_unused_kwargs = kwargs.pop('return_unused_kwargs', False)

        if pretrained_model_name_or_path in cls.pretrained_config_archive_map:
            config_file = cls.pretrained_config_archive_map[pretrained_model_name_or_path]
        elif os.path.isdir(pretrained_model_name_or_path):
            config_file = os.path.join(pretrained_model_name_or_path, CONFIG_NAME)
        else:
            config_file = pretrained_model_name_or_path
        # redirect to the cache, if necessary
        try:
            resolved_config_file = cached_path(config_file, cache_dir=cache_dir, force_download=force_download, proxies=proxies)
        except EnvironmentError:
            if pretrained_model_name_or_path in cls.pretrained_config_archive_map:
                msg = "Couldn't reach server at '{}' to download pretrained model configuration file.".format(
                        config_file)
            else:
                msg = "Model name '{}' was not found in model name list ({}). " \
                      "We assumed '{}' was a path or url to a configuration file named {} or " \
                      "a directory containing such a file but couldn't find any such file at this path or url.".format(
                        pretrained_model_name_or_path,
                        ', '.join(cls.pretrained_config_archive_map.keys()),
                        config_file, CONFIG_NAME)
            raise EnvironmentError(msg)

        
        # Load config
        config = cls.from_json_file(resolved_config_file)

        if hasattr(config, 'pruned_heads'):
            config.pruned_heads = dict((int(key), value) for key, value in config.pruned_heads.items())

        # Update config with kwargs if needed
        to_remove = []
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
                to_remove.append(key)
        for key in to_remove:
            kwargs.pop(key, None)

        if return_unused_kwargs:
            return config, kwargs
        else:
            return config

    @classmethod
    def from_dict(cls, json_object):
        """Constructs a `Config` from a Python dictionary of parameters."""
        config = cls(vocab_size_or_config_json_file=-1)
        for key, value in json_object.items():
            setattr(config, key, value)
        return config

    @classmethod
    def from_json_file(cls, json_file):
        """Constructs a `BertConfig` from a json file of parameters."""
        with open(json_file, "r", encoding='utf-8') as reader:
            text = reader.read()
        return cls.from_dict(json.loads(text))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return str(self.to_json_string())

    def to_dict(self):
        """Serializes this instance to a Python dictionary."""
        output = copy.deepcopy(self.__dict__)
        return output

    def to_json_string(self):
        """Serializes this instance to a JSON string."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"

    def to_json_file(self, json_file_path):
        """ Save this instance to a json file."""
        with open(json_file_path, "w", encoding='utf-8') as writer:
            writer.write(self.to_json_string())

class BertConfig(PretrainedConfig):
    r"""
        :class:`~transformers.BertConfig` is the configuration class to store the configuration of a
        `BertModel`.
        Arguments:
            vocab_size_or_config_json_file: Vocabulary size of `inputs_ids` in `BertModel`.
            hidden_size: Size of the encoder layers and the pooler layer.
            num_hidden_layers: Number of hidden layers in the Transformer encoder.
            num_attention_heads: Number of attention heads for each attention layer in
                the Transformer encoder.
            intermediate_size: The size of the "intermediate" (i.e., feed-forward)
                layer in the Transformer encoder.
            hidden_act: The non-linear activation function (function or string) in the
                encoder and pooler. If string, "gelu", "relu", "swish" and "gelu_new" are supported.
            hidden_dropout_prob: The dropout probabilitiy for all fully connected
                layers in the embeddings, encoder, and pooler.
            attention_probs_dropout_prob: The dropout ratio for the attention
                probabilities.
            max_position_embeddings: The maximum sequence length that this model might
                ever be used with. Typically set this to something large just in case
                (e.g., 512 or 1024 or 2048).
            type_vocab_size: The vocabulary size of the `token_type_ids` passed into
                `BertModel`.
            initializer_range: The sttdev of the truncated_normal_initializer for
                initializing all weight matrices.
            layer_norm_eps: The epsilon used by LayerNorm.
    """
    pretrained_config_archive_map = BERT_PRETRAINED_CONFIG_ARCHIVE_MAP

    def __init__(self,
                 vocab_size_or_config_json_file=30522,
                 hidden_size=768,
                 num_hidden_layers=12,
                 num_attention_heads=12,
                 intermediate_size=3072,
                 hidden_act="gelu",
                 hidden_dropout_prob=0.1,
                 attention_probs_dropout_prob=0.1,
                 max_position_embeddings=512,
                 type_vocab_size=2,
                 initializer_range=0.02,
                 layer_norm_eps=1e-12,
                 **kwargs):
        super(BertConfig, self).__init__(**kwargs)
        if isinstance(vocab_size_or_config_json_file, str) or (sys.version_info[0] == 2
                        and isinstance(vocab_size_or_config_json_file, unicode)):
            with open(vocab_size_or_config_json_file, "r", encoding='utf-8') as reader:
                json_config = json.loads(reader.read())
            for key, value in json_config.items():
                self.__dict__[key] = value
        elif isinstance(vocab_size_or_config_json_file, int):
            self.vocab_size = vocab_size_or_config_json_file
            self.hidden_size = hidden_size
            self.num_hidden_layers = num_hidden_layers
            self.num_attention_heads = num_attention_heads
            self.hidden_act = hidden_act
            self.intermediate_size = intermediate_size
            self.hidden_dropout_prob = hidden_dropout_prob
            self.attention_probs_dropout_prob = attention_probs_dropout_prob
            self.max_position_embeddings = max_position_embeddings
            self.type_vocab_size = type_vocab_size
            self.initializer_range = initializer_range
            self.layer_norm_eps = layer_norm_eps
        else:
            raise ValueError("First argument must be either a vocabulary size (int)"
                             " or the path to a pretrained model config file (str)")

class RobertaConfig(BertConfig):
    pretrained_config_archive_map = ROBERTA_PRETRAINED_CONFIG_ARCHIVE_MAP

class XLNetConfig(PretrainedConfig):
    """Configuration class to store the configuration of a ``XLNetModel``.
    Args:
        vocab_size_or_config_json_file: Vocabulary size of ``inputs_ids`` in ``XLNetModel``.
        d_model: Size of the encoder layers and the pooler layer.
        n_layer: Number of hidden layers in the Transformer encoder.
        n_head: Number of attention heads for each attention layer in
            the Transformer encoder.
        d_inner: The size of the "intermediate" (i.e., feed-forward)
            layer in the Transformer encoder.
        ff_activation: The non-linear activation function (function or string) in the
            encoder and pooler. If string, "gelu", "relu" and "swish" are supported.
        untie_r: untie relative position biases
        attn_type: 'bi' for XLNet, 'uni' for Transformer-XL
        dropout: The dropout probabilitiy for all fully connected
            layers in the embeddings, encoder, and pooler.
        initializer_range: The sttdev of the truncated_normal_initializer for
            initializing all weight matrices.
        layer_norm_eps: The epsilon used by LayerNorm.
        dropout: float, dropout rate.
        init: str, the initialization scheme, either "normal" or "uniform".
        init_range: float, initialize the parameters with a uniform distribution
            in [-init_range, init_range]. Only effective when init="uniform".
        init_std: float, initialize the parameters with a normal distribution
            with mean 0 and stddev init_std. Only effective when init="normal".
        mem_len: int, the number of tokens to cache.
        reuse_len: int, the number of tokens in the currect batch to be cached
            and reused in the future.
        bi_data: bool, whether to use bidirectional input pipeline.
            Usually set to True during pretraining and False during finetuning.
        clamp_len: int, clamp all relative distances larger than clamp_len.
            -1 means no clamping.
        same_length: bool, whether to use the same attention length for each token.
        finetuning_task: name of the glue task on which the model was fine-tuned if any
    """
    pretrained_config_archive_map = XLNET_PRETRAINED_CONFIG_ARCHIVE_MAP

    def __init__(self,
                 vocab_size_or_config_json_file=32000,
                 d_model=1024,
                 n_layer=24,
                 n_head=16,
                 d_inner=4096,
                 max_position_embeddings=512,
                 ff_activation="gelu",
                 untie_r=True,
                 attn_type="bi",

                 initializer_range=0.02,
                 layer_norm_eps=1e-12,

                 dropout=0.1,
                 mem_len=None,
                 reuse_len=None,
                 bi_data=False,
                 clamp_len=-1,
                 same_length=False,

                 finetuning_task=None,
                 num_labels=2,
                 summary_type='last',
                 summary_use_proj=True,
                 summary_activation='tanh',
                 summary_last_dropout=0.1,
                 start_n_top=5,
                 end_n_top=5,
                 **kwargs):
        """Constructs XLNetConfig.
        """
        super(XLNetConfig, self).__init__(**kwargs)

        if isinstance(vocab_size_or_config_json_file, str) or (sys.version_info[0] == 2
                        and isinstance(vocab_size_or_config_json_file, unicode)):
            with open(vocab_size_or_config_json_file, "r", encoding='utf-8') as reader:
                json_config = json.loads(reader.read())
            for key, value in json_config.items():
                setattr(config, key, value)
        elif isinstance(vocab_size_or_config_json_file, int):
            self.n_token = vocab_size_or_config_json_file
            self.d_model = d_model
            self.n_layer = n_layer
            self.n_head = n_head
            assert d_model % n_head == 0
            self.d_head = d_model // n_head
            self.ff_activation = ff_activation
            self.d_inner = d_inner
            self.untie_r = untie_r
            self.attn_type = attn_type

            self.initializer_range = initializer_range
            self.layer_norm_eps = layer_norm_eps

            self.dropout = dropout
            self.mem_len = mem_len
            self.reuse_len = reuse_len
            self.bi_data = bi_data
            self.clamp_len = clamp_len
            self.same_length = same_length

            self.finetuning_task = finetuning_task
            self.num_labels = num_labels
            self.summary_type = summary_type
            self.summary_use_proj = summary_use_proj
            self.summary_activation = summary_activation
            self.summary_last_dropout = summary_last_dropout
            self.start_n_top = start_n_top
            self.end_n_top = end_n_top
        else:
            raise ValueError("First argument must be either a vocabulary size (int)"
                             " or the path to a pretrained model config file (str)")

    @property
    def max_position_embeddings(self):
        return -1

    @property
    def vocab_size(self):
        return self.n_token

    @vocab_size.setter
    def vocab_size(self, value):
        self.n_token = value

    @property
    def hidden_size(self):
        return self.d_model

    @property
    def num_attention_heads(self):
        return self.n_head

    @property
    def num_hidden_layers(self):
        return self.n_layer

class PreTrainedModel(nn.Module):
    r""" Base class for all models.
        :class:`~transformers.PreTrainedModel` takes care of storing the configuration of the models and handles methods for loading/downloading/saving models
        as well as a few methods commons to all models to (i) resize the input embeddings and (ii) prune heads in the self-attention heads.
        Class attributes (overridden by derived classes):
            - ``config_class``: a class derived from :class:`~transformers.PretrainedConfig` to use as configuration class for this model architecture.
            - ``pretrained_model_archive_map``: a python ``dict`` of with `short-cut-names` (string) as keys and `url` (string) of associated pretrained weights as values.
            - ``load_tf_weights``: a python ``method`` for loading a TensorFlow checkpoint in a PyTorch model, taking as arguments:
                - ``model``: an instance of the relevant subclass of :class:`~transformers.PreTrainedModel`,
                - ``config``: an instance of the relevant subclass of :class:`~transformers.PretrainedConfig`,
                - ``path``: a path (string) to the TensorFlow checkpoint.
            - ``base_model_prefix``: a string indicating the attribute associated to the base model in derived classes of the same architecture adding modules on top of the base model.
    """
    config_class = None
    pretrained_model_archive_map = {}
    load_tf_weights = lambda model, config, path: None
    base_model_prefix = ""

    def __init__(self, config, *inputs, **kwargs):
        super(PreTrainedModel, self).__init__()
        if not isinstance(config, PretrainedConfig):
            raise ValueError(
                "Parameter config in `{}(config)` should be an instance of class `PretrainedConfig`. "
                "To create a model from a pretrained model use "
                "`model = {}.from_pretrained(PRETRAINED_MODEL_NAME)`".format(
                    self.__class__.__name__, self.__class__.__name__
                ))
        # Save config in model
        self.config = config

    def _get_resized_embeddings(self, old_embeddings, new_num_tokens=None):
        """ Build a resized Embedding Module from a provided token Embedding Module.
            Increasing the size will add newly initialized vectors at the end
            Reducing the size will remove vectors from the end
        Args:
            new_num_tokens: (`optional`) int
                New number of tokens in the embedding matrix.
                Increasing the size will add newly initialized vectors at the end
                Reducing the size will remove vectors from the end
                If not provided or None: return the provided token Embedding Module.
        Return: ``torch.nn.Embeddings``
            Pointer to the resized Embedding Module or the old Embedding Module if new_num_tokens is None
        """
        if new_num_tokens is None:
            return old_embeddings

        old_num_tokens, old_embedding_dim = old_embeddings.weight.size()
        if old_num_tokens == new_num_tokens:
            return old_embeddings

        # Build new embeddings
        new_embeddings = nn.Embedding(new_num_tokens, old_embedding_dim)
        new_embeddings.to(old_embeddings.weight.device)

        # initialize all new embeddings (in particular added tokens)
        self._init_weights(new_embeddings)

        # Copy word embeddings from the previous weights
        num_tokens_to_copy = min(old_num_tokens, new_num_tokens)
        new_embeddings.weight.data[:num_tokens_to_copy, :] = old_embeddings.weight.data[:num_tokens_to_copy, :]

        return new_embeddings

    def _tie_or_clone_weights(self, first_module, second_module):
        """ Tie or clone module weights depending of weither we are using TorchScript or not
        """
        if self.config.torchscript:
            first_module.weight = nn.Parameter(second_module.weight.clone())
        else:
            first_module.weight = second_module.weight

        if hasattr(first_module, 'bias') and first_module.bias is not None:
            first_module.bias.data = torch.nn.functional.pad(
                first_module.bias.data,
                (0, first_module.weight.shape[0] - first_module.bias.shape[0]),
                'constant',
                0
            )

    def resize_token_embeddings(self, new_num_tokens=None):
        """ Resize input token embeddings matrix of the model if new_num_tokens != config.vocab_size.
        Take care of tying weights embeddings afterwards if the model class has a `tie_weights()` method.
        Arguments:
            new_num_tokens: (`optional`) int:
                New number of tokens in the embedding matrix. Increasing the size will add newly initialized vectors at the end. Reducing the size will remove vectors from the end.
                If not provided or None: does nothing and just returns a pointer to the input tokens ``torch.nn.Embeddings`` Module of the model.
        Return: ``torch.nn.Embeddings``
            Pointer to the input tokens Embeddings Module of the model
        """
        base_model = getattr(self, self.base_model_prefix, self)  # get the base model if needed
        model_embeds = base_model._resize_token_embeddings(new_num_tokens)
        if new_num_tokens is None:
            return model_embeds

        # Update base model and current model config
        self.config.vocab_size = new_num_tokens
        base_model.vocab_size = new_num_tokens

        # Tie weights again if needed
        if hasattr(self, 'tie_weights'):
            self.tie_weights()

        return model_embeds

    def init_weights(self):
        """ Initialize and prunes weights if needed. """
        # Initialize weights
        self.apply(self._init_weights)

        # Prune heads if needed
        if self.config.pruned_heads:
            self.prune_heads(self.config.pruned_heads)

    def prune_heads(self, heads_to_prune):
        """ Prunes heads of the base model.
            Arguments:
                heads_to_prune: dict with keys being selected layer indices (`int`) and associated values being the list of heads to prune in said layer (list of `int`).
                E.g. {1: [0, 2], 2: [2, 3]} will prune heads 0 and 2 on layer 1 and heads 2 and 3 on layer 2.
        """
        base_model = getattr(self, self.base_model_prefix, self)  # get the base model if needed

        # save new sets of pruned heads as union of previously stored pruned heads and newly pruned heads
        for layer, heads in heads_to_prune.items():
            union_heads = set(self.config.pruned_heads.get(layer, [])) | set(heads)
            self.config.pruned_heads[layer] = list(union_heads)  # Unfortunately we have to store it as list for JSON

        base_model._prune_heads(heads_to_prune)

    def save_pretrained(self, save_directory):
        """ Save a model and its configuration file to a directory, so that it
            can be re-loaded using the `:func:`~transformers.PreTrainedModel.from_pretrained`` class method.
        """
        assert os.path.isdir(save_directory), "Saving path should be a directory where the model and configuration can be saved"

        # Only save the model it-self if we are using distributed training
        model_to_save = self.module if hasattr(self, 'module') else self

        # Save configuration file
        model_to_save.config.save_pretrained(save_directory)

        # If we save using the predefined names, we can load using `from_pretrained`
        output_model_file = os.path.join(save_directory, WEIGHTS_NAME)
        torch.save(model_to_save.state_dict(), output_model_file)
        
    @classmethod
    def from_pretrained(cls, pretrained_model_name_or_path, *model_args, **kwargs):
        r"""Instantiate a pretrained pytorch model from a pre-trained model configuration.
        The model is set in evaluation mode by default using ``model.eval()`` (Dropout modules are deactivated)
        To train the model, you should first set it back in training mode with ``model.train()``
        The warning ``Weights from XXX not initialized from pretrained model`` means that the weights of XXX do not come pre-trained with the rest of the model.
        It is up to you to train those weights with a downstream fine-tuning task.
        The warning ``Weights from XXX not used in YYY`` means that the layer XXX is not used by YYY, therefore those weights are discarded.
        Parameters:
            pretrained_model_name_or_path: either:
                - a string with the `shortcut name` of a pre-trained model to load from cache or download, e.g.: ``bert-base-uncased``.
                - a path to a `directory` containing model weights saved using :func:`~transformers.PreTrainedModel.save_pretrained`, e.g.: ``./my_model_directory/``.
                - a path or url to a `tensorflow index checkpoint file` (e.g. `./tf_model/model.ckpt.index`). In this case, ``from_tf`` should be set to True and a configuration object should be provided as ``config`` argument. This loading path is slower than converting the TensorFlow checkpoint in a PyTorch model using the provided conversion scripts and loading the PyTorch model afterwards.
                - None if you are both providing the configuration and state dictionary (resp. with keyword arguments ``config`` and ``state_dict``)
            model_args: (`optional`) Sequence of positional arguments:
                All remaning positional arguments will be passed to the underlying model's ``__init__`` method
            config: (`optional`) instance of a class derived from :class:`~transformers.PretrainedConfig`:
                Configuration for the model to use instead of an automatically loaded configuation. Configuration can be automatically loaded when:
                - the model is a model provided by the library (loaded with the ``shortcut-name`` string of a pretrained model), or
                - the model was saved using :func:`~transformers.PreTrainedModel.save_pretrained` and is reloaded by suppling the save directory.
                - the model is loaded by suppling a local directory as ``pretrained_model_name_or_path`` and a configuration JSON file named `config.json` is found in the directory.
            state_dict: (`optional`) dict:
                an optional state dictionnary for the model to use instead of a state dictionary loaded from saved weights file.
                This option can be used if you want to create a model from a pretrained configuration but load your own weights.
                In this case though, you should check if using :func:`~transformers.PreTrainedModel.save_pretrained` and :func:`~transformers.PreTrainedModel.from_pretrained` is not a simpler option.
            cache_dir: (`optional`) string:
                Path to a directory in which a downloaded pre-trained model
                configuration should be cached if the standard cache should not be used.
            force_download: (`optional`) boolean, default False:
                Force to (re-)download the model weights and configuration files and override the cached versions if they exists.
            proxies: (`optional`) dict, default None:
                A dictionary of proxy servers to use by protocol or endpoint, e.g.: {'http': 'foo.bar:3128', 'http://hostname': 'foo.bar:4012'}.
                The proxies are used on each request.
            output_loading_info: (`optional`) boolean:
                Set to ``True`` to also return a dictionnary containing missing keys, unexpected keys and error messages.
            kwargs: (`optional`) Remaining dictionary of keyword arguments:
                Can be used to update the configuration object (after it being loaded) and initiate the model. (e.g. ``output_attention=True``). Behave differently depending on whether a `config` is provided or automatically loaded:
                - If a configuration is provided with ``config``, ``**kwargs`` will be directly passed to the underlying model's ``__init__`` method (we assume all relevant updates to the configuration have already been done)
                - If a configuration is not provided, ``kwargs`` will be first passed to the configuration class initialization function (:func:`~transformers.PretrainedConfig.from_pretrained`). Each key of ``kwargs`` that corresponds to a configuration attribute will be used to override said attribute with the supplied ``kwargs`` value. Remaining keys that do not correspond to any configuration attribute will be passed to the underlying model's ``__init__`` function.
        Examples::
            model = BertModel.from_pretrained('bert-base-uncased')    # Download model and configuration from S3 and cache.
            model = BertModel.from_pretrained('./test/saved_model/')  # E.g. model was saved using `save_pretrained('./test/saved_model/')`
            model = BertModel.from_pretrained('bert-base-uncased', output_attention=True)  # Update configuration during loading
            assert model.config.output_attention == True
            # Loading from a TF checkpoint file instead of a PyTorch model (slower)
            config = BertConfig.from_json_file('./tf_model/my_tf_model_config.json')
            model = BertModel.from_pretrained('./tf_model/my_tf_checkpoint.ckpt.index', from_tf=True, config=config)
        """
        config = kwargs.pop('config', None)
        state_dict = kwargs.pop('state_dict', None)
        cache_dir = kwargs.pop('cache_dir', None)
        from_tf = kwargs.pop('from_tf', False)
        force_download = kwargs.pop('force_download', False)
        proxies = kwargs.pop('proxies', None)
        output_loading_info = kwargs.pop('output_loading_info', False)

        # Load config
        if config is None:
            config, model_kwargs = cls.config_class.from_pretrained(
                pretrained_model_name_or_path, *model_args,
                cache_dir=cache_dir, return_unused_kwargs=True,
                force_download=force_download,
                **kwargs
            )
        else:
            model_kwargs = kwargs

        # Load model
        if pretrained_model_name_or_path is not None:
            if pretrained_model_name_or_path in cls.pretrained_model_archive_map:
                archive_file = cls.pretrained_model_archive_map[pretrained_model_name_or_path]
            elif os.path.isdir(pretrained_model_name_or_path):
                if from_tf and os.path.isfile(os.path.join(pretrained_model_name_or_path, TF_WEIGHTS_NAME + ".index")):
                    # Load from a TF 1.0 checkpoint
                    archive_file = os.path.join(pretrained_model_name_or_path, TF_WEIGHTS_NAME + ".index")
                elif from_tf and os.path.isfile(os.path.join(pretrained_model_name_or_path, TF2_WEIGHTS_NAME)):
                    # Load from a TF 2.0 checkpoint
                    archive_file = os.path.join(pretrained_model_name_or_path, TF2_WEIGHTS_NAME)
                elif os.path.isfile(os.path.join(pretrained_model_name_or_path, WEIGHTS_NAME)):
                    # Load from a PyTorch checkpoint
                    archive_file = os.path.join(pretrained_model_name_or_path, WEIGHTS_NAME)
                else:
                    raise EnvironmentError("Error no file named {} found in directory {} or `from_tf` set to False".format(
                        [WEIGHTS_NAME, TF2_WEIGHTS_NAME, TF_WEIGHTS_NAME + ".index"],
                        pretrained_model_name_or_path))
            elif os.path.isfile(pretrained_model_name_or_path):
                archive_file = pretrained_model_name_or_path
            else:
                assert from_tf, "Error finding file {}, no file or TF 1.X checkpoint found".format(pretrained_model_name_or_path)
                archive_file = pretrained_model_name_or_path + ".index"

            # redirect to the cache, if necessary
            try:
                resolved_archive_file = cached_path(archive_file, cache_dir=cache_dir, force_download=force_download, proxies=proxies)
            except EnvironmentError:
                if pretrained_model_name_or_path in cls.pretrained_model_archive_map:
                    msg = "Couldn't reach server at '{}' to download pretrained weights.".format(
                            archive_file)
                else:
                    msg = "Model name '{}' was not found in model name list ({}). " \
                        "We assumed '{}' was a path or url to model weight files named one of {} but " \
                        "couldn't find any such file at this path or url.".format(
                            pretrained_model_name_or_path,
                            ', '.join(cls.pretrained_model_archive_map.keys()),
                            archive_file,
                            [WEIGHTS_NAME, TF2_WEIGHTS_NAME, TF_WEIGHTS_NAME])
                raise EnvironmentError(msg)

            
        else:
            resolved_archive_file = None

        # Instantiate model.
        model = cls(config, *model_args, **model_kwargs)

        if state_dict is None and not from_tf:
            state_dict = torch.load(resolved_archive_file, map_location='cpu')

        missing_keys = []
        unexpected_keys = []
        error_msgs = []

        if from_tf:
            if resolved_archive_file.endswith('.index'):
                # Load from a TensorFlow 1.X checkpoint - provided by original authors
                model = cls.load_tf_weights(model, config, resolved_archive_file[:-6])  # Remove the '.index'
            else:
                # Load from our TensorFlow 2.0 checkpoints
                try:
                    from transformers import load_tf2_checkpoint_in_pytorch_model
                    model = load_tf2_checkpoint_in_pytorch_model(model, resolved_archive_file, allow_missing_keys=True)
                except ImportError as e:
                    raise e
        else:
            # Convert old format to new format if needed from a PyTorch state_dict
            old_keys = []
            new_keys = []
            for key in state_dict.keys():
                new_key = None
                if 'gamma' in key:
                    new_key = key.replace('gamma', 'weight')
                if 'beta' in key:
                    new_key = key.replace('beta', 'bias')
                if new_key:
                    old_keys.append(key)
                    new_keys.append(new_key)
            for old_key, new_key in zip(old_keys, new_keys):
                state_dict[new_key] = state_dict.pop(old_key)

            # copy state_dict so _load_from_state_dict can modify it
            metadata = getattr(state_dict, '_metadata', None)
            state_dict = state_dict.copy()
            if metadata is not None:
                state_dict._metadata = metadata

            def load(module, prefix=''):
                local_metadata = {} if metadata is None else metadata.get(prefix[:-1], {})
                module._load_from_state_dict(
                    state_dict, prefix, local_metadata, True, missing_keys, unexpected_keys, error_msgs)
                for name, child in module._modules.items():
                    if child is not None:
                        load(child, prefix + name + '.')

            # Make sure we are able to load base models as well as derived models (with heads)
            start_prefix = ''
            model_to_load = model
            if not hasattr(model, cls.base_model_prefix) and any(s.startswith(cls.base_model_prefix) for s in state_dict.keys()):
                start_prefix = cls.base_model_prefix + '.'
            if hasattr(model, cls.base_model_prefix) and not any(s.startswith(cls.base_model_prefix) for s in state_dict.keys()):
                model_to_load = getattr(model, cls.base_model_prefix)

            load(model_to_load, prefix=start_prefix)
            if len(error_msgs) > 0:
                raise RuntimeError('Error(s) in loading state_dict for {}:\n\t{}'.format(
                                model.__class__.__name__, "\n\t".join(error_msgs)))

        if hasattr(model, 'tie_weights'):
            model.tie_weights()  # make sure word embedding weights are still tied

        # Set model in evaluation mode to desactivate DropOut modules by default
        model.eval()

        if output_loading_info:
            loading_info = {"missing_keys": missing_keys, "unexpected_keys": unexpected_keys, "error_msgs": error_msgs}
            return model, loading_info

        return model

XLNetLayerNorm = nn.LayerNorm
class XLNetRelativeAttention(nn.Module):
    def __init__(self, config):
        super(XLNetRelativeAttention, self).__init__()
        self.output_attentions = config.output_attentions

        if config.d_model % config.n_head != 0:
            raise ValueError(
                "The hidden size (%d) is not a multiple of the number of attention "
                "heads (%d)" % (config.d_model, config.n_head))

        self.n_head = config.n_head
        self.d_head = config.d_head
        self.d_model = config.d_model
        self.scale = 1 / (config.d_head ** 0.5)

        self.q = nn.Parameter(torch.FloatTensor(config.d_model, self.n_head, self.d_head))
        self.k = nn.Parameter(torch.FloatTensor(config.d_model, self.n_head, self.d_head))
        self.v = nn.Parameter(torch.FloatTensor(config.d_model, self.n_head, self.d_head))
        self.o = nn.Parameter(torch.FloatTensor(config.d_model, self.n_head, self.d_head))
        self.r = nn.Parameter(torch.FloatTensor(config.d_model, self.n_head, self.d_head))

        self.r_r_bias = nn.Parameter(torch.FloatTensor(self.n_head, self.d_head))
        self.r_s_bias = nn.Parameter(torch.FloatTensor(self.n_head, self.d_head))
        self.r_w_bias = nn.Parameter(torch.FloatTensor(self.n_head, self.d_head))
        self.seg_embed = nn.Parameter(torch.FloatTensor(2, self.n_head, self.d_head))

        self.layer_norm = XLNetLayerNorm(config.d_model, eps=config.layer_norm_eps)
        self.dropout = nn.Dropout(config.dropout)

    def prune_heads(self, heads):
        raise NotImplementedError

    @staticmethod
    def rel_shift(x, klen=-1):
        """perform relative shift to form the relative attention score."""
        x_size = x.shape

        x = x.reshape(x_size[1], x_size[0], x_size[2], x_size[3])
        x = x[1:, ...]
        x = x.reshape(x_size[0], x_size[1] - 1, x_size[2], x_size[3])
        # x = x[:, 0:klen, :, :]
        x = torch.index_select(x, 1, torch.arange(klen, device=x.device, dtype=torch.long))

        return x

    @staticmethod
    def rel_shift_bnij(x, klen=-1):
        x_size = x.shape

        x = x.reshape(x_size[0], x_size[1], x_size[3], x_size[2])
        x = x[:, :, 1:, :]
        x = x.reshape(x_size[0], x_size[1], x_size[2], x_size[3]-1)
        # Note: the tensor-slice form was faster in my testing than torch.index_select
        #       However, tracing doesn't like the nature of the slice, and if klen changes
        #       during the run then it'll fail, whereas index_select will be fine.
        x = torch.index_select(x, 3, torch.arange(klen, device=x.device, dtype=torch.long))
        # x = x[:, :, :, :klen]

        return x

    def rel_attn_core(self, q_head, k_head_h, v_head_h, k_head_r, seg_mat=None, attn_mask=None, head_mask=None):
        """Core relative positional attention operations."""

        # content based attention score
        ac = torch.einsum('ibnd,jbnd->bnij', q_head + self.r_w_bias, k_head_h)

        # position based attention score
        bd = torch.einsum('ibnd,jbnd->bnij', q_head + self.r_r_bias, k_head_r)
        bd = self.rel_shift_bnij(bd, klen=ac.shape[3])

        # segment based attention score
        if seg_mat is None:
            ef = 0
        else:
            ef = torch.einsum('ibnd,snd->ibns', q_head + self.r_s_bias, self.seg_embed)
            ef = torch.einsum('ijbs,ibns->bnij', seg_mat, ef)

        # merge attention scores and perform masking
        attn_score = (ac + bd + ef) * self.scale
        if attn_mask is not None:
            # attn_score = attn_score * (1 - attn_mask) - 1e30 * attn_mask
            if attn_mask.dtype == torch.float16:
                attn_score = attn_score - 65500 * torch.einsum('ijbn->bnij', attn_mask)
            else:
                attn_score = attn_score - 1e30 * torch.einsum('ijbn->bnij', attn_mask)

        # attention probability
        attn_prob = F.softmax(attn_score, dim=3)
        attn_prob = self.dropout(attn_prob)

        # Mask heads if we want to
        if head_mask is not None:
            attn_prob = attn_prob * torch.einsum('ijbn->bnij', head_mask)

        # attention output
        attn_vec = torch.einsum('bnij,jbnd->ibnd', attn_prob, v_head_h)

        if self.output_attentions:
            return attn_vec, torch.einsum('bnij->ijbn', attn_prob)

        return attn_vec

    def post_attention(self, h, attn_vec, residual=True):
        """Post-attention processing."""
        # post-attention projection (back to `d_model`)
        attn_out = torch.einsum('ibnd,hnd->ibh', attn_vec, self.o)

        attn_out = self.dropout(attn_out)
        if residual:
            attn_out = attn_out + h
        output = self.layer_norm(attn_out)

        return output

    def forward(self, h, g,
                      attn_mask_h, attn_mask_g,
                      r, seg_mat,
                      mems=None, target_mapping=None, head_mask=None):
        if g is not None:
            ###### Two-stream attention with relative positional encoding.
            # content based attention score
            if mems is not None and mems.dim() > 1:
                cat = torch.cat([mems, h], dim=0)
            else:
                cat = h

            # content-based key head
            k_head_h = torch.einsum('ibh,hnd->ibnd', cat, self.k)

            # content-based value head
            v_head_h = torch.einsum('ibh,hnd->ibnd', cat, self.v)

            # position-based key head
            k_head_r = torch.einsum('ibh,hnd->ibnd', r, self.r)

            ##### h-stream
            # content-stream query head
            q_head_h = torch.einsum('ibh,hnd->ibnd', h, self.q)

            # core attention ops
            attn_vec_h = self.rel_attn_core(
                q_head_h, k_head_h, v_head_h, k_head_r, seg_mat=seg_mat, attn_mask=attn_mask_h, head_mask=head_mask)

            if self.output_attentions:
                attn_vec_h, attn_prob_h = attn_vec_h

            # post processing
            output_h = self.post_attention(h, attn_vec_h)

            ##### g-stream
            # query-stream query head
            q_head_g = torch.einsum('ibh,hnd->ibnd', g, self.q)

            # core attention ops
            if target_mapping is not None:
                q_head_g = torch.einsum('mbnd,mlb->lbnd', q_head_g, target_mapping)
                attn_vec_g = self.rel_attn_core(
                    q_head_g, k_head_h, v_head_h, k_head_r, seg_mat=seg_mat, attn_mask=attn_mask_g, head_mask=head_mask)

                if self.output_attentions:
                    attn_vec_g, attn_prob_g = attn_vec_g

                attn_vec_g = torch.einsum('lbnd,mlb->mbnd', attn_vec_g, target_mapping)
            else:
                attn_vec_g = self.rel_attn_core(
                    q_head_g, k_head_h, v_head_h, k_head_r, seg_mat=seg_mat, attn_mask=attn_mask_g, head_mask=head_mask)

                if self.output_attentions:
                    attn_vec_g, attn_prob_g = attn_vec_g

            # post processing
            output_g = self.post_attention(g, attn_vec_g)

            if self.output_attentions:
                attn_prob = attn_prob_h, attn_prob_g

        else:
            ###### Multi-head attention with relative positional encoding
            if mems is not None and mems.dim() > 1:
                cat = torch.cat([mems, h], dim=0)
            else:
                cat = h

            # content heads
            q_head_h = torch.einsum('ibh,hnd->ibnd', h, self.q)
            k_head_h = torch.einsum('ibh,hnd->ibnd', cat, self.k)
            v_head_h = torch.einsum('ibh,hnd->ibnd', cat, self.v)

            # positional heads
            k_head_r = torch.einsum('ibh,hnd->ibnd', r, self.r)

            # core attention ops
            attn_vec = self.rel_attn_core(
                q_head_h, k_head_h, v_head_h, k_head_r, seg_mat=seg_mat, attn_mask=attn_mask_h, head_mask=head_mask)

            if self.output_attentions:
                attn_vec, attn_prob = attn_vec

            # post processing
            output_h = self.post_attention(h, attn_vec)
            output_g = None

        outputs = (output_h, output_g)
        if self.output_attentions:
            outputs = outputs + (attn_prob,)
        return outputs

class XLNetFeedForward(nn.Module):
    def __init__(self, config):
        super(XLNetFeedForward, self).__init__()
        self.layer_norm = XLNetLayerNorm(config.d_model, eps=config.layer_norm_eps)
        self.layer_1 = nn.Linear(config.d_model, config.d_inner)
        self.layer_2 = nn.Linear(config.d_inner, config.d_model)
        self.dropout = nn.Dropout(config.dropout)
        if isinstance(config.ff_activation, str) or \
                (sys.version_info[0] == 2 and isinstance(config.ff_activation, unicode)):
            self.activation_function = ACT2FN[config.ff_activation]
        else:
            self.activation_function = config.ff_activation

    def forward(self, inp):
        output = inp
        output = self.layer_1(output)
        output = self.activation_function(output)
        output = self.dropout(output)
        output = self.layer_2(output)
        output = self.dropout(output)
        output = self.layer_norm(output + inp)
        return output

class XLNetLayer(nn.Module):
    def __init__(self, config):
        super(XLNetLayer, self).__init__()
        self.rel_attn = XLNetRelativeAttention(config)
        self.ff = XLNetFeedForward(config)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, output_h, output_g,
                attn_mask_h, attn_mask_g,
                r, seg_mat, mems=None, target_mapping=None, head_mask=None):
        outputs = self.rel_attn(output_h, output_g, attn_mask_h, attn_mask_g,
                                r, seg_mat, mems=mems, target_mapping=target_mapping,
                                head_mask=head_mask)
        output_h, output_g = outputs[:2]

        if output_g is not None:
            output_g = self.ff(output_g)
        output_h = self.ff(output_h)

        outputs = (output_h, output_g) + outputs[2:]  # Add again attentions if there are there
        return outputs


class XLNetPreTrainedModel(PreTrainedModel):
    """ An abstract class to handle weights initialization and
        a simple interface for dowloading and loading pretrained models.
    """
    config_class = XLNetConfig
    pretrained_model_archive_map = XLNET_PRETRAINED_MODEL_ARCHIVE_MAP
    load_tf_weights = load_tf_weights_in_xlnet
    base_model_prefix = "transformer"

    def _init_weights(self, module):
        """ Initialize the weights.
        """
        if isinstance(module, (nn.Linear, nn.Embedding)):
            # Slightly different from the TF version which uses truncated_normal for initialization
            # cf https://github.com/pytorch/pytorch/pull/5617
            module.weight.data.normal_(mean=0.0, std=self.config.initializer_range)
            if isinstance(module, nn.Linear) and module.bias is not None:
                module.bias.data.zero_()
        elif isinstance(module, XLNetLayerNorm):
            module.bias.data.zero_()
            module.weight.data.fill_(1.0)
        elif isinstance(module, XLNetRelativeAttention):
            for param in [module.q, module.k, module.v, module.o, module.r,
                          module.r_r_bias, module.r_s_bias, module.r_w_bias,
                          module.seg_embed]:
                param.data.normal_(mean=0.0, std=self.config.initializer_range)
        elif isinstance(module, XLNetModel):
                module.mask_emb.data.normal_(mean=0.0, std=self.config.initializer_range)

class XLNetModel(XLNetPreTrainedModel):
    r"""
    Outputs: `Tuple` comprising various elements depending on the configuration (config) and inputs:
        **last_hidden_state**: ``torch.FloatTensor`` of shape ``(batch_size, sequence_length, hidden_size)``
            Sequence of hidden-states at the last layer of the model.
        **mems**: (`optional`, returned when ``config.mem_len > 0``)
            list of ``torch.FloatTensor`` (one for each layer):
            that contains pre-computed hidden-states (key and values in the attention blocks) as computed by the model
            if config.mem_len > 0 else tuple of None. Can be used to speed up sequential decoding and attend to longer context.
            See details in the docstring of the `mems` input above.
        **hidden_states**: (`optional`, returned when ``config.output_hidden_states=True``)
            list of ``torch.FloatTensor`` (one for the output of each layer + the output of the embeddings)
            of shape ``(batch_size, sequence_length, hidden_size)``:
            Hidden-states of the model at the output of each layer plus the initial embedding outputs.
        **attentions**: (`optional`, returned when ``config.output_attentions=True``)
            list of ``torch.FloatTensor`` (one for each layer) of shape ``(batch_size, num_heads, sequence_length, sequence_length)``:
            Attentions weights after the attention softmax, used to compute the weighted average in the self-attention heads.
    Examples::
        tokenizer = XLNetTokenizer.from_pretrained('xlnet-large-cased')
        model = XLNetModel.from_pretrained('xlnet-large-cased')
        input_ids = torch.tensor(tokenizer.encode("Hello, my dog is cute")).unsqueeze(0)  # Batch size 1
        outputs = model(input_ids)
        last_hidden_states = outputs[0]  # The last hidden-state is the first element of the output tuple
    """
    def __init__(self, config):
        super(XLNetModel, self).__init__(config)
        self.output_attentions = config.output_attentions
        self.output_hidden_states = config.output_hidden_states
        self.output_past = config.output_past

        self.mem_len = config.mem_len
        self.reuse_len = config.reuse_len
        self.d_model = config.d_model
        self.same_length = config.same_length
        self.attn_type = config.attn_type
        self.bi_data = config.bi_data
        self.clamp_len = config.clamp_len
        self.n_layer = config.n_layer

        self.word_embedding = nn.Embedding(config.n_token, config.d_model)
        self.mask_emb = nn.Parameter(torch.FloatTensor(1, 1, config.d_model))
        self.layer = nn.ModuleList([XLNetLayer(config) for _ in range(config.n_layer)])
        self.dropout = nn.Dropout(config.dropout)

        self.init_weights()

    def _resize_token_embeddings(self, new_num_tokens):
        self.word_embedding = self._get_resized_embeddings(self.word_embedding, new_num_tokens)
        return self.word_embedding

    def _prune_heads(self, heads_to_prune):
        raise NotImplementedError

    def create_mask(self, qlen, mlen):
        """
        Creates causal attention mask. Float mask where 1.0 indicates masked, 0.0 indicates not-masked.
        Args:
            qlen: TODO Lysandre didn't fill
            mlen: TODO Lysandre didn't fill
        ::
                  same_length=False:      same_length=True:
                  <mlen > <  qlen >       <mlen > <  qlen >
               ^ [0 0 0 0 0 1 1 1 1]     [0 0 0 0 0 1 1 1 1]
                 [0 0 0 0 0 0 1 1 1]     [1 0 0 0 0 0 1 1 1]
            qlen [0 0 0 0 0 0 0 1 1]     [1 1 0 0 0 0 0 1 1]
                 [0 0 0 0 0 0 0 0 1]     [1 1 1 0 0 0 0 0 1]
               v [0 0 0 0 0 0 0 0 0]     [1 1 1 1 0 0 0 0 0]
        """
        attn_mask = torch.ones([qlen, qlen])
        mask_up = torch.triu(attn_mask, diagonal=1)
        attn_mask_pad = torch.zeros([qlen, mlen])
        ret = torch.cat([attn_mask_pad, mask_up], dim=1)
        if self.same_length:
            mask_lo = torch.tril(attn_mask, diagonal=-1)
            ret = torch.cat([ret[:, :qlen] + mask_lo, ret[:, qlen:]], dim=1)

        ret = ret.to(next(self.parameters()))
        return ret

    def cache_mem(self, curr_out, prev_mem):
        """cache hidden states into memory."""
        if self.reuse_len is not None and self.reuse_len > 0:
            curr_out = curr_out[:self.reuse_len]

        if prev_mem is None:
            new_mem = curr_out[-self.mem_len:]
        else:
            new_mem = torch.cat([prev_mem, curr_out], dim=0)[-self.mem_len:]

        return new_mem.detach()

    @staticmethod
    def positional_embedding(pos_seq, inv_freq, bsz=None):
        sinusoid_inp = torch.einsum('i,d->id', pos_seq, inv_freq)
        pos_emb = torch.cat([torch.sin(sinusoid_inp), torch.cos(sinusoid_inp)], dim=-1)
        pos_emb = pos_emb[:, None, :]

        if bsz is not None:
            pos_emb = pos_emb.expand(-1, bsz, -1)

        return pos_emb

    def relative_positional_encoding(self, qlen, klen, bsz=None):
        """create relative positional encoding."""
        freq_seq = torch.arange(0, self.d_model, 2.0, dtype=torch.float)
        inv_freq = 1 / torch.pow(10000, (freq_seq / self.d_model))

        if self.attn_type == 'bi':
            # beg, end = klen - 1, -qlen
            beg, end = klen, -qlen
        elif self.attn_type == 'uni':
            # beg, end = klen - 1, -1
            beg, end = klen, -1
        else:
            raise ValueError('Unknown `attn_type` {}.'.format(self.attn_type))

        if self.bi_data:
            fwd_pos_seq = torch.arange(beg, end, -1.0, dtype=torch.float)
            bwd_pos_seq = torch.arange(-beg, -end, 1.0, dtype=torch.float)

            if self.clamp_len > 0:
                fwd_pos_seq = fwd_pos_seq.clamp(-self.clamp_len, self.clamp_len)
                bwd_pos_seq = bwd_pos_seq.clamp(-self.clamp_len, self.clamp_len)

            if bsz is not None:
                fwd_pos_emb = self.positional_embedding(fwd_pos_seq, inv_freq, bsz//2)
                bwd_pos_emb = self.positional_embedding(bwd_pos_seq, inv_freq, bsz//2)
            else:
                fwd_pos_emb = self.positional_embedding(fwd_pos_seq, inv_freq)
                bwd_pos_emb = self.positional_embedding(bwd_pos_seq, inv_freq)

            pos_emb = torch.cat([fwd_pos_emb, bwd_pos_emb], dim=1)
        else:
            fwd_pos_seq = torch.arange(beg, end, -1.0)
            if self.clamp_len > 0:
                fwd_pos_seq = fwd_pos_seq.clamp(-self.clamp_len, self.clamp_len)
            pos_emb = self.positional_embedding(fwd_pos_seq, inv_freq, bsz)

        pos_emb = pos_emb.to(next(self.parameters()))
        return pos_emb

    def forward(self, input_ids, attention_mask=None, mems=None, perm_mask=None, target_mapping=None,
                token_type_ids=None, input_mask=None, head_mask=None):
        # the original code for XLNet uses shapes [len, bsz] with the batch dimension at the end
        # but we want a unified interface in the library with the batch size on the first dimension
        # so we move here the first dimension (batch) to the end
        input_ids = input_ids.transpose(0, 1).contiguous()
        token_type_ids = token_type_ids.transpose(0, 1).contiguous() if token_type_ids is not None else None
        input_mask = input_mask.transpose(0, 1).contiguous() if input_mask is not None else None
        attention_mask = attention_mask.transpose(0, 1).contiguous() if attention_mask is not None else None
        perm_mask = perm_mask.permute(1, 2, 0).contiguous() if perm_mask is not None else None
        target_mapping = target_mapping.permute(1, 2, 0).contiguous() if target_mapping is not None else None

        qlen, bsz = input_ids.shape[0], input_ids.shape[1]
        mlen = mems[0].shape[0] if mems is not None and mems[0] is not None else 0
        klen = mlen + qlen

        dtype_float = next(self.parameters()).dtype
        device = next(self.parameters()).device

        ##### Attention mask
        # causal attention mask
        if self.attn_type == 'uni':
            attn_mask = self.create_mask(qlen, mlen)
            attn_mask = attn_mask[:, :, None, None]
        elif self.attn_type == 'bi':
            attn_mask = None
        else:
            raise ValueError('Unsupported attention type: {}'.format(self.attn_type))

        # data mask: input mask & perm mask
        assert input_mask is None or attention_mask is None, "You can only use one of input_mask (uses 1 for padding) "
        "or attention_mask (uses 0 for padding, added for compatbility with BERT). Please choose one."
        if input_mask is None and attention_mask is not None:
            input_mask = 1.0 - attention_mask
        if input_mask is not None and perm_mask is not None:
            data_mask = input_mask[None] + perm_mask
        elif input_mask is not None and perm_mask is None:
            data_mask = input_mask[None]
        elif input_mask is None and perm_mask is not None:
            data_mask = perm_mask
        else:
            data_mask = None

        if data_mask is not None:
            # all mems can be attended to
            if mlen > 0:
                mems_mask = torch.zeros([data_mask.shape[0], mlen, bsz]).to(data_mask)
                data_mask = torch.cat([mems_mask, data_mask], dim=1)
            if attn_mask is None:
                attn_mask = data_mask[:, :, :, None]
            else:
                attn_mask += data_mask[:, :, :, None]

        if attn_mask is not None:
            attn_mask = (attn_mask > 0).to(dtype_float)

        if attn_mask is not None:
            non_tgt_mask = -torch.eye(qlen).to(attn_mask)
            if mlen > 0:
                non_tgt_mask = torch.cat([torch.zeros([qlen, mlen]).to(attn_mask), non_tgt_mask], dim=-1)
            non_tgt_mask = ((attn_mask + non_tgt_mask[:, :, None, None]) > 0).to(attn_mask)
        else:
            non_tgt_mask = None

        ##### Word embeddings and prepare h & g hidden states
        word_emb_k = self.word_embedding(input_ids)
        output_h = self.dropout(word_emb_k)
        if target_mapping is not None:
            word_emb_q = self.mask_emb.expand(target_mapping.shape[0], bsz, -1)
        # else:  # We removed the inp_q input which was same as target mapping
        #     inp_q_ext = inp_q[:, :, None]
        #     word_emb_q = inp_q_ext * self.mask_emb + (1 - inp_q_ext) * word_emb_k
            output_g = self.dropout(word_emb_q)
        else:
            output_g = None

        ##### Segment embedding
        if token_type_ids is not None:
            # Convert `token_type_ids` to one-hot `seg_mat`
            if mlen > 0:
                mem_pad = torch.zeros([mlen, bsz], dtype=torch.long, device=device)
                cat_ids = torch.cat([mem_pad, token_type_ids], dim=0)
            else:
                cat_ids = token_type_ids

            # `1` indicates not in the same segment [qlen x klen x bsz]
            seg_mat = (token_type_ids[:, None] != cat_ids[None, :]).long()
            seg_mat = F.one_hot(seg_mat, num_classes=2).to(dtype_float)
        else:
            seg_mat = None

        ##### Positional encoding
        pos_emb = self.relative_positional_encoding(qlen, klen, bsz=bsz)
        pos_emb = self.dropout(pos_emb)

        # Prepare head mask if needed
        # 1.0 in head_mask indicate we keep the head
        # attention_probs has shape bsz x n_heads x N x N
        # input head_mask has shape [num_heads] or [num_hidden_layers x num_heads] (a head_mask for each layer)
        # and head_mask is converted to shape [num_hidden_layers x qlen x klen x bsz x n_head]
        if head_mask is not None:
            if head_mask.dim() == 1:
                head_mask = head_mask.unsqueeze(0).unsqueeze(0).unsqueeze(0).unsqueeze(0)
                head_mask = head_mask.expand(self.n_layer, -1, -1, -1, -1)
            elif head_mask.dim() == 2:
                head_mask = head_mask.unsqueeze(1).unsqueeze(1).unsqueeze(1)
            head_mask = head_mask.to(dtype=next(self.parameters()).dtype) # switch to fload if need + fp16 compatibility
        else:
            head_mask = [None] * self.n_layer

        new_mems = ()
        if mems is None:
            mems = [None] * len(self.layer)

        attentions = []
        hidden_states = []
        for i, layer_module in enumerate(self.layer):
            if self.mem_len is not None and self.mem_len > 0 and self.output_past:
                # cache new mems
                new_mems = new_mems + (self.cache_mem(output_h, mems[i]),)
            if self.output_hidden_states:
                hidden_states.append((output_h, output_g) if output_g is not None else output_h)

            outputs = layer_module(output_h, output_g, attn_mask_h=non_tgt_mask, attn_mask_g=attn_mask,
                                   r=pos_emb, seg_mat=seg_mat, mems=mems[i], target_mapping=target_mapping,
                                   head_mask=head_mask[i])
            output_h, output_g = outputs[:2]
            if self.output_attentions:
                attentions.append(outputs[2])

        # Add last hidden state
        if self.output_hidden_states:
            hidden_states.append((output_h, output_g) if output_g is not None else output_h)

        output = self.dropout(output_g if output_g is not None else output_h)

        # Prepare outputs, we transpose back here to shape [bsz, len, hidden_dim] (cf. beginning of forward() method)
        outputs = (output.permute(1, 0, 2).contiguous(),)

        if self.mem_len is not None and self.mem_len > 0 and self.output_past:
            outputs = outputs + (new_mems,)

        if self.output_hidden_states:
            if output_g is not None:
                hidden_states = tuple(h.permute(1, 0, 2).contiguous() for hs in hidden_states for h in hs)
            else:
                hidden_states = tuple(hs.permute(1, 0, 2).contiguous() for hs in hidden_states)
            outputs = outputs + (hidden_states,)
        if self.output_attentions:
            attentions = tuple(t.permute(2, 3, 0, 1).contiguous() for t in attentions)
            outputs = outputs + (attentions,)

        return outputs  # outputs, (new_mems), (hidden_states), (attentions)

## Our implementation of XLNetForTokenClassification
class XLNetForTokenClassification(XLNetPreTrainedModel):
  def __init__(self, config):
        super(XLNetForTokenClassification, self).__init__(config)
        self.num_labels = config.num_labels
        self.transformer = XLNetModel(config)
        self.dropout = nn.Dropout(config.dropout)
        self.logits_proj = nn.Linear(config.d_model, config.num_labels)
        self.init_weights()

  def forward(self, input_ids, attention_mask=None, mems=None, perm_mask=None, target_mapping=None,
                token_type_ids=None, input_mask=None, head_mask=None, labels=None):
        transformer_outputs = self.transformer(input_ids,
                                               attention_mask=attention_mask,
                                               mems=mems,
                                               perm_mask=perm_mask,
                                               target_mapping=target_mapping,
                                               token_type_ids=token_type_ids,
                                               input_mask=input_mask,
                                               head_mask=head_mask)
        
        output = transformer_outputs[0]
        output = self.dropout(output)
        logits = self.logits_proj(output)

        return (logits,)

class CueModel:
    def __init__(self, full_finetuning = True, train = False, pretrained_model_path = 'Cue_Detection.pickle', device = 'cuda', learning_rate = 3e-5, class_weight = [100, 100, 100, 1, 0], num_labels = 5):
        self.model_name = CUE_MODEL
        self.task = TASK
        if train == True:
            if 'xlnet' in CUE_MODEL:
                self.model = XLNetForTokenClassification.from_pretrained(CUE_MODEL, num_labels=num_labels, cache_dir = 'xlnet-base-cased-model')
            elif 'roberta' in CUE_MODEL:
                self.model = RobertaForTokenClassification.from_pretrained(CUE_MODEL, num_labels=num_labels, cache_dir = 'roberta-base-model')
            elif 'bert' in CUE_MODEL:
                self.model = BertForTokenClassification.from_pretrained(CUE_MODEL, num_labels=num_labels, cache_dir = 'bert_base_uncased_model')
            else:
                raise ValueError("Supported model types are: xlnet, roberta, bert")
        else:
            self.model = torch.load(pretrained_model_path)
        self.device = torch.device(device)
        self.class_weight = class_weight
        self.learning_rate = learning_rate
        self.num_labels = num_labels
        if device == 'cuda':
            self.model.cuda()
        else:
            self.model.cpu()
            
        if full_finetuning:
            param_optimizer = list(self.model.named_parameters())
            no_decay = ['bias', 'gamma', 'beta']
            optimizer_grouped_parameters = [
                {'params': [p for n, p in param_optimizer if not any(nd in n for nd in no_decay)],
                 'weight_decay_rate': 0.01},
                {'params': [p for n, p in param_optimizer if any(nd in n for nd in no_decay)],
                 'weight_decay_rate': 0.0}
            ]
        else:
            if intermediate_neurons == None:
                param_optimizer = list(self.model.classifier.named_parameters()) 
            else:
                param_optimizer = list(self.model.classifier.named_parameters())+list(self.model.int_layer.named_parameters())
            optimizer_grouped_parameters = [{"params": [p for n, p in param_optimizer]}]
        self.optimizer = Adam(optimizer_grouped_parameters, lr=learning_rate)

    #@telegram_sender(token=TELEGRAM_TOKEN, chat_id=TELEGRAM_CHAT_ID)  
    def train(self, train_dataloader, valid_dataloaders, train_dl_name, val_dl_name, epochs = 5, max_grad_norm = 1.0, patience = 3):
        
        self.train_dl_name = train_dl_name
        return_dict = {"Task": f"{self.task} Cue Detection",
                       "Model": self.model_name,
                       "Train Dataset": train_dl_name,
                       "Val Dataset": val_dl_name,
                       "Best Precision": 0,
                       "Best Recall": 0,
                       "Best F1": 0}
        train_loss = []
        valid_loss = []
        early_stopping = EarlyStopping(patience=patience, verbose=True)
        loss_fn = CrossEntropyLoss(weight=torch.Tensor(self.class_weight).to(self.device))
        for _ in tqdm(range(epochs), desc="Epoch"):
            self.model.train()
            tr_loss = 0
            nb_tr_examples, nb_tr_steps = 0, 0
            for step, batch in enumerate(train_dataloader):
                batch = tuple(t.to(self.device) for t in batch)
                b_input_ids, b_input_mask, b_labels, b_mymasks = batch
                logits = self.model(b_input_ids, token_type_ids=None,attention_mask=b_input_mask)[0]
                active_loss = b_input_mask.view(-1) == 1
                active_logits = logits.view(-1, self.num_labels)[active_loss] #5 is num_labels
                active_labels = b_labels.view(-1)[active_loss]
                loss = loss_fn(active_logits, active_labels)
                loss.backward()
                tr_loss += loss.item()
                if step % 100 == 0:
                    print(f"Batch {step}, loss {loss.item()}")
                train_loss.append(loss.item())
                nb_tr_examples += b_input_ids.size(0)
                nb_tr_steps += 1
                torch.nn.utils.clip_grad_norm_(parameters=self.model.parameters(), max_norm=max_grad_norm)
                self.optimizer.step()
                self.model.zero_grad()
            print("Train loss: {}".format(tr_loss/nb_tr_steps))
            
            self.model.eval()
            eval_loss, eval_accuracy, eval_scope_accuracy, eval_positive_cue_accuracy = 0, 0, 0, 0
            nb_eval_steps, nb_eval_examples, steps_positive_cue_accuracy = 0, 0, 0
            predictions , true_labels, ip_mask = [], [], []
            for valid_dataloader in valid_dataloaders:
                for batch in valid_dataloader:
                    batch = tuple(t.to(self.device) for t in batch)
                    b_input_ids, b_input_mask, b_labels, b_mymasks = batch

                    with torch.no_grad():
                        logits = self.model(b_input_ids, token_type_ids=None, attention_mask=b_input_mask)[0]
                        active_loss = b_input_mask.view(-1) == 1
                        active_logits = logits.view(-1, self.num_labels)[active_loss] #5 is num_labels
                        active_labels = b_labels.view(-1)[active_loss]
                        tmp_eval_loss = loss_fn(active_logits, active_labels)
                        
                    logits = logits.detach().cpu().numpy()
                    label_ids = b_labels.to('cpu').numpy()
                    mymasks = b_mymasks.to('cpu').numpy()
                    
                    if F1_METHOD == 'first_token':

                        logits = [list(p) for p in np.argmax(logits, axis=2)]
                        actual_logits = []
                        actual_label_ids = []
                        for l,lid,m in zip(logits, label_ids, mymasks):
                            actual_logits.append([i for i,j in zip(l,m) if j==1])
                            actual_label_ids.append([i for i,j in zip(lid, m) if j==1])

                        logits = actual_logits
                        label_ids = actual_label_ids

                        predictions.append(logits)
                        true_labels.append(label_ids)
                    
                    elif F1_METHOD == 'average':

                        logits = [list(p) for p in logits]
                        
                        actual_logits = []
                        actual_label_ids = []
                        
                        for l,lid,m in zip(logits, label_ids, mymasks):
                            
                            actual_label_ids.append([i for i,j in zip(lid, m) if j==1])
                            curr_preds = []
                            my_logits = []
                            in_split = 0
                            for i,j in zip(l,m):
                                if j==1:
                                    if in_split == 1:
                                        if len(my_logits)>0:
                                            curr_preds.append(my_logits[-1])
                                        mode_pred = np.argmax(np.average(np.array(curr_preds), axis=0), axis=0)
                                        if len(my_logits)>0:
                                            my_logits[-1] = mode_pred
                                        else:
                                            my_logits.append(mode_pred)
                                        curr_preds = []
                                        in_split = 0
                                    my_logits.append(np.argmax(i))
                                if j==0:
                                    curr_preds.append(i)
                                    in_split = 1
                            if in_split == 1:
                                if len(my_logits)>0:
                                    curr_preds.append(my_logits[-1])
                                mode_pred = np.argmax(np.average(np.array(curr_preds), axis=0), axis=0)
                                if len(my_logits)>0:
                                    my_logits[-1] = mode_pred
                                else:
                                    my_logits.append(mode_pred)
                            actual_logits.append(my_logits)
                            
                        logits = actual_logits
                        label_ids = actual_label_ids
                        
                        predictions.append(logits)
                        true_labels.append(label_ids)
                    
                    tmp_eval_accuracy = flat_accuracy(logits, label_ids)
                    tmp_eval_positive_cue_accuracy = flat_accuracy_positive_cues(logits, label_ids)
                    eval_loss += tmp_eval_loss.mean().item()
                    valid_loss.append(tmp_eval_loss.mean().item())
                    eval_accuracy += tmp_eval_accuracy
                    if tmp_eval_positive_cue_accuracy!=None:
                        eval_positive_cue_accuracy+=tmp_eval_positive_cue_accuracy
                        steps_positive_cue_accuracy+=1
                    nb_eval_examples += b_input_ids.size(0)
                    nb_eval_steps += 1
                eval_loss = eval_loss/nb_eval_steps
                
            print("Validation loss: {}".format(eval_loss))
            print("Validation Accuracy: {}".format(eval_accuracy/nb_eval_steps))
            print("Validation Accuracy for Positive Cues: {}".format(eval_positive_cue_accuracy/steps_positive_cue_accuracy))
            labels_flat = [l_ii for l in true_labels for l_i in l for l_ii in l_i]
            pred_flat = [p_ii for p in predictions for p_i in p for p_ii in p_i]
            pred_flat = [p for p,l in zip(pred_flat, labels_flat) if l!=4]
            labels_flat = [l for l in labels_flat if l!=4]
            report_per_class_accuracy(labels_flat, pred_flat)
            print(classification_report(labels_flat, pred_flat))
            print("F1-Score Overall: {}".format(f1_score(labels_flat,pred_flat, average='weighted')))
            p,r,f1 = f1_cues(labels_flat, pred_flat)
            if f1>return_dict['Best F1']:
                return_dict['Best F1'] = f1
                return_dict['Best Precision'] = p
                return_dict['Best Recall'] = r
            early_stopping(f1, self.model)
        
            if early_stopping.early_stop:
                print("Early stopping")
                break

            labels_flat = [int(i!=3) for i in labels_flat]
            pred_flat = [int(i!=3) for i in pred_flat]
            print("F1-Score Cue_No Cue: {}".format(f1_score(labels_flat,pred_flat, average='weighted')))
            
        self.model.load_state_dict(torch.load('checkpoint.pt'))
        plt.xlabel("Iteration")
        plt.ylabel("Train Loss")
        plt.plot([i for i in range(len(train_loss))], train_loss)
        plt.figure()
        plt.xlabel("Iteration")
        plt.ylabel("Validation Loss")
        plt.plot([i for i in range(len(valid_loss))], valid_loss)
        return return_dict

    #@telegram_sender(token=TELEGRAM_TOKEN, chat_id=TELEGRAM_CHAT_ID)
    def evaluate(self, test_dataloader, test_dl_name):
        return_dict = {"Task": f"{self.task} Cue Detection",
                       "Model": self.model_name,
                       "Train Dataset": self.train_dl_name,
                       "Test Dataset": test_dl_name,
                       "Precision": 0,
                       "Recall": 0,
                       "F1": 0}
        self.model.eval()
        eval_loss, eval_accuracy, eval_scope_accuracy, eval_positive_cue_accuracy = 0, 0, 0, 0
        nb_eval_steps, nb_eval_examples, steps_positive_cue_accuracy = 0, 0, 0
        predictions , true_labels, ip_mask = [], [], []
        loss_fn = CrossEntropyLoss(weight=torch.Tensor(self.class_weight).to(self.device))
        for batch in test_dataloader:
            batch = tuple(t.to(self.device) for t in batch)
            b_input_ids, b_input_mask, b_labels, b_mymasks = batch
            
            with torch.no_grad():
                logits = self.model(b_input_ids, token_type_ids=None,attention_mask=b_input_mask)[0]
                active_loss = b_input_mask.view(-1) == 1
                active_logits = logits.view(-1, self.num_labels)[active_loss] #5 is num_labels
                active_labels = b_labels.view(-1)[active_loss]
                tmp_eval_loss = loss_fn(active_logits, active_labels)
                logits = logits.detach().cpu().numpy()
            label_ids = b_labels.to('cpu').numpy()
            mymasks = b_mymasks.to('cpu').numpy()

            if F1_METHOD == 'first_token':

                logits = [list(p) for p in np.argmax(logits, axis=2)]
                actual_logits = []
                actual_label_ids = []
                for l,lid,m in zip(logits, label_ids, mymasks):
                    actual_logits.append([i for i,j in zip(l,m) if j==1])
                    actual_label_ids.append([i for i,j in zip(lid, m) if j==1])

                logits = actual_logits
                label_ids = actual_label_ids

                predictions.append(logits)
                true_labels.append(label_ids)

            elif F1_METHOD == 'average':
                logits = [list(p) for p in logits]
                    
                actual_logits = []
                actual_label_ids = []
                for l,lid,m in zip(logits, label_ids, mymasks):
                        
                    actual_label_ids.append([i for i,j in zip(lid, m) if j==1])
                    my_logits = []
                    curr_preds = []
                    in_split = 0
                    for i,j in zip(l,m):
                        if j==1:
                            if in_split == 1:
                                if len(my_logits)>0:
                                    curr_preds.append(my_logits[-1])
                                mode_pred = np.argmax(np.average(np.array(curr_preds), axis=0), axis=0)
                                if len(my_logits)>0:
                                    my_logits[-1] = mode_pred
                                else:
                                    my_logits.append(mode_pred)
                                curr_preds = []
                                in_split = 0
                            my_logits.append(np.argmax(i))
                        if j==0:
                            curr_preds.append(i)
                            in_split = 1
                    if in_split == 1:
                        if len(my_logits)>0:
                            curr_preds.append(my_logits[-1])
                        mode_pred = np.argmax(np.average(np.array(curr_preds), axis=0), axis=0)
                        if len(my_logits)>0:
                            my_logits[-1] = mode_pred
                        else:
                            my_logits.append(mode_pred)
                    actual_logits.append(my_logits)

                logits = actual_logits
                label_ids = actual_label_ids
                
                predictions.append(logits)
                true_labels.append(label_ids)    
                
            tmp_eval_accuracy = flat_accuracy(logits, label_ids)
            tmp_eval_positive_cue_accuracy = flat_accuracy_positive_cues(logits, label_ids)
        
            eval_loss += tmp_eval_loss.mean().item()
            eval_accuracy += tmp_eval_accuracy
            if tmp_eval_positive_cue_accuracy != None:
                eval_positive_cue_accuracy += tmp_eval_positive_cue_accuracy
                steps_positive_cue_accuracy+=1
            nb_eval_examples += b_input_ids.size(0)
            nb_eval_steps += 1
        eval_loss = eval_loss/nb_eval_steps
        print("Validation loss: {}".format(eval_loss))
        print("Validation Accuracy: {}".format(eval_accuracy/nb_eval_steps))
        print("Validation Accuracy for Positive Cues: {}".format(eval_positive_cue_accuracy/steps_positive_cue_accuracy))
        labels_flat = [l_ii for l in true_labels for l_i in l for l_ii in l_i]
        pred_flat = [p_ii for p in predictions for p_i in p for p_ii in p_i]
        pred_flat = [p for p,l in zip(pred_flat, labels_flat) if l!=4]
        labels_flat = [l for l in labels_flat if l!=4]
        report_per_class_accuracy(labels_flat, pred_flat)
        print(classification_report(labels_flat, pred_flat))
        print("F1-Score: {}".format(f1_score(labels_flat,pred_flat,average='weighted')))
        p,r,f1 = f1_cues(labels_flat, pred_flat)
        return_dict['Precision'] = p
        return_dict['Recall'] = r
        return_dict['F1'] = f1
        labels_flat = [int(i!=3) for i in labels_flat]
        pred_flat = [int(i!=3) for i in pred_flat]
        print("F1-Score Cue_No Cue: {}".format(f1_score(labels_flat,pred_flat,average='weighted')))
        return return_dict

    def predict(self, dataloader):
        self.model.eval()
        predictions, ip_mask = [], []
        for batch in dataloader:
            batch = tuple(t.to(self.device) for t in batch)
            b_input_ids, b_input_mask, b_mymasks = batch

            with torch.no_grad():
                logits = self.model(b_input_ids, token_type_ids=None, attention_mask=b_input_mask)[0]
            logits = logits.detach().cpu().numpy()
            mymasks = b_mymasks.to('cpu').numpy()
            #predictions.extend([list(p) for p in np.argmax(logits, axis=2)])
            if F1_METHOD == 'first_token':

                logits = [list(p) for p in np.argmax(logits, axis=2)]
                actual_logits = []
                for l,m in zip(logits, mymasks):
                    actual_logits.append([i for i,j in zip(l,m) if j==1])
                
                predictions.append(actual_logits)

            elif F1_METHOD == 'average':
                logits = [list(p) for p in logits]
                    
                actual_logits = []
                actual_label_ids = []
                for l,m in zip(logits, mymasks):
                    my_logits = []
                    curr_preds = []
                    in_split = 0
                    for i,j in zip(l,m):
                        if j==1:
                            if in_split == 1:
                                if len(my_logits)>0:
                                    curr_preds.append(my_logits[-1])
                                mode_pred = np.argmax(np.average(np.array(curr_preds), axis=0), axis=0)
                                if len(my_logits)>0:
                                    my_logits[-1] = mode_pred
                                else:
                                    my_logits.append(mode_pred)
                                curr_preds = []
                                in_split = 0
                            my_logits.append(np.argmax(i))
                        if j==0:
                            curr_preds.append(i)
                            in_split = 1
                    if in_split == 1:
                        if len(my_logits)>0:
                            curr_preds.append(my_logits[-1])
                        mode_pred = np.argmax(np.average(np.array(curr_preds), axis=0), axis=0)
                        if len(my_logits)>0:
                            my_logits[-1] = mode_pred
                        else:
                            my_logits.append(mode_pred)
                    actual_logits.append(my_logits)
                predictions.append(actual_logits)
                
        return predictions

class ScopeModel:
    def __init__(self, full_finetuning = True, train = False, pretrained_model_path = 'Scope_Resolution_Augment.pickle', device = 'cuda', learning_rate = 3e-5):
        self.model_name = SCOPE_MODEL
        self.task = TASK
        self.num_labels = 2
        if train == True:
            if 'xlnet' in SCOPE_MODEL:
                self.model = XLNetForTokenClassification.from_pretrained(SCOPE_MODEL, num_labels=self.num_labels, cache_dir = 'xlnet-base-cased-model')
            elif 'roberta' in SCOPE_MODEL:
                self.model = RobertaForTokenClassification.from_pretrained(SCOPE_MODEL, num_labels=self.num_labels, cache_dir = 'roberta-base-model')
            elif 'bert' in SCOPE_MODEL:
                self.model = BertForTokenClassification.from_pretrained(SCOPE_MODEL, num_labels=self.num_labels, cache_dir = 'bert_base_uncased_model')
            else:
                raise ValueError("Supported model types are: xlnet, roberta, bert")
        else:
            self.model = torch.load(pretrained_model_path)
        self.device = torch.device(device)
        if device=='cuda':
            self.model.cuda()
        else:
            self.model.cpu()

        if full_finetuning:
            param_optimizer = list(self.model.named_parameters())
            no_decay = ['bias', 'gamma', 'beta']
            optimizer_grouped_parameters = [
                {'params': [p for n, p in param_optimizer if not any(nd in n for nd in no_decay)],
                 'weight_decay_rate': 0.01},
                {'params': [p for n, p in param_optimizer if any(nd in n for nd in no_decay)],
                 'weight_decay_rate': 0.0}
            ]
        else:
            param_optimizer = list(self.model.classifier.named_parameters()) 
            optimizer_grouped_parameters = [{"params": [p for n, p in param_optimizer]}]
        self.optimizer = Adam(optimizer_grouped_parameters, lr=learning_rate)

    #@telegram_sender(token=TELEGRAM_TOKEN, chat_id=TELEGRAM_CHAT_ID)    
    def train(self, train_dataloader, valid_dataloaders, train_dl_name, val_dl_name, epochs = 5, max_grad_norm = 1.0, patience = 3):
        self.train_dl_name = train_dl_name
        return_dict = {"Task": f"{self.task} Scope Resolution",
                       "Model": self.model_name,
                       "Train Dataset": train_dl_name,
                       "Val Dataset": val_dl_name,
                       "Best Precision": 0,
                       "Best Recall": 0,
                       "Best F1": 0}
        train_loss = []
        valid_loss = []
        early_stopping = EarlyStopping(patience=patience, verbose=True)
        loss_fn = CrossEntropyLoss()
        for _ in tqdm(range(epochs), desc="Epoch"):
            self.model.train()
            tr_loss = 0
            nb_tr_examples, nb_tr_steps = 0, 0
            for step, batch in enumerate(train_dataloader):
                batch = tuple(t.to(self.device) for t in batch)
                b_input_ids, b_input_mask, b_labels, b_mymasks = batch
                logits = self.model(b_input_ids, token_type_ids=None,
                             attention_mask=b_input_mask)[0]
                active_loss = b_input_mask.view(-1) == 1
                active_logits = logits.view(-1, self.num_labels)[active_loss] #2 is num_labels
                active_labels = b_labels.view(-1)[active_loss]
                loss = loss_fn(active_logits, active_labels)
                loss.backward()
                tr_loss += loss.item()
                train_loss.append(loss.item())
                if step%100 == 0:
                    print(f"Batch {step}, loss {loss.item()}")
                nb_tr_examples += b_input_ids.size(0)
                nb_tr_steps += 1
                torch.nn.utils.clip_grad_norm_(parameters=self.model.parameters(), max_norm=max_grad_norm)
                self.optimizer.step()
                self.model.zero_grad()
            print("Train loss: {}".format(tr_loss/nb_tr_steps))
            
            self.model.eval()
            
            eval_loss, eval_accuracy, eval_scope_accuracy = 0, 0, 0
            nb_eval_steps, nb_eval_examples = 0, 0
            predictions , true_labels, ip_mask = [], [], []
            loss_fn = CrossEntropyLoss()
            for valid_dataloader in valid_dataloaders:
                for batch in valid_dataloader:
                    batch = tuple(t.to(self.device) for t in batch)
                    b_input_ids, b_input_mask, b_labels, b_mymasks = batch

                    with torch.no_grad():
                        logits = self.model(b_input_ids, token_type_ids=None,
                                      attention_mask=b_input_mask)[0]
                        active_loss = b_input_mask.view(-1) == 1
                        active_logits = logits.view(-1, self.num_labels)[active_loss]
                        active_labels = b_labels.view(-1)[active_loss]
                        tmp_eval_loss = loss_fn(active_logits, active_labels)
                        
                    logits = logits.detach().cpu().numpy()
                    label_ids = b_labels.to('cpu').numpy()
                    b_input_ids = b_input_ids.to('cpu').numpy()

                    mymasks = b_mymasks.to('cpu').numpy()
                        
                    if F1_METHOD == 'first_token':

                        logits = [list(p) for p in np.argmax(logits, axis=2)]
                        actual_logits = []
                        actual_label_ids = []
                        for l,lid,m in zip(logits, label_ids, mymasks):
                            actual_logits.append([i for i,j in zip(l,m) if j==1])
                            actual_label_ids.append([i for i,j in zip(lid, m) if j==1])

                        logits = actual_logits
                        label_ids = actual_label_ids

                        predictions.append(logits)
                        true_labels.append(label_ids)
                    elif F1_METHOD == 'average':
                      
                        logits = [list(p) for p in logits]
                    
                        actual_logits = []
                        actual_label_ids = []
                        
                        for l,lid,m,b_ii in zip(logits, label_ids, mymasks, b_input_ids):
                                
                            actual_label_ids.append([i for i,j in zip(lid, m) if j==1])
                            my_logits = []
                            curr_preds = []
                            in_split = 0
                            for i,j,k in zip(l,m, b_ii):
                                '''if k == 0:
                                    break'''
                                if j==1:
                                    if in_split == 1:
                                        if len(my_logits)>0:
                                            curr_preds.append(my_logits[-1])
                                        mode_pred = np.argmax(np.average(np.array(curr_preds), axis=0), axis=0)
                                        if len(my_logits)>0:
                                            my_logits[-1] = mode_pred
                                        else:
                                            my_logits.append(mode_pred)
                                        curr_preds = []
                                        in_split = 0
                                    my_logits.append(np.argmax(i))
                                if j==0:
                                    curr_preds.append(i)
                                    in_split = 1
                            if in_split == 1:
                                if len(my_logits)>0:
                                    curr_preds.append(my_logits[-1])
                                mode_pred = np.argmax(np.average(np.array(curr_preds), axis=0), axis=0)
                                if len(my_logits)>0:
                                    my_logits[-1] = mode_pred
                                else:
                                    my_logits.append(mode_pred)
                            actual_logits.append(my_logits)
                            
                        predictions.append(actual_logits)
                        true_labels.append(actual_label_ids)    
                        
                    tmp_eval_accuracy = flat_accuracy(actual_logits, actual_label_ids)
                    tmp_eval_scope_accuracy = scope_accuracy(actual_logits, actual_label_ids)
                    eval_scope_accuracy += tmp_eval_scope_accuracy
                    valid_loss.append(tmp_eval_loss.mean().item())

                    eval_loss += tmp_eval_loss.mean().item()
                    eval_accuracy += tmp_eval_accuracy

                    nb_eval_examples += len(b_input_ids)
                    nb_eval_steps += 1
                eval_loss = eval_loss/nb_eval_steps
            print("Validation loss: {}".format(eval_loss))
            print("Validation Accuracy: {}".format(eval_accuracy/nb_eval_steps))
            print("Validation Accuracy Scope Level: {}".format(eval_scope_accuracy/nb_eval_steps))
            f1_scope([j for i in true_labels for j in i], [j for i in predictions for j in i], level='scope')
            labels_flat = [l_ii for l in true_labels for l_i in l for l_ii in l_i]
            pred_flat = [p_ii for p in predictions for p_i in p for p_ii in p_i]
            classification_dict = classification_report(labels_flat, pred_flat, output_dict= True)
            p = classification_dict["1"]["precision"]
            r = classification_dict["1"]["recall"]
            f1 = classification_dict["1"]["f1-score"]
            if f1>return_dict['Best F1']:
                return_dict['Best F1'] = f1
                return_dict['Best Precision'] = p
                return_dict['Best Recall'] = r
            print("F1-Score Token: {}".format(f1))
            print(classification_report(labels_flat, pred_flat))
            early_stopping(f1, self.model)
            if early_stopping.early_stop:
                print("Early stopping")
                break
        
        self.model.load_state_dict(torch.load('checkpoint.pt'))
        plt.xlabel("Iteration")
        plt.ylabel("Train Loss")
        plt.plot([i for i in range(len(train_loss))], train_loss)
        plt.figure()
        plt.xlabel("Iteration")
        plt.ylabel("Validation Loss")
        plt.plot([i for i in range(len(valid_loss))], valid_loss)
        return return_dict

    #@telegram_sender(token=TELEGRAM_TOKEN, chat_id=TELEGRAM_CHAT_ID)
    def evaluate(self, test_dataloader, test_dl_name = "SFU"):
        return_dict = {"Task": f"{self.task} Scope Resolution",
                       "Model": self.model_name,
                       "Train Dataset": self.train_dl_name,
                       "Test Dataset": test_dl_name,
                       "Precision": 0,
                       "Recall": 0,
                       "F1": 0}
        self.model.eval()
        eval_loss, eval_accuracy, eval_scope_accuracy = 0, 0, 0
        nb_eval_steps, nb_eval_examples = 0, 0
        predictions , true_labels, ip_mask = [], [], []
        loss_fn = CrossEntropyLoss()
        for batch in test_dataloader:
            batch = tuple(t.to(self.device) for t in batch)
            b_input_ids, b_input_mask, b_labels, b_mymasks = batch

            with torch.no_grad():
                logits = self.model(b_input_ids, token_type_ids=None,
                               attention_mask=b_input_mask)[0]
                active_loss = b_input_mask.view(-1) == 1
                active_logits = logits.view(-1, self.num_labels)[active_loss] #5 is num_labels
                active_labels = b_labels.view(-1)[active_loss]
                tmp_eval_loss = loss_fn(active_logits, active_labels)
                
            logits = logits.detach().cpu().numpy()
            label_ids = b_labels.to('cpu').numpy()
            b_input_ids = b_input_ids.to('cpu').numpy()
            
            mymasks = b_mymasks.to('cpu').numpy()

            if F1_METHOD == 'first_token':

                logits = [list(p) for p in np.argmax(logits, axis=2)]
                actual_logits = []
                actual_label_ids = []
                for l,lid,m in zip(logits, label_ids, mymasks):
                    actual_logits.append([i for i,j in zip(l,m) if j==1])
                    actual_label_ids.append([i for i,j in zip(lid, m) if j==1])

                logits = actual_logits
                label_ids = actual_label_ids

                predictions.append(logits)
                true_labels.append(label_ids)

            elif F1_METHOD == 'average':
                
                logits = [list(p) for p in logits]
                
                actual_logits = []
                actual_label_ids = []
                
                for l,lid,m,b_ii in zip(logits, label_ids, mymasks, b_input_ids):
                        
                    actual_label_ids.append([i for i,j in zip(lid, m) if j==1])
                    my_logits = []
                    curr_preds = []
                    in_split = 0
                    for i,j,k in zip(l,m,b_ii):
                        '''if k == 0:
                            break'''
                        if j==1:
                            if in_split == 1:
                                if len(my_logits)>0:
                                    curr_preds.append(my_logits[-1])
                                mode_pred = np.argmax(np.average(np.array(curr_preds), axis=0), axis=0)
                                if len(my_logits)>0:
                                    my_logits[-1] = mode_pred
                                else:
                                    my_logits.append(mode_pred)
                                curr_preds = []
                                in_split = 0
                            my_logits.append(np.argmax(i))
                        if j==0:
                            curr_preds.append(i)
                            in_split = 1
                    if in_split == 1:
                        if len(my_logits)>0:
                            curr_preds.append(my_logits[-1])
                        mode_pred = np.argmax(np.average(np.array(curr_preds), axis=0), axis=0)
                        if len(my_logits)>0:
                            my_logits[-1] = mode_pred
                        else:
                            my_logits.append(mode_pred)
                    actual_logits.append(my_logits)
                    
                predictions.append(actual_logits)
                true_labels.append(actual_label_ids)

            tmp_eval_accuracy = flat_accuracy(actual_logits, actual_label_ids)
            tmp_eval_scope_accuracy = scope_accuracy(actual_logits, actual_label_ids)
            eval_scope_accuracy += tmp_eval_scope_accuracy

            eval_loss += tmp_eval_loss.mean().item()
            eval_accuracy += tmp_eval_accuracy

            nb_eval_examples += len(b_input_ids)
            nb_eval_steps += 1
        eval_loss = eval_loss/nb_eval_steps
        print("Validation loss: {}".format(eval_loss))
        print("Validation Accuracy: {}".format(eval_accuracy/nb_eval_steps))
        print("Validation Accuracy Scope Level: {}".format(eval_scope_accuracy/nb_eval_steps))
        f1_scope([j for i in true_labels for j in i], [j for i in predictions for j in i], level='scope')
        labels_flat = [l_ii for l in true_labels for l_i in l for l_ii in l_i]
        pred_flat = [p_ii for p in predictions for p_i in p for p_ii in p_i]
        classification_dict = classification_report(labels_flat, pred_flat, output_dict= True)
        p = classification_dict["1"]["precision"]
        r = classification_dict["1"]["recall"]
        f1 = classification_dict["1"]["f1-score"]
        return_dict['Precision'] = p
        return_dict['Recall'] = r
        return_dict['F1'] = f1
        print("Classification Report:")
        print(classification_report(labels_flat, pred_flat))
        return return_dict

    def predict(self, dataloader):
        self.model.eval()
        predictions, ip_mask = [], []
        for batch in dataloader:
            batch = tuple(t.to(self.device) for t in batch)
            b_input_ids, b_input_mask, b_mymasks = batch

            with torch.no_grad():
                logits = self.model(b_input_ids, token_type_ids=None, attention_mask=b_input_mask)[0]
            logits = logits.detach().cpu().numpy()
            mymasks = b_mymasks.to('cpu').numpy()

            if F1_METHOD == 'first_token':

                logits = [list(p) for p in np.argmax(logits, axis=2)]
                actual_logits = []
                for l,lid,m in zip(logits, label_ids, mymasks):
                    actual_logits.append([i for i,j in zip(l,m) if j==1])
                
                logits = actual_logits
                label_ids = actual_label_ids

                predictions.append(logits)
                true_labels.append(label_ids)

            elif F1_METHOD == 'average':
                
                logits = [list(p) for p in logits]
                
                actual_logits = []
                
                for l,m in zip(logits, mymasks):
                        
                    my_logits = []
                    curr_preds = []
                    in_split = 0
                    for i,j in zip(l,m):
                        
                        if j==1:
                            if in_split == 1:
                                if len(my_logits)>0:
                                    curr_preds.append(my_logits[-1])
                                mode_pred = np.argmax(np.average(np.array(curr_preds), axis=0), axis=0)
                                if len(my_logits)>0:
                                    my_logits[-1] = mode_pred
                                else:
                                    my_logits.append(mode_pred)
                                curr_preds = []
                                in_split = 0
                            my_logits.append(np.argmax(i))
                        if j==0:
                            curr_preds.append(i)
                            in_split = 1
                    if in_split == 1:
                        if len(my_logits)>0:
                            curr_preds.append(my_logits[-1])
                        mode_pred = np.argmax(np.average(np.array(curr_preds), axis=0), axis=0)
                        if len(my_logits)>0:
                            my_logits[-1] = mode_pred
                        else:
                            my_logits.append(mode_pred)
                    actual_logits.append(my_logits)
                    
                predictions.append(actual_logits)
        return predictions

