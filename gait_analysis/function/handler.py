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
from utils import download_kinematics


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
    # session_id = "bd61b3a6-813d-411c-8067-92315b3d4e0d"
    session_id = kwargs['session_id']

    # Specify trial names in a list; use None to process all trials in a session.
    # specific_trial_names = ['test']
    specific_trial_names = kwargs['specific_trial_names']

    # Specify where to download the data.
    data_folder = os.path.join("/tmp/Data", session_id)

    # %% Download data.
    trial_names, _ = download_kinematics(session_id, folder=data_folder, trialNames=specific_trial_names)

    # Select how many gait cycles you'd like to analyze. Select -1 for all gait
    # cycles detected in the trial.
    n_gait_cycles = -1 

    # Select lowpass filter frequency for kinematics data.
    filter_frequency = 6

    # Select scalar names to compute.
    scalar_names = {'gait_speed','stride_length','step_width','cadence',
                    'single_support_time','double_support_time'}

    # %% Process data.
    gaitResults = {}
    for trial_name in trial_names:
        gait_r = gait_analysis(
            data_folder, trial_name, leg='r',
            lowpass_cutoff_frequency_for_coordinate_values=filter_frequency,
            n_gait_cycles=n_gait_cycles)
        gait_l = gait_analysis(
            data_folder, trial_name, leg='l',
            lowpass_cutoff_frequency_for_coordinate_values=filter_frequency,
            n_gait_cycles=n_gait_cycles)
        
        gaitResults[trial_name] = {}
        gaitResults[trial_name]['scalars_r'] = gait_r.compute_scalars(scalar_names)
        # gaitResults[trial_name]['curves_r'] = gait_r.get_coordinates_normalized_time()
        gaitResults[trial_name]['scalars_l'] = gait_l.compute_scalars(scalar_names)
        # gaitResults[trial_name]['curves_l'] = gait_l.get_coordinates_normalized_time()
    
    right_gait_speed = np.round(gaitResults[trial_name]['scalars_r']['gait_speed'], 2)
    right_stride_length = np.round(gaitResults[trial_name]['scalars_r']['stride_length'], 2)
    right_step_width = np.round(gaitResults[trial_name]['scalars_r']['step_width'], 2)
    right_cadence = np.round(gaitResults[trial_name]['scalars_r']['cadence'], 2)
    right_single_support_time = np.round(gaitResults[trial_name]['scalars_r']['single_support_time'], 2)
    right_double_support_time = np.round(gaitResults[trial_name]['scalars_r']['double_support_time'], 2)
    
    left_gait_speed = np.round(gaitResults[trial_name]['scalars_l']['gait_speed'], 2)
    left_stride_length = np.round(gaitResults[trial_name]['scalars_l']['stride_length'], 2)
    left_step_width = np.round(gaitResults[trial_name]['scalars_l']['step_width'], 2)
    left_cadence = np.round(gaitResults[trial_name]['scalars_l']['cadence'], 2)
    left_single_support_time = np.round(gaitResults[trial_name]['scalars_l']['single_support_time'], 2)
    left_double_support_time = np.round(gaitResults[trial_name]['scalars_l']['double_support_time'], 2)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': {
            'message': f'Gait speed - Right: {right_gait_speed} m/s'
            # 'message': f'''
            # Gait speed - Right: {right_gait_speed} m/s, Left: {left_gait_speed} m/s \n 
            # Stride length - Right: {right_stride_length} m, Left: {left_stride_length} m \n
            # Step width - Right: {right_step_width} m, Left: {left_step_width} m \n
            # Cadence - Right: {right_cadence} step/s, Left: {left_cadence} step/s \n
            # Single support time - Right: {right_single_support_time} s, Left: {left_single_support_time} s \n
            # Double support time - Right: {right_double_support_time} s, Left: {left_double_support_time} s \n
            # '''
        }
    }