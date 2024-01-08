from datetime import datetime
import simplejson as json
import pytz
import boto3

client = boto3.resource('dynamodb')
table = client.Table('UserData')

'''
Returns a timestamp for use as sort key
'''
def get_sortk_timestamp():
  # get latest timestamp for sork key purposes
  utc_now = datetime.now(pytz.utc)
  timestamp = utc_now.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
  sortk_t = timestamp
  return sortk_t


def put_items_ddb(items):
  '''
  Adds multiple items to ddb.
  Items must be [{}] iterable of objects, purpotedly items. Batch_writer automatically paginates if len(messages) > 25
  '''
  try:
    with table.batch_writer() as batch:
      for item in items:
        batch.put_item(Item=item)
    return "Messages added successfully"
  
  except Exception as e:
    # Handle or log the exception as needed
    return f"An error occurred: {str(e)}"


def put_item_ddb(item):
  """
  Simply puts and item to ddb.
  """
  try:
    table.put_item(Item=item)
    return {
      'statusCode': 200,
      'body': json.dumps('Request processed successfully')
    }
  
  except Exception as e:
    # Handle or log the exception as needed
    return {
      'statusCode': 500,
      'body': json.dumps(f"An error occurred: {str(e)}")
    }


def full_limit_query(partitionk, scan_index_forward=True, limit=1):
  """
  Returns a full query items list (NOT response) for a given partitionk, sortk, and limit. As in, it returns
  all items specified by limit regardless of the 1mb ddb limit.

  paritionk: the partition key for the query in user-data
  scan_index_forward: True if ascending, False if descending
  limit: the items to be returned, must be at least 1
  """
  # all items will be placed, ordered, in the list below
  items = []

  # Initial query
  initial_items_response = table.query(
    KeyConditionExpression=boto3.dynamodb.conditions.Key('partitionk').eq(partitionk),
    ScanIndexForward=scan_index_forward,
    Limit=limit
  )

  # Adding initial items
  items.extend(initial_items_response['Items'])

  # Pagination handling
  while ('LastEvaluatedKey' in initial_items_response and len(items) < limit):
    initial_items_response = table.query(
      KeyConditionExpression=boto3.dynamodb.conditions.Key('partitionk').eq(partitionk),
      ScanIndexForward=scan_index_forward,
      ExclusiveStartKey=initial_items_response['LastEvaluatedKey'],
      Limit=limit - len(items)
    )
    items.extend(initial_items_response['Items'])

  return items