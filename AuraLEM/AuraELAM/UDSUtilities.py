import simplejson as json


def validate_response(response):
  uds_text = response.choices[0].message.content
  uds_dict = {}
  try:
    uds_dict = json.loads(uds_text)

  except Exception as e:
    return [False, "Invalid JSON string"]
  
  try:
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
    
  except Exception as e:
    return [False, str(e)]