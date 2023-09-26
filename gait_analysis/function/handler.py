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
from utils import get_trial_id, download_trial


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
    sessionDir = os.path.join("/tmp/Data", session_id)

    # %% Download data.
    trial_id = get_trial_id(session_id,specific_trial_names[0])
    trial_name = download_trial(trial_id,sessionDir,session_id=session_id) 

    # Select how many gait cycles you'd like to analyze. Select -1 for all gait
    # cycles detected in the trial.
    n_gait_cycles = 1

    # Select lowpass filter frequency for kinematics data.
    filter_frequency = 6

    # Select scalar names to compute.
    scalar_names = {'gait_speed','stride_length','step_width','cadence',
                    'single_support_time','double_support_time'}

    # %% Process data.
    # Init gait analysis and get gait events.
    legs = ['r','l']
    gait, gait_events, ipsilateral = {}, {}, {}
    for leg in legs:
        gait[leg] = gait_analysis(
            sessionDir, trial_name, leg=leg,
            lowpass_cutoff_frequency_for_coordinate_values=filter_frequency,
            n_gait_cycles=n_gait_cycles)
        gait_events[leg] = gait[leg].get_gait_events()
        ipsilateral[leg] = gait_events[leg]['ipsilateralTime'][0,-1]

    # Select last leg.
    last_leg = 'r' if ipsilateral['r'] > ipsilateral['l'] else 'l'

    # Compute scalars.
    gait_scalars = gait[last_leg].compute_scalars(scalar_names)

    # %% Return indices for visualizer and line curve plot.
    indices = {}
    indices['start'] = int(gait_events[last_leg]['ipsilateralIdx'][0,0])
    indices['end'] = int(gait_events[last_leg]['ipsilateralIdx'][0,-1])

    # The visualizer in step 5 loads the file tagged `visualizerTransforms-json`.
    # https://github.com/stanfordnmbl/opencap-viewer/blob/main/src/components/pages/Step5.vue#L973 
    # For the gait dashboard, we should use the same file but play it from
    # index indices['start'] to index indices['end'].

    # The line curve chart loads the file tagged `ik_results`.
    # https://github.com/stanfordnmbl/opencap-viewer/blob/main/src/components/pages/Dashboard.vue#L244
    # https://github.com/stanfordnmbl/opencap-viewer/blob/main/src/components/pages/Dashboard.vue#L433
    # For the gait dashboard, we should use the same file but play it from
    # index indices['start'] to index indices['end'].

    # Both files have the same number of frames. We want to display a vertical bar
    # on the line curve chart that is temporarily aligned with the visualizer. Eg,
    # when the visualizer displays frame #50, the vertical bar in the line curve
    # chart should be at frame #50. The goal is to allow users to visualy compare
    # what is happening in the visualizer (skeleton) with what is happening in the
    # data (line curves). For example, when the left foot touches the ground, the
    # angle of the knee is 10 degrees.

    # %% Return gait metrics for scalar chart.
    # Instructions for the frontend will come later.
    gait_metrics = {}
    for scalar_name in scalar_names:
        gait_metrics[scalar_name] = np.round(gait_scalars[scalar_name], 2)

    # %% Dump data into json file.
    # Create results dictionnary with indices and gait_metrics.
    results = {'indices': indices, 'gait_metrics': gait_metrics}    

    # TODO: push results dict to `Results` instance of the trial.
    # with open('results.json', 'w') as outfile:
    #     json.dump(results, outfile)

    # Temporary placeholder.
    gait_speed = gait_metrics['gait_speed']
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': {
            'message': f'Gait speed - {gait_speed} m/s',
            'results': results,
        }
    }