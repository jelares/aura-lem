import simplejson as json

"""
Fake class mimicing the AWS API Gateway connection object for ws
"""
class FakeConn:
  def __init__(self):
    pass

  def post_to_connection(self, **kwargs):
    # Print the new characters without a newline and flush the output
    if json.loads(kwargs['Data'])['status'] != "complete":
      print(json.loads(kwargs['Data'])["message"], end='', flush=True)
    else:
      print("[COMPLETE]")