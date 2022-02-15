# -*- coding: utf-8 -*-
"""
Copyright (c) 2022, Ocean Perception Lab, Univ. of Southampton
All rights reserved.
Licensed under GNU General Public License v3.0
See LICENSE file in the project root for full license information.
"""
# Author: Jose Cappelletto (j.cappelletto@soton.ac.uk) 

# Import general libraries
import re # Regular expressions (eventually to be deprecated)
import sys
import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
import pandas as pd
import argparse
# Import blitz (BNN) modules
from blitz.modules import BayesianLinear
from blitz.utils import variational_estimator
# Import sklearn dataset parsers and samples
from sklearn.datasets import load_boston
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
# Helper libaries (viz)
import matplotlib.pyplot as plt
# Toolkit
from tools.console import Console
from tools.dataloader import CustomDataloader
from tools.predictor import PredictiveEngine
from tools.bnn_model import BayesianRegressor
import tools.parser as par
import statistics
import math

def main(args=None):
    description_str = "Bayesian Neural Network inference module to predict terrain related derivatives from low-resolution priors"
    formatter = lambda prog: argparse.HelpFormatter(prog, width=120)
    parser = argparse.ArgumentParser(description=description_str, formatter_class=formatter)
    # argparse.HelpFormatter(parser,'width=120')
    par.add_arguments(parser)

    if len(sys.argv) == 1 and args is None: # no argument passed? error, some parameters were expected
        # Show help if no args provided
        parser.print_help(sys.stderr)
        sys.exit(2)
    args = parser.parse_args(args)  # retrieve parsed arguments
    Console.info("Bayesian Neural Network for hi-res inference from low res acoustic priors (LGA-Bathymetry)")

    # we are in prediction (inference) mode
    Console.info("Prediction mode enabled. Looking for pretained network and input latent vectors")
    # Looking for CSV with latent vectors (input)
    if os.path.isfile(args.input):
        Console.info("Latent input file: ", args.input)
    else:
        Console.error("Latent input file [" + args.input + "] not found. Please check the provided input path (-l, --latent)")

    # check for pre-trained network
    if os.path.isfile(args.network):
        Console.info("Pre-trained network file [", args.network, "] found")
    else:
        Console.error("No pre-trained network found at: ", args.network)
        Console.info ("Terminating...")
        return -1
    # if output file exists, warn user
    if os.path.isfile(args.output):
        Console.warn("Output file [", args.output, "] already exists. It will be overwritten (default action)")
    else:
        Console.info("Output file: ", args.output)
    # ELBO k-sampling for posterior estimation. The larger the better the MLE, but slower. Good range: 5~25
    # WARNING: current MLE relies on the assumption that the predicted output follows a symmetric distribution, spec. Gaussian. 
    if (args.samples):
        k_samples = args.samples
    else:
        k_samples = 20
    # this is the 'key' that is used to identity the target output (single) or the column name for the predictions
    if (args.key):
        output_key = args.key
    else:
        output_key = 'predicted'
    # user defined keyword (affix) employed to detect the columns containing our input values (latent space representation of the bathymetry images)
    if (args.latent):
        input_key = args.latent
    else:
        input_key = 'latent_'   # default expected from LGA based pipeline 
    # if necessary, the user can provide a scaling factor for the input values
    if (args.scale):
        scaling_factor = args.scale 
    else:
        scaling_factor = 1.0

    Console.info("Loading latent input [", args.input ,"]")
    np_latent, n_latents, df = PredictiveEngine.loadData(args.input, latent_name_prefix= 'latent_')

    Console.info("Loading pretrained network [", args.network ,"]")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    regressor = BayesianRegressor(n_latents, 1).to(device)                  # Single output being predicted

    if torch.cuda.is_available():
        Console.info("Using CUDA")
        regressor.load_state_dict(torch.load(args.network)) # load state from deserialized object
    else:
        Console.warn("Using CPU")
        regressor.load_state_dict(torch.load(args.network, map_location=torch.device('cpu'))) # load state from deserialized object
#    regressor.load_state_dict(torch.load(args.network)) # load state from deserialized object

    regressor.eval()    # switch to inference mode (set dropout layers)

    # DEBUG information
    # print("Model's state_dict:")
    # for param_tensor in regressor.state_dict():
    #     print(param_tensor, "\t", regressor.state_dict()[param_tensor].size())

    # Apply any pre-existing scaling factor to the input
    X_norm = np_latent  # for large latents, input to the network
    print ("X_norm [min,max]", np.amin(X_norm),"/", np.amax(X_norm))

    # Then, check the dataframe which should contain the same ordered rows from the latent space (see final step of training/validation)
    idx = 0 
    Xp_ = torch.tensor(X_norm).float()  # convert normalized intput vector into tensor

########################################################################
########################################################################

    # Network is pretrained so we start inferring
    # expected = [] # if we provide the target file (labels) then we can append a column with the expected values
    uncertainty = []
    predicted = [] # == y

    # For every input (row) we draw a K samples from the posterior
    for x in Xp_:
        predictions = []
        for n in range(k_samples):
            p = regressor(x.to(device)).item()
            predictions.append(p) #1D output, retieve single item

        p_mean = statistics.mean(predictions) * scaling_factor  # --> scaling the output of our prediction (after MC sampling)
        p_stdv = statistics.stdev(predictions) * scaling_factor # yes, stdev needs to be scaled too (under Normal distribution assumption)
        idx = idx + 1

        predicted.append(p_mean)
        uncertainty.append(p_stdv)
        Console.progress(idx, len(Xp_))

########################################################################
########################################################################
    print ("Total predicted rows: ", len(predicted))

    # # y_list = [element.item() for element in y_test.flatten()]
    # xl = np.squeeze(X_norm).tolist()

    # # predicted.len = X.len (as desired)
    # # pred_df  = pd.DataFrame ([xl, y_list, predicted, uncertainty, index_df]).transpose()
    pred_df  = df.copy()    # make a copy, then we append the results
    pred_df[output_key] = predicted    
    pred_df["uncertainty"] = uncertainty    
    new_cols = pred_df.columns.values
    new_cols[0]="uuid"  # this should be the first non-index column, expected to be the uuid

    # Let's clean the dataframe before exporting it
    # 1- Drop the latent vector (as it can be massive and the is no need for most of our maps and pred calculations)
    pred_df.drop(list(pred_df.filter(regex = input_key)), # the regex string could be updated to match any user-defined latent vector name
                axis =1,            # search in columns
                inplace = True)     # replace the current df, no need to reassign to a new variable

    print (pred_df.head())
    output_name = args.output
    Console.info("Exporting predictions to:", output_name)
    pred_df.index.names = ['index']
    pred_df.to_csv(output_name)
    Console.warn("Done!")
    return 0

if __name__ == '__main__':
    main()
