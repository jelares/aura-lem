import unittest
import json
from unittest.mock import patch, MagicMock
from LEMChat import lambda_handler


class TestLambdaHandler(unittest.TestCase):
    @patch("LEMChat.message_from_content")
    @patch("LEMChat.validate_inputs")
    @patch("LEMChat.get_context_window_meta")
    @patch("LEMChat.idempotency_lock")
    @patch("LEMChat.get_context_window")
    @patch("LEMChat.validate_context_window")
    @patch("LEMChat.synthesize_response")
    @patch("LEMChat.update_context_window")
    @patch("LEMChat.synchronize_ddb")
    @patch("LEMChat.analyze")
    def test_lambda_handler(
        self,
        mock_analyze,
        mock_synchronize_ddb,
        mock_update_context_window,
        mock_synthesize_response,
        mock_validate_context_window,
        mock_get_context_window,
        mock_idempotency_lock,
        mock_get_context_window_meta,
        mock_validate_inputs,
        mock_message_from_content,
    ):
        # Mock the request event and context
        event = {
            "requestContext": {"connectionId": "test_connection"},
            "body": json.dumps(
                {
                    "sub": "test_sub",
                    "uid": "test_uid",
                    "iid": "test_iid",
                    "user_message": "test_message",
                    "force_reflect": False,
                }
            ),
        }
        context = {}

        # Mock the functions called in lambda_handler
        mock_message_from_content.return_value = "mock_message"
        mock_validate_inputs.return_value = {"statusCode": 200}
        mock_get_context_window_meta.return_value = "mock_meta"
        mock_idempotency_lock.return_value = {"statusCode": 200}
        mock_get_context_window.return_value = "mock_window"
        mock_validate_context_window.return_value = ("mock_window", "mock_meta")
        mock_synthesize_response.return_value = "mock_response"
        mock_update_context_window.return_value = ("mock_analysis_input", "mock_meta")
        mock_synchronize_ddb.return_value = None
        mock_analyze.return_value = "mock_analysis_response"

        # Call the function with the mock inputs
        result = lambda_handler(event, context)

        # Assert that the result is as expected
        self.assertEqual(
            result,
            {
                "statusCode": 200,
                "body": json.dumps(
                    "Communication Instance completed successfully. Data unlocked."
                ),
            },
        )

    def test_lambda_handler_missing_fields(self):
        event = {
            "requestContext": {"connectionId": "test_connection"},
            "body": json.dumps(
                {"sub": "test_sub", "uid": "test_uid", "iid": "test_iid"}
            ),
        }
        context = {}
        result = lambda_handler(event, context)
        self.assertEqual(result["statusCode"], 400)

    @patch("LEMChat.message_from_content")
    @patch("LEMChat.validate_inputs")
    def test_lambda_handler_invalid_inputs(
        self, mock_validate_inputs, mock_message_from_content
    ):
        event = {
            "requestContext": {"connectionId": "test_connection"},
            "body": json.dumps(
                {
                    "sub": "test_sub",
                    "uid": "test_uid",
                    "iid": "test_iid",
                    "user_message": "test_message",
                    "force_reflect": False,
                }
            ),
        }
        context = {}
        mock_message_from_content.return_value = "mock_message"
        mock_validate_inputs.return_value = {
            "statusCode": 400,
            "response": {"statusCode": 400, "body": '"test error"'},
        }
        result = lambda_handler(event, context)
        self.assertEqual(result["statusCode"], 400)


if __name__ == "__main__":
    unittest.main()
