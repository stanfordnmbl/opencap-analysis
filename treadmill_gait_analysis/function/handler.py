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

from gait_analysis import gait_analysis
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
    
    # Select how many gait cycles you'd like to analyze. Select -1 for all gait
    # cycles detected in the trial.
    n_gait_cycles = -1
    
    # Select lowpass filter frequency for kinematics data.
    filter_frequency = 6
    
    # Select scalar names to compute.
    scalar_names = {
        'gait_speed','stride_length','step_width','cadence',
        'double_support_time','step_length_symmetry'}
    # 'single_support_time', 
    
    scalar_labels = {
                 'gait_speed': "Gait speed (m/s)",
                 'stride_length':'Stride length (m)',
                 'step_width': 'Step width (cm)',
                 'cadence': 'Cadence (steps/min)',
                #  'single_support_time': 'Single support time (% gait cycle)', 
                 'double_support_time': 'Double support (% gait cycle)',
                 'step_length_symmetry': 'Step length symmetry (%, R/L)'}
    
    # %% Process data.
    # Init gait analysis and get gait events.
    legs = ['r']
    gait, gait_events = {}, {}
    for leg in legs:
        gait[leg] = gait_analysis(
            sessionDir, trial_name, leg=leg,
            lowpass_cutoff_frequency_for_coordinate_values=filter_frequency,
            n_gait_cycles=n_gait_cycles, gait_style='treadmill')
        gait_events[leg] = gait[leg].get_gait_events()
    
    # Select last leg.
    last_leg = 'r'
    
    # Compute scalars.
    gait_scalars = gait[last_leg].compute_scalars(scalar_names)
    
    gait_scalars['gait_speed']['decimal'] = 2
    gait_scalars['step_width']['decimal'] = 1
    gait_scalars['stride_length']['decimal'] = 2
    gait_scalars['cadence']['decimal'] = 1
    gait_scalars['double_support_time']['decimal'] = 1
    gait_scalars['step_length_symmetry']['decimal'] = 1
    
    # Change units
    # Default = 1
    for key in gait_scalars:
        gait_scalars[key]['multiplier'] = 1
    
    gait_scalars['step_width']['multiplier'] = 100 # cm

    # %% Info about metrics.
    gait_scalars['gait_speed']['info'] = "Gait speed is computed by dividing the displacement of the center of mass by the time it takes to move that distance. A speed larger than 1.12 m/s is considered good."
    gait_scalars['step_width']['info'] = "Step width is computed as the average distance between the ankle joint centers in the mediolateral direction during 40-60% of the stance phase. A step width between 4.3 and 7.4 times the subject's height is considered good."
    gait_scalars['stride_length']['info'] = "Stride length is computed as the distance between the calcaneus positions at the beginning and end of the gait cycle. A stride length larger than 0.45 times the subject's height is considered good."
    gait_scalars['cadence']['info'] = "Cadence is computed as the number of gait cycles (left and right) per minute. A cadence larger than 100 is considered good."
    gait_scalars['double_support_time']['info'] = "Double support time is computed as the duration when both feet are in contact with the ground. A double support time smaller than 35% of the gait cycle is considered good."
    gait_scalars['step_length_symmetry']['info'] = "Step length symmetry is computed as the ratio between the right and left step lengths. A step length symmetry between 90 and 110 is considered good."
    
    # %% Thresholds.
    metadataPath = os.path.join(sessionDir, 'sessionMetadata.yaml')
    metadata = import_metadata(metadataPath)
    subject_height = metadata['height_m']
    gait_speed_threshold = 67/60
    step_width_threshold = [4.3*subject_height, 7.4*subject_height]
    stride_length_threshold = subject_height * .45
    cadence_threshold = 100
    # single_support_time_threshold = 65
    double_support_time_threshold = 35
    step_length_symmetry_threshold = [90,110]
    thresholds = {
              'gait_speed': {'value': gait_speed_threshold, 'decimal': 2},
              'step_width': {'value': step_width_threshold, 'decimal': 1},
              'stride_length': {'value': stride_length_threshold, 'decimal': 2},
              'cadence': {'value': cadence_threshold, 'decimal': 1},
            #   'single_support_time': single_support_time_threshold,
              'double_support_time': {'value': double_support_time_threshold, 'decimal': 1},
              'step_length_symmetry': {'value': step_length_symmetry_threshold, 'decimal': 1}}
    # Whether below-threshold values should be colored in red (default) or green (reverse).
    scalar_reverse_colors = ['double_support_time']
    # Whether should be red-green-red plot
    scalar_centered = ['step_length_symmetry','step_width']
    
    # %% Return indices for visualizer and line curve plot.
    # %% Create json for deployement.
    # Indices / Times
    indices = {}
    indices['start'] = int(gait_events[last_leg]['ipsilateralIdx'][-1,0])
    indices['end'] = int(gait_events[last_leg]['ipsilateralIdx'][0,-1])
    times = {}
    times['start'] = float(gait_events[last_leg]['ipsilateralTime'][-1,0])
    times['end'] = float(gait_events[last_leg]['ipsilateralTime'][0,-1])
    
    # Metrics
    metrics_out = {}
    for scalar_name in scalar_names:
        metrics_out[scalar_name] = {}
        vertical_values = np.round(gait_scalars[scalar_name]['value'] *
                                   gait_scalars[scalar_name]['multiplier'], 
                                   gait_scalars[scalar_name]['decimal'])
        metrics_out[scalar_name]['label'] = scalar_labels[scalar_name]
        metrics_out[scalar_name]['value'] = vertical_values
        metrics_out[scalar_name]['info'] = gait_scalars[scalar_name]['info']
        if scalar_name in scalar_reverse_colors:
            # Margin zone (orange) is 10% above threshold.
            metrics_out[scalar_name]['colors'] = ["green", "yellow", "red"]
            metrics_out[scalar_name]['min_limit'] = float(np.round(thresholds[scalar_name]['value'],thresholds[scalar_name]['decimal']))
            metrics_out[scalar_name]['max_limit'] = float(np.round(1.10*thresholds[scalar_name]['value'],thresholds[scalar_name]['decimal']))
        elif scalar_name in scalar_centered:
            # Red, green, red
            metrics_out[scalar_name]['colors'] = ["red", "green", "red"]
            metrics_out[scalar_name]['min_limit'] = float(np.round(thresholds[scalar_name]['value'][0],thresholds[scalar_name]['decimal']))        
            metrics_out[scalar_name]['max_limit'] = float(np.round(thresholds[scalar_name]['value'][1],thresholds[scalar_name]['decimal'])) 
        else:
            # Margin zone (orange) is 10% below threshold.
            metrics_out[scalar_name]['colors'] = ["red", "yellow", "green"]
            metrics_out[scalar_name]['min_limit'] = float(np.round(0.90*thresholds[scalar_name]['value'],thresholds[scalar_name]['decimal']))
            metrics_out[scalar_name]['max_limit'] = float(np.round(thresholds[scalar_name]['value'],thresholds[scalar_name]['decimal']))
            
    # Datasets
    colNames = gait[last_leg].coordinateValues.columns
    data = gait[last_leg].coordinateValues.to_numpy()
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
        'metrics': metrics_out, 
        'datasets': datasets,
        'x_axis': 'time', 
        'y_axis': y_axes}
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': results
    }