"""
    Various utility methods
"""
import csv
import json
import math
import os
import pickle

import torch
from torch.autograd import Variable

from learn import models
from constants import *
import datasets
import persistence
import numpy as np

def pick_model(args, dicts, label_weight=None):
    """
        Use args to initialize the appropriate model
    """
    Y = len(dicts['ind2c'])
    if args.model == "rnn":
        model = models.VanillaRNN(Y, args.embed_file, dicts, args.rnn_dim, args.cell_type, args.rnn_layers, args.gpu, args.embed_size,
                                  args.bidirectional)
    elif args.model == "cnn_vanilla":
        filter_size = int(args.filter_size)
        model = models.VanillaConv(Y, args.embed_file, filter_size, args.num_filter_maps, args.gpu, dicts, args.embed_size, args.dropout)
    elif args.model == "conv_attn":
        filter_size = int(args.filter_size)
        model = models.ConvAttnPool(args, Y, args.embed_file, filter_size, args.num_filter_maps, args.lmbda, args.gpu, dicts,
                                    embed_size=args.embed_size, dropout=args.dropout, code_emb=args.code_emb)
    elif args.model == 'conv_attn_ldep':
        filter_size = int(args.filter_size)
        model = models.ConvAttnPool_ldep(Y, args.embed_file, filter_size, args.num_filter_maps, args.lmbda, args.gpu, dicts,
                                    embed_size=args.embed_size, dropout=args.dropout, code_emb=args.code_emb)
    elif args.model == "logreg":
        model = models.BOWPool(Y, args.embed_file, args.lmbda, args.gpu, dicts, args.pool, args.embed_size, args.dropout, args.code_emb)

    elif args.model == 'bert_conv':
        filter_size = int(args.filter_size)
        model = models.Bert_Conv(Y, args.embed_file, filter_size, args.num_filter_maps, args.lmbda, args.gpu, dicts,
                                     args.bert_dir,
                                     embed_size=args.embed_size, dropout=args.dropout, code_emb=args.code_emb)

    elif args.model == 'bert_pooling':
        filter_size = int(args.filter_size)
        model = models.Bert_Pooling(Y, args.embed_file, filter_size, args.num_filter_maps, args.lmbda, args.gpu, dicts,
                                     args.bert_dir,
                                     embed_size=args.embed_size, dropout=args.dropout, code_emb=args.code_emb)
    elif args.model == 'multi_conv_attn':
        filter_size = int(args.filter_size)
        model = models.MultiConvAttnPool(args, Y, args.embed_file, filter_size, args.num_filter_maps, args.lmbda, args.gpu, dicts,
                                         args.conv_layer, args.use_res,
                                    embed_size=args.embed_size, dropout=args.dropout, code_emb=args.code_emb)

    elif args.model == 'conv_attn_lco':
        filter_size = int(args.filter_size)
        model = models.ConvAttnPool_lco(args, Y, args.embed_file, filter_size, args.num_filter_maps, args.lmbda, args.gpu, dicts,
                                    embed_size=args.embed_size, dropout=args.dropout, code_emb=args.code_emb)
    elif args.model == 'transformer1':
        model = models.Transformer1(args, Y)
    elif args.model == 'transformer2':
        model = models.Transformer2(args, Y)
    elif args.model == 'transformer3':
        model = models.Transformer3(args, Y)
    elif args.model == 'transformer4':
        model = models.Transformer4(args, Y)
    elif args.model == 'bert_seq_cls':
        model = models.Bert_seq_cls(args, Y)
    elif args.model == 'CNN':
        model = models.CNN(args, Y, dicts)
    elif args.model == 'TFIDF':
        model = models.TFIDF(args, Y)
    elif args.model == 'MultiCNN':
        model = models.MultiCNN(args, Y, dicts)
    elif args.model == 'ResCNN':
        model = models.ResCNN(args, Y, dicts)
    elif args.model == 'MultiResCNN':
        model = models.MultiResCNN(args, Y, dicts)
    else:
        raise RuntimeError("wrong model name")

    if args.test_model:
        sd = torch.load(args.test_model)
        model.load_state_dict(sd)
    if args.gpu >= 0:
        model.cuda(args.gpu)
    return model

def pick_model1(args, dicts, all_data):
    Y = len(dicts['ind2c'])

    if args.mode == 'sp-mtl' and args.model == 'MultiResCNN':
        output_layers = []
        feature_extractor = models.MultiResCNN_Feature(args, Y, dicts)
        if args.gpu >= 0:
            feature_extractor = feature_extractor.cuda(args.gpu)
        for data in all_data:
            ol = models.Output_Layer(args, Y, dicts)
            if args.gpu >= 0:
                ol = ol.cuda(args.gpu)
            output_layers.append(ol)

    else:
        raise RuntimeError("wrong model or mode name")

    return feature_extractor, output_layers


def make_param_dict(args):
    """
        Make a list of parameters to save for future reference
    """
    param_vals = [args.Y, args.filter_size, args.dropout, args.num_filter_maps, args.rnn_dim, args.cell_type, args.rnn_layers, 
                  args.lmbda, args.command, args.weight_decay, args.version, args.data_path, args.vocab, args.embed_file, args.lr]
    param_names = ["Y", "filter_size", "dropout", "num_filter_maps", "rnn_dim", "cell_type", "rnn_layers", "lmbda", "command",
                   "weight_decay", "version", "data_path", "vocab", "embed_file", "lr"]
    params = {name:val for name, val in zip(param_names, param_vals) if val is not None}
    return params

def build_code_vecs(code_inds, dicts):
    """
        Get vocab-indexed arrays representing words in descriptions of each *unseen* label
    """
    code_inds = list(code_inds)
    ind2w, ind2c, dv_dict = dicts['ind2w'], dicts['ind2c'], dicts['dv']
    vecs = []
    for c in code_inds:
        code = ind2c[c]
        if code in dv_dict.keys():
            vecs.append(dv_dict[code])
        else:
            #vec is a single UNK if not in lookup
            vecs.append([len(ind2w) + 1])
    #pad everything
    vecs = datasets.pad_desc_vecs(vecs)
    return (torch.cuda.LongTensor(code_inds), vecs)

