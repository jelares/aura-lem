'''
Utilities for the LEMChat function
'''

import simplejson as json
from DynamoDBUtilities import *

def message_from_content(content, api_key, uid, iid, tokenizer):
  '''
  Creates and returns a full communication message from just text content.
  '''

  um_tl = tokenizer.calculate_tokenized_length(content)
  um = {"content": content, "role": "user", "uid": uid, "iid": iid}
  um["token_lengths"] = um_tl
  um["sortk"] = get_sortk_timestamp()
  um["partitionk"] = api_key + uid + iid + 'messages'
  return um


def validate_inputs(um, force_reflect, cw_config):
  '''
  Validates invariants about the inputs and returns a response accordingly. 
  '''
  input_validation_response = {}

  # future: validate the api key. For user sub, will be auto validated by aws
  
  # assert that either um is not empty, or this is a force reflect
  if (um["content"] == "") and (force_reflect == False):
    input_validation_response["statusCode"] = 400
    input_validation_response["response"] = {
      'statusCode': 400,
      'body': json.dumps(f'User message is empty, and force reflect is false.')
    }
    return input_validation_response

  # assert the um is the appropriate token length 
  if (um["token_lengths"][cw_config["elks_token_type"]] > cw_config["elks_um_mtl"]) or \
    (um["token_lengths"][cw_config["elam_token_type"]] > cw_config["elam_um_mtl"]):
    input_validation_response["statusCode"] = 400
    input_validation_response["response"] = {
      'statusCode': 400,
      'body': json.dumps(f'User message exceed max token length.')
    }
    return input_validation_response
  
  # asser a communication instance (CI) consisting of um + im together, can fit into the aw and ch
  elam_aw_check = (cw_config["elam_um_mtl"] + cw_config["elam_im_mtl"] < cw_config["elam_aw_mtl"])
  elks_ch_check = (cw_config["elks_um_mtl"] + cw_config["elks_response_mtl"] < cw_config["elks_ch_mtl"])

  if not (elam_aw_check and elks_ch_check):
    input_validation_response["statusCode"] = 400
    input_validation_response["response"] = {
      'statusCode': 400,
      'body': json.dumps(f'Context window misconfigured. UM & Response mtls are larger than ch and aw.')
    }
    return input_validation_response
  
  input_validation_response["statusCode"] = 200
  input_validation_response["response"] = None
  return input_validation_response


def get_context_window_meta(api_key, uid, iid, cw_config):
  '''
  Returns the communication meta information, or a blank template message if none exists.
  This object contains all meta-information about the context window sizes and current state,
  which is needed for AuraLEM to run. It does not contain the message data for aw & ch itself.
  '''
  cwm_response = {}

  # get the context window meta information
  context_window_meta_partitionk = api_key + uid + iid + 'ch_context_window_meta'
  context_window_meta_items = full_limit_query(context_window_meta_partitionk)

  context_window_meta = {}
  if not context_window_meta_items:       
    # if there is no item / cmwi was empty, this is the first time the user is chatting with this intelligence
    context_window_meta = {
      'partitionk': context_window_meta_partitionk,
      'sortk': get_sortk_timestamp(),
      'idempotency_lock': False,
      'elam_aw_token_length': 0,
      'elam_token_type': cw_config["elam_token_type"],
      'aw_message_count': 0, # the amount of messages to retrieve (starting from more recent) for the analysis window
      'elam_aw_mtl': cw_config["elam_aw_mtl"],
      'elks_ch_token_length': 0,
      'elks_token_type': cw_config["elks_token_type"],
      'ch_message_count': 0, # the amount of messages to retrieve (starting from more recent) for the chat history 
      'elks_ch_mtl': cw_config["elks_ch_mtl"]
    }

  else:
    # context_window_meta_items was not empty: set it to the latest context window meta object
    context_window_meta = context_window_meta_items[0]

  context_window_meta = json.loads(json.dumps(context_window_meta))

  cwm_response['cwm'] = context_window_meta
  cwm_response['uds_partition_key'] = api_key + uid + iid + 'UDS'
  cwm_response['message_history_partitionk'] = api_key + uid + iid + "messages"
  cwm_response['current_elam_aw_mtl'] = cw_config["elam_aw_mtl"]
  cwm_response['current_elks_ch_mtl'] = cw_config["elks_ch_mtl"]
  cwm_response['current_elam_token_type'] = cw_config["elam_token_type"]
  cwm_response['current_elks_token_type'] = cw_config["elks_token_type"]

  # past batch size to use for analysis window
  cwm_response['prev_elam_aw_mtl'] = context_window_meta["elam_aw_mtl"]
  cwm_response['aw_overflow_reflect'] = False

  cwm_response['elks_token_type_updated'] = context_window_meta["elks_token_type"] != cw_config["elks_token_type"]
  cwm_response['elam_token_type_updated'] = context_window_meta["elam_token_type"] != cw_config["elam_token_type"]

  # add the api_key, uid, and iid to cwm_response
  cwm_response['api_key'] = api_key
  cwm_response['uid'] = uid
  cwm_response['iid'] = iid

  return cwm_response


