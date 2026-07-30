import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import ControllerInput


class ControllerInputTests(unittest.TestCase):
    def test_keyboard_forward_command(self):
        controller = ControllerInput()
        controller.pressed_keys = {'s'}
        self.assertEqual(controller.get_command(), (100, 100))

    def test_keyboard_turn_left_command(self):
        controller = ControllerInput()
        controller.pressed_keys = {'a'}
        self.assertEqual(controller.get_command(), (100, 0))

    def test_keyboard_stop_command(self):
        controller = ControllerInput()
        controller.pressed_keys = set()
        self.assertEqual(controller.get_command(), (0, 0))


if __name__ == '__main__':
    unittest.main()
