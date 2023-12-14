from openai import OpenAI
import os
import json
import simplejson as json
import boto3
from LEMChatUtilities import get_sortk_timestamp

client = boto3.resource('dynamodb', region_name='us-east-1')
table = client.Table('UserData')

def validate_response(response):
  uds_text = response['choices'][0]["message"]['content']
  uds_dict = {}
  try:
    uds_dict = json.loads(uds_text)

  except Exception as e:
    return [False, "Invalid JSON string"]
  
  # Check if the uds_dict adheres to the UDS requirements
  if 'basic_info' in uds_dict and 'traits' in uds_dict and 'skills' in uds_dict and 'factual_history' in uds_dict and 'summary' in uds_dict:
    if isinstance(uds_dict['basic_info'], dict) and isinstance(uds_dict['traits'], list) and isinstance(uds_dict['skills'], list) and isinstance(uds_dict['factual_history'], list) and isinstance(uds_dict['summary'], str):
      if len(uds_dict['traits']) <= 15 and len(uds_dict['skills']) <= 15 and len(uds_dict['factual_history']) <= 15:

        # Check if each individual item in basic_info has a value which is only a string
        for key, value in uds_dict['basic_info'].items():
          if not isinstance(value, str):
            return [False, "Non-string value in basic_info"]
          
        # Check if traits, skills, and factual_history adhere to their respective specs
        for trait in uds_dict['traits']:
          if not (isinstance(trait, list) and len(trait) == 3 and isinstance(trait[0], str) and isinstance(trait[1], int) and isinstance(trait[2], str)):
            return [False, "Invalid trait entry"]
          
          if not (0 <= trait[1] <= 100):
            return [False, "Trait strength percentage out of range"]
          
        for skill in uds_dict['skills']:
          if not (isinstance(skill, list) and len(skill) == 3 and isinstance(skill[0], str) and isinstance(skill[1], int) and isinstance(skill[2], str)):
            return [False, "Invalid skill entry"]
          
          if not (0 <= trait[1] <= 100):
            return [False, "Skill strength percentage out of range"]
          
        for history in uds_dict['factual_history']:
          if not (isinstance(history, str)):
            return [False, "Invalid factual_history entry"]
          
        return [True, uds_dict]
      else:
        return [False, "Too many entries in traits, skills, or factual_history"]
    else:
      return [False, "Invalid data types in UDS"]
  else:
    return [False, "Missing required fields in UDS"]


def analyze(event, context):
  # Get the chat history from step function input
  api_key = str(event["api_key"])
  uid = str(event["uid"])
  iid = str(event["iid"])
  batch = tuple(event["batch"])

  message_history_partitionk = api_key + uid + iid + 'messages'

  message_history = []

  # Initial query
  message_history_response = table.query(
    KeyConditionExpression=boto3.dynamodb.conditions.Key('partitionk').eq(message_history_partitionk),
    ScanIndexForward=False,
    Limit=(int(batch[0]) + 1)
  )

  # Adding initial items
  message_history.extend(message_history_response['Items'])

  # Pagination handling if needed
  while 'LastEvaluatedKey' in message_history_response:
    message_history_response = table.query(
      KeyConditionExpression=boto3.dynamodb.conditions.Key('partitionk').eq(message_history_partitionk),
      ScanIndexForward=False,
      ExclusiveStartKey=message_history_response['LastEvaluatedKey'],
      Limit=(int(batch[0]) + 1) - len(message_history)
    )
    message_history.extend(message_history_response['Items'])

  # Remove any elements beyond the batch[1]th element in the array message_history
  message_history = message_history[batch[1]:]

  # Get API key from environment
  openai_key = os.environ['openai_key']
  openai_client = OpenAI(api_key=openai_key)
  
  # Specify the AI model
  model = "gpt-4-1106-preview"
  
  # create the UDS parition key
  context_partition_key = api_key + uid + iid + 'context'
    
  # get the lastest context
  latest_UDS_response = table.query(
    KeyConditionExpression=boto3.dynamodb.conditions.Key('partitionk').eq(context_partition_key),
    ScanIndexForward=False,  # sorts the data in descending order based on the sort key
    Limit=1
  )

  latest_UDS = latest_UDS_response['Items'][0]['uds'] if latest_UDS_response['Items'] else None

  # Check if latest_UDS exists, if not create a blank one
  if not latest_UDS:
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

  for message in messages:
      print(message, "\n")
  
  response = openai_client.chat.completions.create(model=model,
  messages=messages,
  stop=None,
  max_tokens=2500)


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
    max_tokens=2500)

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
  uds_put_response = table.put_item(
    Item={
      'partitionk': context_partition_key,
      'sortk': get_sortk_timestamp(),
      'uds': modified_UDS
    }
  )

  if uds_put_response['ResponseMetadata']['HTTPStatusCode'] == 200:
    return {
      'statusCode': 200,
      'body': json.dumps('Successfully updated UDS.')
    }


def batch_analyze(batches_to_analyze):
  '''
  Input: a batch of messages to be analyzed in the form
  i.e. [(7,4), (3,2)] with both start and end inclusive, meaning
  'analyze message 7 to 4, then in the next batch 4 to 2.
  '''
  for event in batches_to_analyze:
    analyze(event, None)