def idempotency_lock(cwm_response):
  '''
  Sets an idempotency lock for the AuraLEM data parameterized by (uid & iid)
  '''
  idempotency_response = {}

  # if the lock is already active
  if cwm_response['cwm']['idempotency_lock']:
    idempotency_response["statusCode"] = 400
    idempotency_response["response"] = {
      'statusCode': 400,
      'body': json.dumps('Process already running for this user, please wait for it to return completed.')
    }
    return idempotency_response

  # Lock for the remainder of this invocation
  else:
    cwm_response['cwm']['idempotency_lock'] = True

    # lock required data in dynamodb 
    put_item_ddb(cwm_response['cwm'])

    idempotency_response["statusCode"] = 200
    idempotency_response["response"] = {
      'statusCode': 200,
      'body': json.dumps('Idempotency check passed. Locked for rest of invokation.')
    }
    return idempotency_response


def get_context_window(cwm_response):
  '''
  Retrieves message data for context window (messages that will make up aw & ch, the uds, etc.) using
  the context window meta-information.
  '''
  cw_response = {}

  uds_partition_key = cwm_response['uds_partition_key']

  # Check if latest_UDS exists, if not create a blank one
  latest_UDS_items = full_limit_query(uds_partition_key, False)
  latest_UDS = latest_UDS_items[0]['uds'] if latest_UDS_items else None
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

  cw_response['uds'] = latest_UDS

  # get the current chat history and analysis window
  context_window_meta = cwm_response['cwm']

  analysis_window = []
  chat_history = []

  message_history = []
  limit = max(context_window_meta['aw_message_count'], context_window_meta['ch_message_count'])

  if(limit > 0):
    # get the current chat history and analysis window
    message_history_partitionk = cwm_response['message_history_partitionk']
    message_history = full_limit_query(message_history_partitionk, False, limit)

    # get the current analysis window
    analysis_window = message_history[:context_window_meta['aw_message_count']]

    # get the current chat history
    chat_history = message_history[:context_window_meta['ch_message_count']]


  cw_response['aw'] = analysis_window
  cw_response['ch'] = chat_history
  cw_response['message_history'] = message_history
  return cw_response


def validate_context_window(cw_response, cwm_response, tokenizer):
  '''
  Also validates all data, including messages and the context window metadata itself.
  Note: validation is necessary to maintain consistent state in the case cw config parameters have been changed.
  '''
  context_window_meta = cwm_response['cwm']
  chat_history = cw_response['ch']
  analysis_window = cw_response['aw']

  # if ELKS token definition has changed: update the chat metadata, and the chat window itself
  if cwm_response['elks_token_type_updated']:
    chat_history, ch_tls = tokenizer.update_token_context(cw_response['ch'])
    context_window_meta['elks_ch_token_length'] = ch_tls[cwm_response['current_elks_token_type']]
    context_window_meta['elks_token_type'] = cwm_response['current_elks_token_type']

  # NOTE 1: chat_history and analysis_window are ordered [(lastest/newest_message), ..., (oldest_message)]

  # if ch_mtl changed & chat history is now too large, remove necessary messages
  while context_window_meta['elks_ch_token_length'] > cwm_response["current_elks_ch_mtl"]: # continue until ch window is small enough
    current_chm_tl = chat_history[-1]['token_lengths'][cwm_response['current_elks_token_type']] # the oldest message's elk_tl
    context_window_meta['elks_ch_token_length'] -= current_chm_tl # subtract it from the cwm total tl
    context_window_meta['ch_message_count'] -= 1 # subtract one from the cwm chat history count
    chat_history = chat_history[:-1] # remove the message from the chat history window
  
  # if the elam token type changed, update the tokenization
  if cwm_response['elam_token_type_updated']:
    analysis_window, aw_tls = tokenizer.update_token_context(cw_response['aw'])
    context_window_meta['elam_aw_token_length'] = aw_tls[cwm_response['current_elam_token_type']]
    context_window_meta['elam_aw_token_type'] = cwm_response['current_elam_token_type']

  # if aw_mtl changed & analysis window has overflowed, queue a forced async reflect with the old params & start a new aw
  # NOTE: an invariant is that the aw is always smaller than the limit. So this will only be true if the limit changed, and it
  # should still be smaller than the old limit (which will be used for the final async reflect call)
  if context_window_meta['elam_aw_token_length'] > cwm_response['current_elam_aw_mtl']:
    cwm_response['aw_overflow_reflect'] = True

  cwm_response['cwm'] = context_window_meta

  cw_response['ch'] = chat_history
  cw_response['aw'] = analysis_window
  cw_response['message_history'] = chat_history if (len(chat_history) > len(analysis_window)) else analysis_window

  return (cw_response, cwm_response)


