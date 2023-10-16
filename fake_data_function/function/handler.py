import json
import os


def handler(event, context):
    """ AWS Lambda function handler. This function returns the prepared
    date from the JSON file. Useful for debug purposes for analysis dashboard.

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

    # %% Read the data.
    body = {}
    with open(f'/datasets/{session_id}_{specific_trial_names[0]}.json', 'r') as f:
        body = json.load(f)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': body
    }