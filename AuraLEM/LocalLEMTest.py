from LEMChat import lambda_handler
import simplejson as json
from LEMChatUtilities import *
import boto3

client = boto3.resource('dynamodb')
table = client.Table('UserData')

api_key = "jesus"
uid = "user5"
iid = "intelligence5"
token_type = "LLAMASentencePieceBytePairEncoding" # the type of tokens used

def reset_context_window_meta():
  context_window_meta_partitionk = api_key + uid + iid + 'ch_context_window_meta'

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

  response = add_message_ddb(context_window_meta, table)
  print("success: ", response)


def run_test():
  while True:
    um = input("User message:\n")
    response = lambda_handler({
      "requestContext": {
        "connectionId": "test"
      },
      "body": json.dumps({
        "sub": api_key,
        "uid": uid,
        "iid": iid,
        "user_message": um
      })
    }, None)

    print("\n", response, "\n")

'''
Practice testing the LEM system.
'''
def main():
  # reset_context_window_meta()
  run_test()

if __name__ == "__main__":
    main()