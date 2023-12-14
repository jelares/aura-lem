from openai import OpenAI
import os
import simplejson as json

'''
OpenAI implementation of AURA ELKs (emotional-linguistic knowledge synthesizer)
'''
class ELKs:
  def __init__(self):
    self.type = "OpenAI"

  '''
  Synthesizes a response from the intelligence given the chat history, user message, and memory context. Streams to conn during building.
  '''
  def synthesize_response(self, chat_history, um, context, connectionId, conn):
    # response params
    params = {
      "Data":"",
      "ConnectionId": connectionId
    }

    # this aspect of system message is 63 tokens using llama sentience byte encoding
    system_message = "You are speaking to a user who's personality is mapped out below (may be empty). Numbers next to traits or skills are the % strength from 0-100%, and evidence is provided. Please only reference specifics if absolutely relevant, otherwise use holistically to inform your responses:\n\n"
    system_message += json.dumps(context)

    # Get API key from environment
    openai_key = os.environ['openai_key']
    openai_client = OpenAI(api_key=openai_key)

    # Specify the AI model
    model = "gpt-4-1106-preview"

    # set the history messages
    messages = []
     # insert system message
    messages.append({"role": "system", "content": system_message})

    # note that chat history goes from most recent to oldest, so must be reversed
    i = len(chat_history) - 1
    while i >= 0:
      item = chat_history[i]
      item['role'] = "assistant" if item['role'] == "intelligence" else "user"
      messages.append({"role": item['role'], "content": item['content']})

      i -= 1

    # add latest user message
    messages.append({"role": um['role'], "content": um['content']})

    for message in messages:
      print(message, "\n")

    # call openAI
    response = ""

    for resp in openai_client.chat.completions.create(model=model,
    messages=messages,
    stream=True,
    stop=None):
            
      if hasattr(resp.choices[0].delta, 'content'):
        res = resp.choices[0].delta.content

        if res is not None:
          response += res
          params["Data"] = json.dumps({"message": res, "status": "partial"})
          conn.post_to_connection(**params)

        else:
          params["Data"] = json.dumps({"message": "null", "status": "complete"})
          conn.post_to_connection(**params)

      else:
          params["Data"] = json.dumps({"message": "null", "status": "complete"})
          conn.post_to_connection(**params)

    im = {"content": response, "role": "intelligence"}
    return im
