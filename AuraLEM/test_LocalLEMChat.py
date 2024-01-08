import unittest
from LocalLEMTest import ref_run_test

# Error list
# 1. If the lambda function is cancelled halfway through then the lock is not released. In this case the
# update_idempotency_lock() function should be called at the beginning of the lambda function
# to manually release the lock.


class TestLocalLEMTest(unittest.TestCase):
    def test_long_string(self):
        # Define your inputs and expected outputs
        um = "test_um" * 1000  # very long user message
        force_reflect = False
        expected_output = {
            "statusCode": 400,
            "body": '"User message exceed max token length."',
        }

        # Call your function with the inputs
        result = ref_run_test(um, force_reflect)

        # Assert that the result equals the expected output
        self.assertEqual(result, expected_output)

    def test_empty_string(self):
        # Define your inputs and expected outputs
        um = ""  # empty user message
        force_reflect = False
        expected_output = {
            "statusCode": 400,
            "body": '"User message is empty, and force reflect is false."',
        }

        # Call your function with the inputs
        result = ref_run_test(um, force_reflect)

        # Assert that the result equals the expected output
        self.assertEqual(result, expected_output)

    def test_empty_string_true(self):
        # Define your inputs and expected outputs
        um = ""  # empty user message
        force_reflect = True
        expected_output = {
            "statusCode": 200,
            "body": '"Communication Instance completed successfully. Data unlocked."',
        }

        # Call your function with the inputs
        result = ref_run_test(um, force_reflect)

        # Assert that the result equals the expected output
        self.assertEqual(result, expected_output)

    def test_normal_input(self):
        # Define your inputs and expected outputs
        um = "test_um"
        force_reflect = False
        expected_output = {
            "statusCode": 200,
            "body": '"Communication Instance completed successfully. Data unlocked."',
        }

        # Call your function with the inputs
        result = ref_run_test(um, force_reflect)

        # Assert that the result equals the expected output
        self.assertEqual(result, expected_output)


if __name__ == "__main__":
    unittest.main()
