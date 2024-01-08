from Tokenizers.OpenAITokenizer import OpenAITokenizer
from Tokenizers.LLAMASentiencePiece import LLAMASentiencePiece

class Tokenizer():
  '''
  Higher-level tokenizer that uses sub-tokenizers to tokenize text. This is used by LEMChat to tokenize messages.
  '''

  def __init__(self, token_types):
    self.token_types = token_types

    self.tokenizers = {} # { token_type: tokenizer object }
    if "cl100k_base" in token_types: self.tokenizers["cl100k_base"]= OpenAITokenizer("cl100k_base")
    if "LLAMASentencePieceBytePairEncoding" in token_types: self.tokenizers["LLAMASentencePieceBytePairEncoding"] = LLAMASentiencePiece("LLAMASentencePieceBytePairEncoding")

    # must have at least one sub-tokenizer in the tokenizer
    assert (len(self.tokenizers) > 0)
  
  def calculate_tokenized_length(self, text):
    lengths = {} # { token_type: tokenized_length }
    for token_type in self.tokenizers:
      lengths[token_type] = self.tokenizers[token_type].calculate_tokenized_length(text)
    return lengths
  

  def update_token_context(self, messages):
    '''
    Retokenizes all the messages in messages according to the subtokenizers. Returns a list of modified messages along with their
    total token lengths.
    '''
    # get the current token length
    window_tls = {}

    # initialize window_tls to zero
    for token_type in self.tokenizers:
      window_tls[token_type] = 0
    
    # tokenize the messages
    for message in messages:
      tls = self.calculate_tokenized_length(message["content"])
      message["token_lengths"] = tls

      # iterate through token_types, the keys of tls
      for token_type in tls:
        window_tls[token_type] += tls[token_type]
    
    return (messages, window_tls)


def main():
  tokenizerOpenAI = Tokenizer("cl100k_base")
  tokenizerDouble = Tokenizer(["cl100k_base", "LLAMASentencePieceBytePairEncoding"])

  # while True:
    # text = input("Enter text to tokenize: ")

  text = """The latency of tokenization using moronment."""
  print(tokenizerOpenAI.calculate_tokenized_length(text))
  print(tokenizerDouble.calculate_tokenized_length(text))
  print("\n\n")

  texts = [{"content": "what what lorem ispsuamf  lsdklj and the n hta aay yeah that cool."}, {"content": "token example"},  {"content": ""}]
  result = tokenizerDouble.update_token_context(texts)
  print(result[0])
  print(result[1])


if __name__ == "__main__":
    main()