import tiktoken

class OpenAITokenizer():
  def __init__(self, token_type):
    # make sure the LEMChat knows this is the token type it is using
    assert (token_type == "cl100k_base")
    self.token_type = "cl100k_base"
    self.tokenizer = tiktoken.get_encoding("cl100k_base")

  
  def calculate_tokenized_length(self, text):
    tokens = self.tokenizer.encode(text)
    return len(tokens)
  

  def update_token_context(self, messages):
    # get the current token length
    window_tl = 0
    
    # tokenize the messages
    for message in messages:
      tl = self.calculate_tokenized_length(message["content"])
      message["token_length"] = tl
      message["token_type"] = self.token_type
      window_tl += tl
    
    return (messages, window_tl)


### testing
# def main():
#   tokenizer = Tokenizer("cl100k_base")

#   # while True:
#     # text = input("Enter text to tokenize: ")

#   text = """The latency of tokenization using moronment."""
#   print(tokenizer.calculate_tokenized_length(text))
#   print("\n\n")

# if __name__ == "__main__":
#     main()