def update_context_window(cwm_response, cw_response, cw_config, um, im, force_reflect):
  '''
  Updates both the chat history and the analysis window, and returns the analysis response which
  determines what kind of chat analysis (if any) the ELAM should run.
  '''
  analysis_response = {}

  # update chat history first
  context_window_meta = cwm_response['cwm']

  # ELKS token lengths are relevant for chat history
  elks_um_tl = um['token_lengths'][cw_config['elks_token_type']]
  elks_im_tl = im['token_lengths'][cw_config['elks_token_type']]

  chat_history = cw_response['ch']
  analysis_window = cw_response['aw']

  # if including the current umessage & imessage into the chat history will make it too large, remove necessary messages
  # NOTE: always add user message along with assistant message as as single communication pair
  while context_window_meta['elks_ch_token_length'] + elks_um_tl + elks_im_tl > cw_config["elks_ch_mtl"]:
    current_chm_tl = chat_history[-1]['token_lengths'][cw_config['elks_token_type']]
    context_window_meta['elks_ch_token_length'] -= current_chm_tl
    context_window_meta['ch_message_count'] -= 1
    chat_history = chat_history[:-1]

  # add the current umessage & imessage to the chat history
  context_window_meta['elks_ch_token_length'] += elks_um_tl + elks_im_tl
  context_window_meta['ch_message_count'] += 2

  # update analysis window
  elam_um_tl = um['token_lengths'][cw_config['elam_token_type']]
  elam_im_tl = im['token_lengths'][cw_config['elam_token_type']]

  # three situations to understand: natural update, force_update, and aw_overflow_reflect

  # overflow reflect occurs when the LEM configuration changed: namely the aw_mtl changed. Must run a final reflect with the old aw_mtl
  # this is essentially a force_reflect with the previous parameters
  if cwm_response['aw_overflow_reflect']:
    analysis_response = {
      'analyze': True,
      'synchronous': False,
      'limits': [len(analysis_window), 2]
    }
    analysis_window = [im, um]
    context_window_meta['elam_aw_token_length'] = elam_um_tl + elam_im_tl
    context_window_meta['aw_message_count'] = 2

  # regular analysis window logic, add the two and send to analysis if necessary
  else:
    if (context_window_meta['elam_aw_token_length'] + elam_um_tl + elam_im_tl) > cw_config["elam_aw_mtl"]:
      analysis_response = {
      'analyze': True,
      'synchronous': False,
      'limits': [len(analysis_window)+2, 2]
      }
      analysis_window = [im, um]
      context_window_meta['elam_aw_token_length'] = elam_um_tl + elam_im_tl
      context_window_meta['aw_message_count'] = 2

    # if no analysis was naturally queued but is user asked for it to be forced, queue it
    elif (force_reflect):
      analysis_window.insert(0, um)
      analysis_window.insert(0, im)

      analysis_response = {
        'analyze': True,
        'synchronous': True,
        'limits': [len(analysis_window), 0],
        'analysis_window': analysis_window,
      }
      analysis_window = []
      context_window_meta['elam_aw_token_length'] = 0
      context_window_meta['aw_message_count'] = 0

    # else the window is still being built up, just add the two messages to the analysis window, no analysis needed atm
    else:
      analysis_response = {
        'analyze': False,
        'synchronous': None,
        'limits': None
      }
      analysis_window.insert(0, um)
      analysis_window.insert(0, im)
      context_window_meta['elam_aw_token_length'] += elam_um_tl + elam_im_tl
      context_window_meta['aw_message_count'] += 2

  analysis_response['api_key'] = cwm_response['api_key']
  analysis_response['uid'] = cwm_response['uid']
  analysis_response['iid'] = cwm_response['iid']
  analysis_response['elam_response_mtl'] = cw_config["elam_response_mtl"]

  return analysis_response, context_window_meta


def synchronize_ddb(context_window_meta, um, im):
  '''
  Synchronizes the dynamodb table with the current state of the context window, and adds the new um & im to message history.
  '''
  try:
    context_window_meta['idempotency_lock'] = False

    items_to_put = [context_window_meta, um, im]
    put_items_ddb(items_to_put)

    return {
      'statusCode': 200,
      'body': json.dumps('Successfully synchronized ddb.')
    }

  except Exception as e:
    return f"An error occurred: {str(e)}"

