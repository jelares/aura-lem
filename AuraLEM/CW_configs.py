def get_cw_config(name):
  config_object = {}

  if name == 'production':
    config_object = {
      "elks_token_type": "cl100k_base", # the type of tokens used for the ELKs
      "elks_ctx_ws": 4096, # the context window size
      "elks_response_mtl": 500, # the max length of the response (in tokens of token_type)
      "elks_um_mtl": 500, # the max length of the user input (in tokens)
      "elks_ch_mtl": 1596, # max length of chat history (in tokens)
      "elks_uds_mtl": 1393, # max length of UDS (in tokens)
      "elks_system_tl": 92, # length of system message (in tokens)
      "elks_wiggle_room": 15, # the amount of wiggle room allowed for the context window (in tokens)

      "elam_token_type": "cl100k_base", # the type of tokens used for the ELAM
      "elam_ctx_ws": 4096, # the context window size
      "elam_response_mtl": 1393, # cannot exceed UDS max length
      "elam_system_tl": 531, # max length of system message (in tokens)
      "elam_um_mtl": 500, # the max length of the user input (in tokens)
      "elam_im_mtl": 500, # the max length of the intellignece message (in elam tokens)
      "elam_aw_mtl": 1596, # the max length of the analysis window (in tokens)
      "elam_wiggle_room": 15, # the amount of wiggle room allowed for the context window (in tokens)
    }

  elif name == 'local_test_small':
    config_object = {
      "elks_token_type": "cl100k_base", # the type of tokens used for the ELKs
      "elks_ctx_ws": 1590, # the context window size
      "elks_response_mtl": 20, # the max length of the response (in tokens of token_type)
      "elks_um_mtl": 20, # the max length of the user input (in tokens)
      "elks_ch_mtl": 50, # max length of chat history (in tokens)
      "elks_uds_mtl": 1393, # max length of UDS (in tokens)
      "elks_system_tl": 92, # length of system message (in tokens)
      "elks_wiggle_room": 15, # the amount of wiggle room allowed for the context window (in tokens)

      "elam_token_type": "cl100k_base", # the type of tokens used for the ELAM
      "elam_ctx_ws": 1590, # the context window size
      "elam_response_mtl": 1393, # cannot exceed UDS max length
      "elam_system_tl": 531, # max length of system message (in tokens)
      "elam_um_mtl": 20, # the max length of the user input (in tokens)
      "elam_im_mtl": 20, # the max length of the intellignece message (in elam tokens)
      "elam_aw_mtl": 50, # the max length of the analysis window (in tokens)
      "elam_wiggle_room": 15, # the amount of wiggle room allowed for the context window (in tokens)
    }

  else:
    config_object = {
      "elks_token_type": "cl100k_base", # the type of tokens used for the ELKs
      "elks_ctx_ws": 4096, # the context window size
      "elks_response_mtl": 500, # the max length of the response (in tokens of token_type)
      "um_mtl": 500, # the max length of the user input (in tokens)
      "ch_mtl": 1596, # max length of chat history (in tokens)
      "uds_mtl": 1393, # max length of UDS (in tokens)
      "elks_system_tl": 92, # length of system message (in tokens)
      "elks_wiggle_room": 15, # the amount of wiggle room allowed for the context window (in tokens)
      "elam_token_type": "cl100k_base", # the type of tokens used for the ELAM
      "elam_ctx_ws": 4096, # the context window size
      "elam_response_mtl": 1393, # cannot exceed UDS max length
      "elam_system_tl": 531, # max length of system message (in tokens)
      "aw_mtl": 1596, # the max length of the analysis window (in tokens)
      "elam_wiggle_room": 15, # the amount of wiggle room allowed for the context window (in tokens)
    }

  return config_object
