from LEMChat import lambda_handler
import simplejson as json
from LEMChatUtilities import *
from DynamoDBUtilities import *
import boto3
from CW_configs import get_cw_config

client = boto3.resource("dynamodb", region_name="us-east-1")
table = client.Table("UserData")

api_key = "daniel"
uid = "user"
iid = "intelligence"

cw_config = get_cw_config("production")


def reset_context_window_meta():
    context_window_meta_partitionk = api_key + uid + iid + "ch_context_window_meta"

    context_window_meta = {
        "partitionk": context_window_meta_partitionk,
        "sortk": get_sortk_timestamp(),
        "idempotency_lock": False,
        "elam_aw_token_length": 0,
        "elam_token_type": cw_config["elam_token_type"],
        "aw_message_count": 0,  # the amount of messages to retrieve (starting from more recent) for the analysis window
        "elam_aw_mtl": cw_config["elam_aw_mtl"],
        "elks_ch_token_length": 0,
        "elks_token_type": cw_config["elks_token_type"],
        "ch_message_count": 0,  # the amount of messages to retrieve (starting from more recent) for the chat history
        "elks_ch_mtl": cw_config["elks_ch_mtl"],
    }

    response = put_item_ddb(context_window_meta)
    print("update cwm: ", response)


def update_idempotency_lock():
    context_window_meta_partitionk = api_key + uid + iid + "ch_context_window_meta"

    context_window_meta = full_limit_query(context_window_meta_partitionk)
    context_window_meta = context_window_meta[0]
    context_window_meta["idempotency_lock"] = False

    response = put_item_ddb(context_window_meta)
    print("update cwm: ", response)


def run_test(force_reflect=False):
    while True:
        um = input("User message:\n")
        # TEST USER MESSAGE
        # um = "User message:\n Yesterday's tomorrow famously outran today while whispering secrets to the non-existent audience of a paradoxical play, where the protagonist simultaneously climbed an endlessly descending staircase. In this scenario, the colorless green ideas sleep furiously as the square circle debates with the audible fragrance of invisibility. Meanwhile, in a parallel universe where time travels backward, the future reminisces about the past, and a cat, both alive and deceased in Schrödinger's unopened box, recites the complete works of Shakespeare in ancient Sumerian. All while a quantum computer solves an unsolvable riddle by not solving it, encapsulating the essence of a never-ending story that ends on the first page Yesterday's tomorrow famously outran today while whispering secrets to the non-existent audience of a paradoxical play, where the protagonist simultaneously climbed an endlessly descending staircase. In this scenario, the colorless green ideas sleep furiously as the square circle debates with the audibleYesterday's tomorrow famously outran today while whispering secrets to the non-existent audience of a paradoxical play, where the protagonist simultaneously climbed an endlessly descending staircase. In this scenario, the colorless green ideas sleep furiously as the square circle debates with the audible fragrance of invisibility. Meanwhile, in a parallel universe where time travels backward, the future reminisces about the past, and a cat, both alive and deceased in Schrödinger's unopened box, recites the complete works of Shakespeare in ancient Sumerian. All while a quantum computer solves an unsolvable riddle by not solving it, encapsulating the essence of a never-ending story that ends on the first page Yesterday's tomorrow famously outran today while whispering secrets to the non-existent audience of a paradoxical play, where the protagonist simultaneously climbed an endlessly descending staircase. In this scenario, the colorless green ideas sleep furiously as the square circle debates with the audibleYesterday's tomorrow famously outran today while whispering secrets to the non-existent audience of a paradoxical play, where the protagonist simultaneously climbed an endlessly descending staircase. In this scenario, the colorless green ideas sleep furiously as the square circle debates with the audible fragrance of invisibility. Meanwhile, in a parallel universe where time travels backward, the future reminisces about the past, and a cat, both alive and deceased in Schrödinger's unopened box, recites the complete works of Shakespeare in ancient Sumerian. All while a quantum computer solves an unsolvable riddle by not solving it, encapsulating the essence of a never-ending story that ends on the first page Yesterday's tomorrow famously outran today while whispering secrets to the non-existent audience of a paradoxical play, where the protagonist simultaneously climbed an endlessly descending staircase. In this scenario, the colorless green ideas sleep furiously as the square circle debates with the audibleYesterday's tomorrow famously outran today while whispering secrets to the non-existent audience of a paradoxical play, where the protagonist simultaneously climbed an endlessly descending staircase. In this scenario, the colorless green ideas sleep furiously as the square circle debates with the audible fragrance of invisibility. Meanwhile, in a parallel universe where time travels backward, the future reminisces about the past, and a cat, both alive and deceased in Schrödinger's unopened box, recites the complete works of Shakespeare in ancient Sumerian. All while a quantum computer solves an unsolvable riddle by not solving it, encapsulating the essence of a never-ending story that ends on the first page Yesterday's tomorrow famously outran today while whispering secrets to the non-existent audience of a paradoxical play, where the protagonist simultaneously climbed an endlessly descending staircase. In this scenario, the colorless green ideas sleep furiously as the square circle debates with the audibleYesterday's tomorrow famously outran today while whispering secrets to the non-existent audience of a paradoxical play, where the protagonist simultaneously climbed an endlessly descending staircase. In this scenario, the colorless green ideas sleep furiously as the square circle debates with the audible fragrance of invisibility. Meanwhile, in a parallel universe where time travels backward, the future reminisces about the past, and a cat, both alive and deceased in Schrödinger's unopened box, recites the complete works of Shakespeare in ancient Sumerian. All while a quantum computer solves an unsolvable riddle by not solving it, encapsulating the essence of a never-ending story that ends on the first page Yesterday's tomorrow famously outran today while whispering secrets to the non-existent audience of a paradoxical play, where the protagonist simultaneously climbed an endlessly descending staircase. In this scenario, the colorless green ideas sleep furiously as the square circle debates with the audibleYesterday's tomorrow famously outran today while whispering secrets to the non-existent audience of a paradoxical play, where the protagonist simultaneously climbed an endlessly descending staircase. In this scenario, the colorless green ideas sleep furiously as the square circle debates with the audible fragrance of invisibility. Meanwhile, in a parallel universe where time travels backward, the future reminisces about the past, and a cat, both alive and deceased in Schrödinger's unopened box, recites the complete works of Shakespeare in ancient Sumerian. All while a quantum computer solves an unsolvable riddle by not solving it, encapsulating the essence of a never-ending story that ends on the first page Yesterday's tomorrow famously outran today while whispering secrets to the non-existent audience of a paradoxical play, where the protagonist simultaneously climbed an endlessly descending staircase. In this scenario, the colorless green ideas sleep furiously as the square circle debates with the audible"
        # TEST USER MESSAGE
        print("\n\n")

        response = lambda_handler(
            {
                "requestContext": {"connectionId": "test"},
                "body": json.dumps(
                    {
                        "sub": api_key,
                        "uid": uid,
                        "iid": iid,
                        "user_message": um,
                        "force_reflect": force_reflect,
                    }
                ),
            },
            None,
        )

        print(response, "\n\n")


def ref_run_test(um, force_reflect=False):
    response = lambda_handler(
        {
            "requestContext": {"connectionId": "test"},
            "body": json.dumps(
                {
                    "sub": api_key,
                    "uid": uid,
                    "iid": iid,
                    "user_message": um,
                    "force_reflect": force_reflect,
                }
            ),
        },
        None,
    )

    return response


"""
Practice testing the LEM system.
"""


def main():
    # reset_context_window_meta()
    update_idempotency_lock()
    run_test(False)


if __name__ == "__main__":
    main()
