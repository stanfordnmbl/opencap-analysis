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
    session_id = kwargs['session_id']
    
    # Specify trial names in a list; use None to process all trials in a session.
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

    # Detect squat type
    eventTypes = squat.squatEvents['eventTypes']
    
    # Return squat type (none detected, more than one type, or all same type).
    squat_type = ''
    unique_types = set(eventTypes)
    if len(unique_types) < 1:
        squat_type = 'No squats detected'
        
    elif len(unique_types) > 1:
        squat_type = 'Mixed squat types detected'
        
    else:
        if eventTypes[0] == 'double_leg':
            squat_type = 'Double leg squats'
        elif eventTypes[0] == 'single_leg_l':
            squat_type = 'Single leg squats (left)'
        elif eventTypes[0] == 'single_leg_r':
            squat_type = 'Single leg squats (right)'
           
    # Pass squat type information into info_text dictionary.
    info_text = {}
    info_text['squat_type'] = {'label': 'Squat type detected',
                              'text': squat_type}
    
    # Compute metrics.
    max_trunk_lean_ground_mean, max_trunk_lean_ground_std, max_trunk_lean_ground_units = squat.compute_trunk_lean_relative_to_ground()
    max_trunk_flexion_mean, max_trunk_flexion_std, max_trunk_flexion_units = squat.compute_trunk_flexion_relative_to_ground()
    squat_depth_mean, squat_depth_std, squat_depth_units = squat.compute_squat_depth()
    
    # Store metrics dictionary.
    squat_scalars = {}
    squat_scalars['max_trunk_lean_ground'] = {'value': np.round(max_trunk_lean_ground_mean, 2),
                                              'std': np.round(max_trunk_lean_ground_std, 2),
                                              'label': 'Mean max trunk lean (deg)'}
    
    squat_scalars['max_trunk_flexion'] = {'value': np.round(max_trunk_flexion_mean, 2),
                                          'std': np.round(max_trunk_flexion_std, 2),
                                          'label': 'Mean max trunk flexion (deg)'}
    
    squat_scalars['squat_depth'] = {'value': np.round(squat_depth_mean, 2),
                                    'std': np.round(squat_depth_std, 2),
                                    'label': 'Mean squat depth (m)'}
    
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
    
    # Create results dictionary.
    results = {
        'indices': times, 
        'metrics': squat_scalars, 
        'datasets': datasets,
        'x_axis': 'time', 
        'y_axis': y_axes,
        'info_text': info_text}
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': results
    }