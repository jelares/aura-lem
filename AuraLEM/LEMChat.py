import simplejson as json
import boto3
from LEMChatUtilities import *
from AuraELAM.OpenAIELAM import analyze
from CW_configs import get_cw_config
from Tokenizers.Tokenizer import Tokenizer
from AuraELKs.OpenAIELKs import synthesize_response

# conn = boto3.client("apigatewaymanagementapi", endpoint_url="https://bvm4vv2jm6.execute-api.us-east-1.amazonaws.com/dev")
from LEMTestUtilities import FakeConn

conn = FakeConn()

# top-level LEM config
cw_config = get_cw_config("production")
# cw_config = get_cw_config("local_test_small")

# note: tokenizer may have multiple sub-tokenizers
tokenizer = Tokenizer({cw_config["elks_token_type"], cw_config["elam_token_type"]})


def lambda_handler(event, context):
    """
    INVARIENTS:
    elam_tl(aw) <= what ddb stores as: context_window_meta["elam_aw_mtl"].
    In other words, the analysis window token length will always be at least smaller than the previous
    analysis window limit, even if it has just been changed to be smaller in this current iteration.
    """

    # Get data from request
    connectionId = event["requestContext"]["connectionId"]

    # Load the user query
    body = json.loads(event["body"])

    try:
        api_key = str(body["sub"])
        uid = str(
            body["uid"]
        )  # uid and iid uniquely identify a communication thread for a given api key
        iid = str(body["iid"])
        um_content = str(body["user_message"])
        force_reflect = bool(body["force_reflect"])
    except Exception as e:
        return {
            "statusCode": 400,
            "body": json.dumps(f"Error in request body: {str(e)}"),
        }

    # creates the user message from only text content
    um = message_from_content(um_content, api_key, uid, iid, tokenizer)

    # validates inputs
    input_validation_response = validate_inputs(um, force_reflect, cw_config)
    if input_validation_response["statusCode"] != 200:
        return input_validation_response["response"]

    # get context window metadata
    cwm_response = get_context_window_meta(api_key, uid, iid, cw_config)

    # checks idempotency locks: if locked, returns, else locks for the remainder of communication
    idempotency_response = idempotency_lock(cwm_response)
    if idempotency_response["statusCode"] != 200:
        return idempotency_response["response"]

    # uses cw meta to get all context: UDS, analysis & chat windows.
    cw_response = get_context_window(cwm_response)

    # if necessary, validates all context window data & meta-data
    cw_response, cwm_response = validate_context_window(
        cw_response, cwm_response, tokenizer
    )

    # synthesizes all context into an intelligence response, streams to the user
    im = synthesize_response(cw_response, cw_config, um, tokenizer, connectionId, conn)

    # updates ch_meta, ch & aw window, returns anything needed for analysis
    analysis_input, context_window_meta = update_context_window(
        cwm_response, cw_response, cw_config, um, im, force_reflect
    )

    # synchronizes ddb state & unlocks the data for future manipulation.  Unlocks idempotency lock.
    synchronize_ddb(context_window_meta, um, im)

    # syncronously if force_analyze = true, asyncronously if prompted by analysis-window.
    analysis_response = analyze(analysis_input)

    return {
        "statusCode": 200,
        "body": json.dumps(
            "Communication Instance completed successfully. Data unlocked."
        ),
    }
