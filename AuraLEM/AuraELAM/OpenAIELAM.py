from openai import OpenAI
import os
import simplejson as json
import boto3
from DynamoDBUtilities import *
from AuraELAM.UDSUtilities import validate_response

client = boto3.resource('dynamodb', region_name='us-east-1')
table = client.Table('UserData')

# lambda_client = boto3.client('lambda')
from LEMTestUtilities import FakeLambdaClient
lambda_client = FakeLambdaClient()

def analyze_sync(event, context):
  # Get the chat history from step function input
  api_key = str(event["api_key"])
  uid = str(event["uid"])
  iid = str(event["iid"])
  elam_response_mtl = int(event["elam_response_mtl"])
  message_history = event["analysis_window"]

  # Get API key from environment
  # openai_key = os.environ['openai_key']
  openai_key = "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"
  openai_client = OpenAI(api_key=openai_key)
  
  # Specify the AI model
  model = "gpt-4-1106-preview"
  
  # create the UDS parition key
  UDS_partition_key = api_key + uid + iid + 'UDS'
  latest_UDS = full_limit_query(UDS_partition_key, False)

  # Check if latest_UDS exists, if not create a blank one
  if latest_UDS == []:
    latest_UDS = {
      'basic_info': {
        'name': '',
        'current_location': '',
        'occupation': '',
        'sex': ''
      },
      'traits': [],
      'skills': [],
      'factual_history': [],
      'summary': ''
    }

  else:
    latest_UDS = latest_UDS[0]['uds']

  system_message = f"""
    You are being used via API in an LLM chat app which can 'learn' its own users through its chats with them. It works through AI agents: you are such an agent, located in our backend. Your output will never be directly seen by the user but rather you are a reasoning module whose purpose is to initialize & modify the user understanding data structure (UDS) based off chat history.
    
    UDS: a data-dense, JSON, plaintext format for storing information about personalities. Spec below:
    {{
    'basic_info': {{
    'name': 'Jesus Lares',
    'current_location': 'San Francisco',
    'occupation': 'Startup founder',
    'sex': 'male'
    }}
    'traits': [
    ['trait name', (int) % strength of trait from 0-100, 'few words on reasoning & evidence.'],
    ],
    'skills': [
    ['skill name', (int) % strength of trait from 0-100, 'few words on reasoning & evidence.'],
    ],
    'factual_history' : [
    'history event name'
    ]
    'summary': 'a 1-2 paragraph (depending on how much information you have) textual summary encompassing a wholistic view of the users' personality, history, and achievements.'
    }}

    --- Further explanation on UDS ---
    We want the UDS to be short and precise so that only the most prominent & revelaing user info is presented. Unless you think an entry allows you to infer something revealing, you need not add it. For the traits, skills, and factual_history arrays, limit it to the 10 most revealing entries each (max) and remove, combine, or modify them however you feel is best to capture more information about the user.

    Examples:
    traits entry: ['bold', 80, "loves risk, exemplified by his decision to found a startup, rock climb, and go on month-long backpacking trips."]
    skills entry: ['physics', 60, "undergraduate physics degree from MIT."]
    factual_history entry: "did his undergraduate at MIT completing physics and computer science degrees."

    --- Final notes ---
    You are a backend AI. Your entire purpose is to create or modify a UDS. You will be given a (potentially empty) UDS at the end of this system message. You must ONLY respond with a modified UDS following the key name spec above and nothing more. This is extremely important, as any extraneous input will cause the system to crash.

    --- Current User UDS Below ---
    {json.dumps(latest_UDS)}
  """

  user_message = "What can you infer about the user from the following chat history? Again please respond ONLY with a modified UDS: \n\n"
  
  # note that chat history goes from most recent to oldest, so must be reversed
  i = len(message_history) - 1
  while i >= 0:
    message = message_history[i]
    user_message += f"{message['role']}: {message['content']}\n\n"

    i -= 1

  messages = [
    {
      "role": "system",
      "content": system_message
    },
    {
      "role": "user",
      "content": user_message
    }
  ]
  
  response = openai_client.chat.completions.create(model=model,
  messages=messages,
  stop=None,
  response_format={"type": "json_object"},
  max_tokens=elam_response_mtl)

  validated, modified_UDS = validate_response(response)

  # If validation fails try again once more with new message
  if not validated:
    print("VALIDATION FAILED. NEEDED RETRY.")

    messages.append({
      "role": "assistant",
      "content": response
    })

    messages.append({
      "role": "user",
      "content": "This response is not a valid UDS, incorrect syntax. Please try one more time. It is EXTREMELY IMPORTANT that you get the syntax correct as per the system message."
    })
      
    response = openai_client.chat.completions.create(model=model,
    messages=messages,
    stop=None,
    response_format={"type": "json_object"},
    max_tokens=elam_response_mtl)

    validated, modified_UDS = validate_response(response)
    
  # If validation fails again, return error
  if not validated:
    return {
      'statusCode': 500,
      'body': json.dumps('Failed to generate UDS.')
    }

  # at this point, after a max of one retry, it is necessarily valid. Else would have failed.

  # create the new UDS sort key
  print("modified UDS: ", modified_UDS, "\n\n")

  item={
    'partitionk': UDS_partition_key,
    'sortk': get_sortk_timestamp(),
    'uds': modified_UDS
  }

  uds_put_response = put_item_ddb(item)

  if uds_put_response['statusCode'] == 200:
    return {
      'statusCode': 200,
      'body': json.dumps('Successfully updated UDS.')
    }
  
  else:
    return {
      'statusCode': 500,
      'body': json.dumps('Failed to update UDS.')
    }


def analyze_async(payload):
    # Define the parameters for invoking the Lambda
    params = {
        'FunctionName': 'other-lambda-function-name',  # Replace with the target Lambda function name
        'InvocationType': 'Event',  # Use 'Event' for asynchronous, 'RequestResponse' for synchronous
        'Payload': json.dumps(payload)  # Your payload here
    }

    # Invoke the Lambda function
    response = lambda_client.invoke(**params)
    return response


def analyze(analysis_input):
  '''
  @param analysis_input: 
    analysis_input = {
      'analyze': True, # whether to analyze the batch
      'synchronous': True, # whether to run the analysis synchronously or asynchronously
      'limits': [7, 2] # the limits of the batch. From 7th message out (limit=7) to 2nd message (1st if counting by 0 index)
      'api_key': api_key_for_authorizer,
      'uid': user_id,
      'iid': intelligence_id,
      'elam_response_mtl': 1393, # the max length of the response (in tokens of elam_token_type)
    }
  '''
  analysis_response = {}

  if analysis_input['analyze']:
    if analysis_input['synchronous']:
      # run the analysis synchronously
      payload = analysis_input
      analysis_response = analyze_sync(payload, {})

    else:
      # run the analysis asynchronously
      payload = analysis_input
      analysis_response = analyze_async(payload) # would be a lambda call

  else:
    analysis_response = {
      'statusCode': 200,
      'body': json.dumps('Analysis not requested.')
    }
  
  return analysis_response
