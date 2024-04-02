'''
    ---------------------------------------------------------------------------
    OpenCap processing: example.py
    ---------------------------------------------------------------------------

    Copyright 2022 Stanford University and the Authors
    
    Author(s): Antoine Falisse, Scott Uhlrich
    
    Licensed under the Apache License, Version 2.0 (the "License"); you may not
    use this file except in compliance with the License. You may obtain a copy
    of the License at http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''
import json
import os
import numpy as np

from squat_analysis import squat_analysis
from utils import get_trial_id, download_trial, import_metadata


def handler(event, context):
    """ AWS Lambda function handler. This function performs a gait analysis.

        To invoke the function do POST request on the following url
        http://localhost:8080/2015-03-31/functions/function/invocations
    """
    # temporary placeholder
    kwargs = json.loads(event['body'])

    for field in ('session_id', 'specific_trial_names'):
        if field not in kwargs:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': {'error': f'{field} field is required.'}
            }

    # %% User inputs.
    # Specify session id; see end of url in app.opencap.ai/session/<session_id>.
    # session_id = "8e430ad2-989c-4354-a6f1-7eb21fa0a16e"
    session_id = kwargs['session_id']
    
    # Specify trial names in a list; use None to process all trials in a session.
    # specific_trial_names = ['walk']
    specific_trial_names = kwargs['specific_trial_names']
    
    # Specify where to download the data.
    sessionDir = os.path.join("/tmp/Data", session_id)
    
    # %% Download data.
    trial_id = get_trial_id(session_id,specific_trial_names[0])
    trial_name = download_trial(trial_id,sessionDir,session_id=session_id) 
    
    # Select how many repetitions you'd like to analyze. Select -1 for all
    # repetitions detected in the trial.
    n_repetitions = -1
    
    # Select lowpass filter frequency for kinematics data.
    filter_frequency = 4
    
    # %% Process data.
    # Init squat analysis.
    squat = squat_analysis(
        sessionDir, trial_name,
        lowpass_cutoff_frequency_for_coordinate_values=filter_frequency,
        n_repetitions=n_repetitions)
    squat_events = squat.get_squat_events()
    
    max_knee_flexion_angle_r_mean, max_knee_flexion_angle_r_std, _ = squat.compute_peak_angle('knee_angle_r')
    max_knee_flexion_angle_l_mean, max_knee_flexion_angle_l_std, _ = squat.compute_peak_angle('knee_angle_l')
    max_knee_flexion_angle_mean_mean = np.round(np.mean(np.array([max_knee_flexion_angle_r_mean, max_knee_flexion_angle_l_mean])))
    max_knee_flexion_angle_mean_std = np.round(np.mean(np.array([max_knee_flexion_angle_r_std, max_knee_flexion_angle_l_std])))

    max_hip_flexion_angle_r_mean, max_hip_flexion_angle_r_std, _ = squat.compute_peak_angle('hip_flexion_r')
    max_hip_flexion_angle_l_mean, max_hip_flexion_angle_l_std, _ = squat.compute_peak_angle('hip_flexion_l')
    max_hip_flexion_angle_mean_mean = np.round(np.mean(np.array([max_hip_flexion_angle_r_mean, max_hip_flexion_angle_l_mean])))
    max_hip_flexion_angle_mean_std = np.round(np.mean(np.array([max_hip_flexion_angle_r_std, max_hip_flexion_angle_l_std])))

    max_hip_adduction_angle_r_mean, max_hip_adduction_angle_r_std, _ = squat.compute_peak_angle('hip_adduction_r')
    max_hip_adduction_angle_l_mean, max_hip_adduction_angle_l_std, _ = squat.compute_peak_angle('hip_adduction_l')
    max_hip_adduction_angle_mean_mean = np.round(np.mean(np.array([max_hip_adduction_angle_r_mean, max_hip_adduction_angle_l_mean])))
    max_hip_adduction_angle_mean_std = np.round(np.mean(np.array([max_hip_adduction_angle_r_std, max_hip_adduction_angle_l_std])))

    rom_knee_flexion_angle_r_mean, rom_knee_flexion_angle_r_std, _ = squat.compute_range_of_motion('knee_angle_r')
    rom_knee_flexion_angle_l_mean, rom_knee_flexion_angle_l_std, _ = squat.compute_range_of_motion('knee_angle_l')
    rom_knee_flexion_angle_mean_mean = np.round(np.mean(np.array([rom_knee_flexion_angle_r_mean, rom_knee_flexion_angle_l_mean])))
    rom_knee_flexion_angle_mean_std = np.round(np.mean(np.array([rom_knee_flexion_angle_r_std, rom_knee_flexion_angle_l_std])))
    
    squat_scalars = {}
    squat_scalars['peak_knee_flexion_angle_mean'] = {'value': max_knee_flexion_angle_mean_mean}
    squat_scalars['peak_knee_flexion_angle_mean']['label'] = 'Mean peak knee flexion angle (deg)'
    squat_scalars['peak_knee_flexion_angle_mean']['colors'] = ["red", "yellow", "green"]
    peak_knee_flexion_angle_threshold = 100
    squat_scalars['peak_knee_flexion_angle_mean']['min_limit'] = float(np.round(0.90*peak_knee_flexion_angle_threshold))
    squat_scalars['peak_knee_flexion_angle_mean']['max_limit'] = float(peak_knee_flexion_angle_threshold)
    
    squat_scalars['peak_knee_flexion_angle_std'] = {'value': max_knee_flexion_angle_mean_std}
    squat_scalars['peak_knee_flexion_angle_std']['label'] = 'Std peak knee flexion angle (deg)'
    squat_scalars['peak_knee_flexion_angle_std']['colors'] = ["green", "yellow", "red"]
    std_threshold_min = 2
    std_threshold_max = 4
    squat_scalars['peak_knee_flexion_angle_std']['min_limit'] = float(std_threshold_min)
    squat_scalars['peak_knee_flexion_angle_std']['max_limit'] = float(std_threshold_max)
    
    squat_scalars['peak_hip_flexion_angle_mean'] = {'value': max_hip_flexion_angle_mean_mean}
    squat_scalars['peak_hip_flexion_angle_mean']['label'] = 'Mean peak hip flexion angle (deg)'
    squat_scalars['peak_hip_flexion_angle_mean']['colors'] = ["red", "yellow", "green"]
    peak_hip_flexion_angle_threshold = 100
    squat_scalars['peak_hip_flexion_angle_mean']['min_limit'] = float(np.round(0.90*peak_hip_flexion_angle_threshold))
    squat_scalars['peak_hip_flexion_angle_mean']['max_limit'] = float(peak_hip_flexion_angle_threshold)
    
    squat_scalars['peak_hip_flexion_angle_std'] = {'value': max_hip_flexion_angle_mean_std}
    squat_scalars['peak_hip_flexion_angle_std']['label'] = 'Std peak hip flexion angle (deg)'
    squat_scalars['peak_hip_flexion_angle_std']['colors'] = ["green", "yellow", "red"]
    squat_scalars['peak_hip_flexion_angle_std']['min_limit'] = float(std_threshold_min)
    squat_scalars['peak_hip_flexion_angle_std']['max_limit'] = float(std_threshold_max)
    
    squat_scalars['peak_knee_adduction_angle_mean'] = {'value': max_hip_adduction_angle_mean_mean}
    squat_scalars['peak_knee_adduction_angle_mean']['label'] = 'Mean peak knee adduction angle (deg)'
    squat_scalars['peak_knee_adduction_angle_mean']['colors'] = ["red", "green", "red"]
    knee_adduction_angle_threshold = 5
    squat_scalars['peak_knee_adduction_angle_mean']['min_limit'] = float(-knee_adduction_angle_threshold)
    squat_scalars['peak_knee_adduction_angle_mean']['max_limit'] = float(knee_adduction_angle_threshold)
    
    squat_scalars['peak_knee_adduction_angle_std'] = {'value': max_hip_adduction_angle_mean_std}
    squat_scalars['peak_knee_adduction_angle_std']['label'] = 'Std peak knee adduction angle (deg)'
    squat_scalars['peak_knee_adduction_angle_std']['colors'] = ["green", "yellow", "red"]
    squat_scalars['peak_knee_adduction_angle_std']['min_limit'] = float(std_threshold_min)
    squat_scalars['peak_knee_adduction_angle_std']['max_limit'] = float(std_threshold_max)
    
    squat_scalars['rom_knee_flexion_angle_mean'] = {'value': rom_knee_flexion_angle_mean_mean}
    squat_scalars['rom_knee_flexion_angle_mean']['label'] = 'Mean range of motion knee flexion angle (deg)'
    squat_scalars['rom_knee_flexion_angle_mean']['colors'] = ["red", "yellow", "green"]
    rom_knee_flexion_angle_threshold_min = 85
    rom_knee_flexion_angle_threshold_max = 115
    squat_scalars['rom_knee_flexion_angle_mean']['min_limit'] = float(rom_knee_flexion_angle_threshold_min)
    squat_scalars['rom_knee_flexion_angle_mean']['max_limit'] = float(rom_knee_flexion_angle_threshold_max)
    
    squat_scalars['rom_knee_flexion_angle_std'] = {'value': rom_knee_flexion_angle_mean_std}
    squat_scalars['rom_knee_flexion_angle_std']['label'] = 'Std range of motion knee flexion angle (deg)'
    squat_scalars['rom_knee_flexion_angle_std']['colors'] = ["green", "yellow", "red"]
    squat_scalars['rom_knee_flexion_angle_std']['min_limit'] = float(std_threshold_min)
    squat_scalars['rom_knee_flexion_angle_std']['max_limit'] = float(std_threshold_max)
    
    # %% Return indices for visualizer and line curve plot.
    # %% Create json for deployement.
    # Indices / Times
    indices = {}
    indices['start'] = int(squat_events['eventIdxs'][0][0])
    indices['end'] = int(squat_events['eventIdxs'][-1][-1])
    times = {}
    times['start'] = float(squat_events['eventTimes'][0][0])
    times['end'] = float(squat_events['eventTimes'][-1][-1])
                
    # Datasets
    colNames = squat.coordinateValues.columns
    data = squat.coordinateValues.to_numpy()
    coordValues = data[indices['start']:indices['end']+1]
    datasets = []
    for i in range(coordValues.shape[0]):
        datasets.append({})
        for j in range(coordValues.shape[1]):
            # Exclude knee_angle_r_beta and knee_angle_l_beta
            if 'beta' in colNames[j] or 'mtp' in colNames[j]:
                continue
            datasets[i][colNames[j]] = coordValues[i,j]
            
    # Available options for line curve chart.
    y_axes = list(colNames)
    y_axes.remove('time')
    y_axes.remove('knee_angle_r_beta')
    y_axes.remove('knee_angle_l_beta')
    y_axes.remove('mtp_angle_r')
    y_axes.remove('mtp_angle_l')
    
    # Create results dictionnary.
    results = {
        'indices': times, 
        'metrics': squat_scalars, 
        'datasets': datasets,
        'x_axis': 'time', 
        'y_axis': y_axes}
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': results
    }