'''
Utilities for the LEMChat function
'''

import simplejson as json
from datetime import datetime
import pytz
import boto3


'''
Returns a timestamp for use as sort key
'''
def get_sortk_timestamp():
  # get the timestamp for sork key purposes
  utc_now = datetime.now(pytz.utc)
  timestamp = utc_now.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
  sortk_t = timestamp
  return sortk_t


'''
Sets an idempotency lock for the data between uid & iid
'''
def check_then_activate_idempotency_lock(idempotency_key, table):
   # Idempotency check - check if the process is already active for this user and intelligence
  response = table.query(
    KeyConditionExpression=boto3.dynamodb.conditions.Key('partitionk').eq(idempotency_key),
    Limit=1
  )

  # if the lock is already active
  if 'Item' in response and response['Item'].get('active', False):
    return (True, {
      'statusCode': 400,
      'body': json.dumps('Process already running for this user, please wait for it to return completed.')
    })
  
  # Set the active flag for this operation
  table.put_item(Item={'partitionk': idempotency_key, 'sortk': get_sortk_timestamp(), 'active': True})
  return (False, None)


'''
Checks that the user message is valid
'''
def validate_user_message(um, um_mtl):
  # assert the user message is of adequate length
  if um["token_length"] > um_mtl:
    return (True, {
      'statusCode': 400,
      'body': json.dumps(f'User message exceed max token legnth. Expects a maximum of {um_mtl} tokens, got {um_tl}.')
    })

  else:
    return (False, None)


'''
Returns the communication meta information, or a blank template message if none exists
'''
def get_context_window_meta(api_key, uid, iid, table, token_type, boto3):
  # get the context window meta information
  context_window_meta_partitionk = api_key + uid + iid + 'ch_context_window_meta'
  context_window_meta_response = table.query(
    KeyConditionExpression=boto3.dynamodb.conditions.Key('partitionk').eq(context_window_meta_partitionk),
    Limit=1
  )

  context_window_meta = {}
  if not context_window_meta_response['Items']:       
    # if there is no item, this is the first time the user is chatting with this intelligence
    context_window_meta = {
      'partitionk': context_window_meta_partitionk,
      'sortk': get_sortk_timestamp(),
      'aw_token_length': 0,
      'aw_token_type': token_type,
      'aw_message_count': 0,
      'ch_token_length': 0,
      'ch_token_type': token_type,
      'ch_message_count': 0,
    }

  else:
    # else set it to the latest context window meta object
    context_window_meta = context_window_meta_response['Items'][0]

  context_window_meta = json.loads(json.dumps(context_window_meta))
  return context_window_meta


def get_analysis_and_chat_windows(context_window_meta, api_key, uid, iid, table, boto3):
  analysis_window = []
  chat_history = []

  if(max(context_window_meta['aw_message_count'], context_window_meta['ch_message_count']) > 0):
    # get the current chat history and analysis window
    message_history_partitionk = api_key + uid + iid + "messages"
    message_history = []

    # Initial query
    message_history_response = table.query(
      KeyConditionExpression=boto3.dynamodb.conditions.Key('partitionk').eq(message_history_partitionk),
      ScanIndexForward=False,
      Limit=max(context_window_meta['aw_message_count'], context_window_meta['ch_message_count'])
    )

    # Adding initial items
    message_history.extend(message_history_response['Items'])
    print(len(message_history))

    # Pagination handling
    while 'LastEvaluatedKey' in message_history_response:
      message_history_response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('partitionk').eq(message_history_partitionk),
        ScanIndexForward=False,
        ExclusiveStartKey=message_history_response['LastEvaluatedKey'],
        Limit=max(context_window_meta['aw_message_count'], context_window_meta['ch_message_count']) - len(message_history)
      )
      message_history.extend(message_history_response['Items'])

    # get the current analysis window
    analysis_window = message_history[:context_window_meta['aw_message_count']]

    # get the current chat history
    chat_history = message_history[:context_window_meta['ch_message_count']]

  else:
    # if there is no message history, create an empty analysis window and chat history manually since there may be no history entry
    analysis_window = []
    chat_history = []
  
  return (analysis_window, chat_history)


