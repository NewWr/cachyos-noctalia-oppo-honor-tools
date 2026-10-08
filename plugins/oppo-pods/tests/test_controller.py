import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

source = Path(__file__).resolve().parents[1] / 'scripts/oppo_ctl.py'
spec = importlib.util.spec_from_file_location('controller', source)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)

class FakeSocket:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.closed = False
    def settimeout(self, timeout): pass
    def sendall(self, data): pass
    def recv(self, size):
        if not self.chunks: raise socket.timeout()
        return self.chunks.pop(0)
    def close(self): self.closed = True

class ControllerTests(unittest.TestCase):
    def test_fragmented_response_after_unsolicited_report(self):
        report = bytes.fromhex('aa0c00000402ff05000301010800')
        reply = bytes.fromhex('aa080000048402010000')
        connection = FakeSocket([report + reply[:4], reply[4:8], reply[8:]])
        self.assertEqual(controller.read_response(connection, 0x8404, 2), b'\x00')

    def check_failure_keeps_cache(self, chunks):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'state.json'
            original = json.dumps({'connected': True, 'noise_mode': 'anc'})
            state.write_text(original)
            connection = FakeSocket(chunks)
            with patch.object(controller, 'STATE_FILE', str(state)), patch.object(controller, 'connect_rfcomm', return_value=(connection, 15)):
                result = controller.set_anc_mode('AA:BB:CC:DD:EE:FF', 'transparency')
            self.assertFalse(result['success'])
            self.assertNotIn('mode', result)
            self.assertEqual(state.read_text(), original)
            self.assertTrue(connection.closed)

    def test_rejected_command_keeps_confirmed_cache(self):
        self.check_failure_keeps_cache([
            controller.make_frame(0x8100, 1, b'\x00'),
            controller.make_frame(0x8404, 2, b'\x01'),
        ])

    def test_mode_mismatch_keeps_confirmed_cache(self):
        self.check_failure_keeps_cache([
            controller.make_frame(0x8100, 1, b'\x00'),
            controller.make_frame(0x8404, 2, b'\x00'),
            bytes.fromhex('aa0c00000c810305000001011000'),
        ])

    def test_missing_confirmation_keeps_confirmed_cache(self):
        self.check_failure_keeps_cache([
            controller.make_frame(0x8100, 1, b'\x00'),
            controller.make_frame(0x8404, 2, b'\x00'),
        ])

if __name__ == '__main__':
    unittest.main()
