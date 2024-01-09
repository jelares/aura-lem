import unittest
from unittest.mock import Mock, patch
from LEMChatUtilities import *


class TestLEMChatUtilities(unittest.TestCase):
    def setUp(self):
        self.tokenizer = Mock()
        self.tokenizer.calculate_tokenized_length.return_value = 10
        self.api_key = "test_api_key"
        self.uid = "test_uid"
        self.iid = "test_iid"
        self.content = "test_content"
        self.um = {
            "content": self.content,
            "role": "user",
            "uid": self.uid,
            "iid": self.iid,
            "token_lengths": 10,
            "sortk": "timestamp",
            "partitionk": self.api_key + self.uid + self.iid + "messages",
        }
        self.cw_config = {
            "elks_token_type": "elks",
            "elks_um_mtl": 20,
            "elam_token_type": "elam",
            "elam_um_mtl": 20,
            "elam_aw_mtl": 40,
            "elks_response_mtl": 20,
            "elks_ch_mtl": 40,
        }

    def test_message_from_content(self):
        with patch("LEMChatUtilities.get_sortk_timestamp", return_value="timestamp"):
            result = message_from_content(
                self.content, self.api_key, self.uid, self.iid, self.tokenizer
            )
        self.assertEqual(result, self.um)

    # def test_validate_inputs(self):
    #     result = validate_inputs(self.um, False, self.cw_config)
    #     self.assertEqual(result["statusCode"], 200)

    def test_get_context_window_meta(self):
        with patch("LEMChatUtilities.full_limit_query", return_value=[]), patch(
            "LEMChatUtilities.get_sortk_timestamp", return_value="timestamp"
        ):
            result = get_context_window_meta(
                self.api_key, self.uid, self.iid, self.cw_config
            )
        self.assertEqual(
            result["cwm"]["partitionk"],
            self.api_key + self.uid + self.iid + "ch_context_window_meta",
        )

    def test_idempotency_lock(self):
        cwm_response = {"cwm": {"idempotency_lock": False}}
        with patch("LEMChatUtilities.put_item_ddb"):
            result = idempotency_lock(cwm_response)
        self.assertEqual(result["statusCode"], 200)

    # @patch("LEMChatUtilities.full_limit_query")
    # def test_validate_context_window(self, mock_query):
    #     # Mocking the full_limit_query function to return a predefined result
    #     mock_query.return_value = [{"message": "Hello"}]

    #     cw_response = {
    #         "ch": [{"message": "Hello", "token_lengths": {"elks_token_type": 5}}],
    #         "aw": [{"message": "Hello", "token_lengths": {"elam_token_type": 5}}],
    #         "message_history": [{"message": "Hello"}],
    #     }

    #     cwm_response = {
    #         "current_elks_ch_mtl": 10,
    #         "current_elam_aw_mtl": 10,
    #         "elks_token_type_updated": False,
    #         "elam_token_type_updated": False,
    #         "cwm": {"elks_ch_token_length": 5, "elam_aw_token_length": 5},
    #     }

    #     tokenizer = MagicMock()
    #     tokenizer.update_token_context.return_value = (
    #         [{"message": "Hello", "token_lengths": {"elks_token_type": 5}}],
    #         {"elks_token_type": 5},
    #     )

    #     result = validate_context_window(cw_response, cwm_response, tokenizer)
    #     self.assertEqual(
    #         result[0]["ch"],
    #         [{"message": "Hello", "token_lengths": {"elks_token_type": 5}}],
    #     )
    #     self.assertEqual(
    #         result[0]["aw"],
    #         [{"message": "Hello", "token_lengths": {"elam_token_type": 5}}],
    #     )
    #     self.assertEqual(result[1]["cwm"]["elks_ch_token_length"], 5)
    #     self.assertEqual(result[1]["cwm"]["elam_aw_token_length"], 5)

    # def test_update_context_window(self):
    #     cwm_response = {
    #         "cwm": {
    #             "elam_aw_token_length": 0,
    #             "elks_ch_token_length": 0,
    #             "aw_message_count": 0,
    #             "ch_message_count": 0,
    #         },
    #         "current_elam_token_type": "elam",
    #         "current_elks_token_type": "elks",
    #     }
    #     cw_response = {"ch": [], "aw": []}
    #     um = {"token_lengths": {"elam": 10, "elks": 10}}
    #     im = {"token_lengths": {"elam": 10, "elks": 10}}
    #     force_reflect = False
    #     result = update_context_window(
    #         cwm_response, cw_response, self.cw_config, um, im, force_reflect
    #     )
    #     self.assertEqual(result[0]["analyze"], False)

    # def test_update_context_window_with_force_reflect(self):
    #     cwm_response = {
    #         "cwm": {
    #             "elam_aw_token_length": 0,
    #             "elks_ch_token_length": 0,
    #             "aw_message_count": 0,
    #             "ch_message_count": 0,
    #         },
    #         "current_elam_token_type": "elam",
    #         "current_elks_token_type": "elks",
    #     }
    #     cw_response = {"ch": [], "aw": []}
    #     um = {"token_lengths": {"elam": 10, "elks": 10}}
    #     im = {"token_lengths": {"elam": 10, "elks": 10}}
    #     force_reflect = True
    #     result = update_context_window(
    #         cwm_response, cw_response, self.cw_config, um, im, force_reflect
    #     )
    #     self.assertEqual(result[0]["analyze"], True)

    def test_synchronize_ddb(self):
        context_window_meta = {"idempotency_lock": True}
        um = {"content": "Hello"}
        im = {"content": "Hi"}
        with patch("LEMChatUtilities.put_items_ddb"):
            result = synchronize_ddb(context_window_meta, um, im)
        self.assertEqual(result["statusCode"], 200)


if __name__ == "__main__":
    unittest.main()
