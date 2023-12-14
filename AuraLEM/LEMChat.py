import simplejson as json
import boto3
from LEMChatUtilities import *
from AuraELKs.OpenAIELKs import ELKs
from AuraELAM.OpenAIELAM import batch_analyze
from Tokenizers.LLAMASentiencePiece import Tokenizer
from LEMTestUtilities import FakeConn

# conn = boto3.client("apigatewaymanagementapi", endpoint_url="https://bvm4vv2jm6.execute-api.us-east-1.amazonaws.com/dev")
conn = FakeConn()
client = boto3.resource('dynamodb')
table = client.Table('UserData')

# top-level LEM config
token_type = "LLAMASentencePieceBytePairEncoding" # the type of tokens used

# context window size breakdown
# ctx_ws = 4096 # the context window size
# response_mtl = 500 # the max length of the response (in tokens of token_type)
# um_mtl = 500 # the max length of the user input (in tokens)
# ch_mtl = 1596 # max length of chat history (in tokens)
# uds_mtl = 1480 # max length of context information: system message, UDS & IDS (in tokens)
# wiggle_room = 20 # the amount of wiggle room allowed for the context window (in tokens)

ctx_ws = 100 # the context window size
response_mtl = 20 # the max length of the response (in tokens of token_type)
um_mtl = 20 # the max length of the user input (in tokens)
ch_mtl = 50 # max length of chat history (in tokens)
uds_mtl = 50 # max length of context information: system message, UDS & IDS (in tokens)
wiggle_room = 10 # the amount of wiggle room allowed for the context window (in tokens)

# the max length of the analysis window (in tokens)
# aw_mtl = 1596

aw_mtl = 50

# create the tokenizer 
ELKs = ELKs()
tokenizer = Tokenizer(token_type)

def lambda_handler(event, context):
  # Get data from request
  connectionId = event["requestContext"]["connectionId"]

  # Load the user query
  body = json.loads(event["body"])

  # uid and iid uniquely identify a communication thread for a given api key
  api_key = str(body["sub"])
  uid = str(body["uid"])
  iid = str(body["iid"])
  um = {"content": str(body["user_message"]), "role": "user", "uid": uid, "iid": iid}

  um_tl = tokenizer.calculate_tokenized_length(um["content"])

  # checkpoint 1: tokenizer counter works
  print("tl of message: ", um_tl, "\n\n")

  um["token_length"] = um_tl
  um["token_type"] = token_type
  um["sortk"] = get_sortk_timestamp()
  um["partitionk"] = api_key + uid + iid + 'messages'

  # Idempotency check - check if the process is already active for this user and intelligence
  idempotency_key = api_key + uid + iid + "idempotency_key"
  lock_already_active, idempotency_response = check_then_activate_idempotency_lock(idempotency_key, table)
  if lock_already_active:
    return idempotency_response

  um_invalid, invalid_um_response = validate_user_message(um, um_mtl)
  if um_invalid:
    return invalid_um_response

  # get the communication meta information
  context_window_meta = get_context_window_meta(api_key, uid, iid, table, token_type, boto3)

  # checkpoint 2: context_window_meta works
  print("context window meta: ", context_window_meta, "\n\n")

  # get analysis & context window messages
  analysis_window, chat_history = get_analysis_and_chat_windows(context_window_meta, api_key, uid, iid, table, boto3)

  # checkpoint 3
  # print("analysis window: ", analysis_window, "\n\n")
  # print("chat history: ", chat_history, "\n\n")

  # validate the analysis & chat windows, and the context_window_meta objects. Namely, their tokenization is up to date
  context_window_meta, analysis_window, chat_history, token_type_updated = validate_windows_and_meta(context_window_meta, analysis_window, chat_history, token_type, tokenizer, ch_mtl)

  # edge case: if the token type of chat history and analyis window were not up to date, make them so in ddb (for analysis)
  if(token_type_updated):
    ch_extending_analysis_window = chat_history.extends(analysis_window)
    add_messages_ddb(ch_extending_analysis_window, table)

  # make the ELKs call after all system configuration
  message_context = get_context(api_key, uid, iid, table, boto3) # MVP: UDS

  print("Context: ", message_context, "\n\n")

  # synthesize the resopnse & stream it back to the user during building
  im = ELKs.synthesize_response(chat_history, um, message_context, connectionId, conn)
  im_tl = tokenizer.calculate_tokenized_length(im["content"])
  im["token_length"] = im_tl
  im["token_type"] = token_type
  im["sortk"] = get_sortk_timestamp()
  im["partitionk"] = api_key + uid + iid + 'messages'
  im["uid"] = uid
  im["iid"] = iid

  # update the chat history with the new user message, intelligence message, and keep context_window_meta synced
  context_window_meta, chat_history = update_chat_history(context_window_meta, chat_history, um, im, ch_mtl)

  # add the current messages to dynamodb
  add_messages_ddb([um, im], table)

  # update analysis window - add the two new messages for analysis
  context_window_meta, analysis_window, batches_to_analyze = update_analysis_window(context_window_meta, um, im, analysis_window, aw_mtl, api_key, uid, iid)

  # update the context window meta in dynamodb
  add_message_ddb(context_window_meta, table)

  print("\n\nNew context_window_meta: ", context_window_meta, "\n\n")
  print("Batches to analyze: ", batches_to_analyze, "\n\n")

  # Clear the active flag
  table.put_item(Item={'partitionk': idempotency_key, 'sortk': get_sortk_timestamp(), 'active': True})

  # at this point, the only messages left in the aw have sum token length less than the acceptable aw_mtl
  # batches_to_analyze may be empty if the aw is still being built up (has not exceeded aw_mtl), in which case ELAM does nothing

  # in prod this will be a call to activate a lambda step function
  # Map state accepts a JSON array as input. It executes the same workflow steps for each element of the array.
  batch_analyze(batches_to_analyze) # ASYNC

  return {
    'statusCode': 200,
    'body': json.dumps('Request processed successfully')
  }
  