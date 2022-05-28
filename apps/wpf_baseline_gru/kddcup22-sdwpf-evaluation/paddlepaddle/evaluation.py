# -*-Encoding: utf-8 -*-
################################################################################
#
# Copyright (c) 2022 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
Description: Evaluate the performance
Authors: Lu,Xinjiang (luxinjiang@baidu.com)
Date:    2022/04/24
"""
import os
import sys
import time
import traceback
import tempfile
import zipfile
import numpy as np
import metrics
from test_data import TestData


class EvaluationModuleNotFoundError(ModuleNotFoundError):
    """
    Desc:
        Customize the ModuleNotFound error
    """
    def __init__(self, err_message):
        ModuleNotFoundError.__init__(self, err_message)


class EvaluationImportError(ImportError):
    """
    Desc:
        Customize the import error
    """
    def __init__(self, err_message):
        ImportError.__init__(self, err_message)


class LoaderError(Exception):
    """
    Desc:
        Customize the Exception
    """
    def __init__(self, err_message):
        Exception.__init__(self, err_message)


class Loader(object):
    """
    Desc:
        Dynamically Load a Module
    """
    def __init__(self):
        """
        """
        pass

    @staticmethod
    def load(path):
        """
        Args:
            path to the script
        """
        try:
            items = os.path.split(path)
            sys.path.append(os.path.join(*items[:-1]))
            ip_module = __import__(items[-1][:-3])
            return ip_module
        except ModuleNotFoundError as e:
            traceback.print_exc()
            raise EvaluationModuleNotFoundError(e.msg)
        except ImportError as e:
            traceback.print_exc()
            raise EvaluationImportError(e.msg)
        except Exception as error:
            traceback.print_exc()
            raise LoaderError("IMPORT ERROR: {}. Load module [path: {}]".format(error, path))


def load_test_set(settings):
    # type: (dict) -> tuple
    """
    Desc:
        Obtain the input & output sequence in the testing set
    Args:
        settings:
    Returns:
         Input files and output files
    """
    test_x_dir = settings["path_to_test_x"]
    test_x_files = os.listdir(test_x_dir)
    test_x_files = sorted(test_x_files)
    base_dir_test_y = settings["path_to_test_y"]
    test_y_files = sorted(os.listdir(base_dir_test_y))
    return test_x_files, test_y_files


def performance(settings, prediction, ground_truth, ground_truth_df):
    """
    Desc:
        Test the performance on the whole wind farm
    Args:
        settings:
        prediction:
        ground_truth:
        ground_truth_df:
    Returns:
        MAE, RMSE and Accuracy
    """
    # A convenient customized relative metric can be adopted
    # to evaluate the 'accuracy'-like performance of developed model for Wind Power forecasting problem
    wind_farm_prediction = np.sum(prediction, axis=0) / 1000
    wind_farm_ground = np.sum(ground_truth, axis=0) / 1000
    day_len = settings["day_len"]
    _rmse = metrics.rmse(wind_farm_prediction[-day_len:, -1], wind_farm_ground[-day_len:, -1])
    if _rmse <= 0:
        acc = -1
    else:
        acc = 1 - _rmse / settings["capacity"]
    overall_mae, overall_rmse = \
        metrics.regressor_detailed_scores(prediction, ground_truth, ground_truth_df, settings)
    return overall_mae, overall_rmse, acc


TAR_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../test_y'))
PRED_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../test_x'))
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../data'))
REQUIRED_ENV_VARS = [
    "pred_file",
    "checkpoints",
    "start_col",
    "framework"
]
SUPPORTED_FRAMEWORKS = [
    "base", "paddlepaddle", "pytorch", "tensorflow"
]
MAX_TIMEOUT = 3600 * 10     # 10 hours
MIN_TIME = 3                # 3 secs


def evaluate(path_to_src_dir):
    """
    Desc:
        The main entrance for the evaluation
    args:
        path_to_src_dir:
    Returns:
        A dict indicating performance
    """
    begin_time = time.time()
    left_time = MAX_TIMEOUT
    start_test_time = begin_time
    # Set up the initial environment
    path_to_prep_script = os.path.join(path_to_src_dir, "prepare.py")
    if not os.path.exists(path_to_prep_script):
        raise Exception("The preparation script, i.e. 'prepare.py', does NOT exist! ")
    prep_module = Loader.load(path_to_prep_script)

    envs = prep_module.prep_env()
    for req_key in REQUIRED_ENV_VARS:
        if req_key not in envs:
            raise Exception("Key error: '{}'. The variable {} "
                            "is missing in the prepared experimental settings! ".format(req_key, req_key))
    if "is_debug" not in envs:
        envs["is_debug"] = False
    if envs["framework"] not in SUPPORTED_FRAMEWORKS:
        raise Exception("Unsupported machine learning framework: {}. "
                        "The supported frameworks are 'base', 'paddlepaddle', 'pytorch', "
                        "and 'tensorflow'".format(envs["framework"]))

    envs["path_to_test_x"] = PRED_DIR
    envs["path_to_test_y"] = TAR_DIR
    envs["data_path"] = DATA_DIR
    envs["filename"] = "wtbdata_245days.csv"
    envs["day_len"] = 144
    envs["capacity"] = 134
    envs["output_len"] = 288
    envs["out_var"] = 1
    envs["pred_file"] = os.path.join(path_to_src_dir, envs["pred_file"])
    envs["checkpoints"] = os.path.join(path_to_src_dir, envs["checkpoints"])

    test_x_files, test_y_files = load_test_set(envs)

    if envs["is_debug"]:
        end_load_test_set_time = time.time()
        print("Load test_set (test_ys) in {} secs".format(end_load_test_set_time - start_test_time))
        start_test_time = end_load_test_set_time

    maes, rmses = [], []
    forecast_module = Loader.load(envs["pred_file"])

    start_forecast_time = start_test_time
    end_forecast_time = start_forecast_time
    test_x_dir = envs["path_to_test_x"]
    base_dir_test_y = envs["path_to_test_y"]
    for i, file in enumerate(test_x_files):
        envs["path_to_test_x"] = os.path.join(test_x_dir, file)
        prediction = forecast_module.forecast(envs)
        #
        if envs["is_debug"]:
            end_forecast_time = time.time()
            print("\nElapsed time for {}-th prediction is: "
                  "{} secs \n".format(i, end_forecast_time - start_forecast_time))
            start_forecast_time = end_forecast_time

        y_file = test_y_files[i]
        envs["path_to_test_y"] = os.path.join(base_dir_test_y, y_file)
        test_data = TestData(path_to_data=envs["path_to_test_y"], start_col=envs["start_col"])
        turbines, raw_turbines = test_data.get_all_turbines()
        test_ys = []
        for turbine in turbines:
            test_ys.append(turbine[:envs["output_len"], -envs["out_var"]:])
        # tmp_mae, tmp_rmse, tmp_acc = performance(envs, prediction, gt_y, gt_y_df)
        tmp_mae, tmp_rmse, tmp_acc = performance(envs, prediction, test_ys, raw_turbines)
        if 1024 == tmp_mae or 1024 == tmp_rmse:
            return {
                "score": -65535,
                "ML-framework": envs["framework"]
            }
        if tmp_acc <= 0:
            print('\n\tThe {}-th prediction -- '
                  'RMSE: {}, MAE: {}, and Accuracy: {}'.format(i, tmp_mae, tmp_rmse, tmp_acc))
            return {
                "score": -65535,
                "ML-framework": envs["framework"]
            }
        else:
            print('\n\tThe {}-th prediction -- '
                  'RMSE: {}, MAE: {}, Score: {}, '
                  'and Accuracy: {:.4f}%'.format(i, tmp_rmse, tmp_mae, (tmp_rmse + tmp_mae) / 2, tmp_acc * 100))
        maes.append(tmp_mae)
        rmses.append(tmp_rmse)

        cost_time = time.time() - begin_time
        left_time -= cost_time
        cnt_left_runs = len(test_y_files) - (i + 1)
        # After three runs, we will check how much time remain for your code:
        if i > 1 and left_time < MIN_TIME * (cnt_left_runs + 1):
            raise Exception("TIMEOUT! "
                            "Based on current running time analysis, it's not gonna happen that "
                            "your model can run {} predictions in {:.2f} secs! ".format(cnt_left_runs, left_time))
        begin_time = time.time()

    avg_mae, avg_rmse, total_score = -1, -1, 65535
    if len(maes) == len(test_y_files):
        avg_mae = np.array(maes).mean()
        avg_rmse = np.array(rmses).mean()
        total_score = (avg_mae + avg_rmse) / 2
        print('\n --- Final MAE: {}, RMSE: {} ---'.format(avg_mae, avg_rmse))
        print('--- Final Score --- \n\t{}'.format(total_score))

    if envs["is_debug"]:
        print("\nElapsed time for prediction is {} secs\n".format(end_forecast_time - start_test_time))
        end_test_time = time.time()
        print("\nTotal time for evaluation is {} secs\n".format(end_test_time - start_test_time))

    return {
        "score": -1. * total_score,
        "ML-framework": envs["framework"]
    }


def eval(submit_file):
    """
    Desc:
        The interface for the system call
    Args:
        submit_file:
    Returns:
        A dict indicating the score and the machine learning framework
    """
    # Check suffix of the submitted file
    if not submit_file.endswith('.zip'):
        raise Exception("Submitted file does not end with zip ！")

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Extract files
        # Handle exceptions
        with zipfile.ZipFile(submit_file) as src_f:
            src_f.extractall(path=tmp_dir)
            items = os.listdir(tmp_dir)
            if 1 == len(items):
                tmp_dir = os.path.join(tmp_dir, items[0])
                items = os.listdir(tmp_dir)
            if 0 == len(items):
                raise Exception("Zip file is empty! ")
            return evaluate(tmp_dir)