def validate_windows_and_meta(context_window_meta, analysis_window, chat_history, token_type, tokenizer, ch_mtl):
  token_type_updated = False

  # if either the aw or ch token type is different from the current token type, re-tokenize the analysis window and chat history
  if context_window_meta['aw_token_type'] != token_type:
    analysis_window, context_window_meta['aw_token_length'] = tokenizer.update_token_context(analysis_window)
    context_window_meta['aw_token_type'] = token_type
    token_type_updated = True

  if context_window_meta['ch_token_type'] != token_type:
    chat_history, context_window_meta['ch_token_length'] = tokenizer.update_token_context(chat_history)
    context_window_meta['ch_token_type'] = token_type
    token_type_updated = True

  # if ch_mtl changed & chat history is now too large, remove necessary messages
  while context_window_meta['ch_token_length'] > ch_mtl:
    current_chm_tl = chat_history[-1]['token_length']
    context_window_meta['ch_token_length'] -= current_chm_tl
    context_window_meta['ch_message_count'] -= 1
    chat_history = chat_history[:-1]

  return (context_window_meta, analysis_window, chat_history, token_type_updated)


def get_context(api_key, uid, iid, table, boto3):
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

  return latest_UDS


def update_chat_history(context_window_meta, chat_history, um, im, ch_mtl):
  um_tl = um['token_length']
  im_tl = im['token_length']

  # if including the current umessage & imessage into the chat history will make it too large, remove necessary messages
  while context_window_meta['ch_token_length'] + um_tl + im_tl > ch_mtl:
    current_chm_tl = chat_history[-1]['token_length']
    context_window_meta['ch_token_length'] -= current_chm_tl
    context_window_meta['ch_message_count'] -= 1
    chat_history = chat_history[:-1]

  # add the current umessage & imessage to the chat history
  context_window_meta['ch_token_length'] += im_tl + um_tl
  context_window_meta['ch_message_count'] += 2

  return (context_window_meta, chat_history)


def add_messages_ddb(messages, table):
  '''
  Messages must be [{}] array of objects, purpotedly messages. Batch_writer automatically paginates if len(messages) > 25
  '''
  with table.batch_writer() as batch:
    for message in messages:
      batch.put_item(Item=message)


def add_message_ddb(message, table):
  table.put_item(Item=message)


def update_analysis_window(context_window_meta, um, im, analysis_window, aw_mtl, api_key, uid, iid):
  um_tl = um['token_length']
  im_tl = im['token_length']

  context_window_meta['aw_token_length'] += im_tl + um_tl
  context_window_meta['aw_message_count'] += 2
  analysis_window.insert(0, um)
  analysis_window.insert(0, im)

  # if the analysis window is too large, batch necessary messages and send to analysis
  batches_to_analyze = []

  if context_window_meta['aw_token_length'] > aw_mtl:
    # note that the analysis windows are zero indexed, hence the -1 delta from context_window_meta['aw_message_count'] / len(analysis_window)
    i = len(analysis_window) - 1
    current_batch_start = i
    current_batch_token_length = 0

    while i >= 0:
      # analyze from oldest to youngest
      message = analysis_window[i]
      current_batch_token_length += message['token_length']

      if current_batch_token_length > aw_mtl:
        batch_object = {
          "api_key": api_key,
          "uid": uid,
          "iid": iid,
          "batch": (current_batch_start, i)
        }
        batches_to_analyze.append(batch_object)

        context_window_meta['aw_token_length'] -= current_batch_token_length
        context_window_meta['aw_message_count'] -= (current_batch_start - i + 1)
        current_batch_start = i - 1
        current_batch_token_length = 0

      i -= 1

  return (context_window_meta, analysis_window, batches_to_analyze)
