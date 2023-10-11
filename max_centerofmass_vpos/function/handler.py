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

from utilsKinematics import kinematics
from utils import get_trial_id, download_trial


def handler(event, context):
    """ AWS Lambda function handler. This function calculates
        maximal center of mass vertical position for specified session and trials.

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
    sessionDir = os.path.join("/tmp/Data", session_id)

    # %% Download data.
    trial_id = get_trial_id(session_id,specific_trial_names[0])
    trial_name = download_trial(trial_id,sessionDir,session_id=session_id) 

    # %% Process data.
    # Create object from class kinematics.
    kinematics_obj = kinematics(
        sessionDir, trial_name, lowpass_cutoff_frequency_for_coordinate_values=10)    
    # Get center of mass values.
    center_of_mass = kinematics_obj.get_center_of_mass_values(lowpass_cutoff_frequency=10)
    # Get maximal center of mass vertical position.
    max_center_of_mass = np.round(np.max(center_of_mass['y']), 2)
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': {
            'message': f'Maximal center of mass vertical position: {max_center_of_mass} m'
        }
    }
