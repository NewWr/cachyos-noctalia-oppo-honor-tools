import importlib.util
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from oppo_protocol import (FrameDecoder, apply_frame, decode_noise, decode_equalizers,
                           encode_equalizer, capability_state, make_frame)
from oppo_runtime import Session

FIXTURE = json.loads((ROOT / 'tests/fixtures.json').read_text())
RESPONSES = {q['name']: bytes.fromhex(q['matching_response']) for q in FIXTURE['queries']}

class FakeSocket:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.sent = []
    def settimeout(self, value): pass
    def sendall(self, value): self.sent.append(value)
    def recv(self, size):
        if not self.chunks: raise socket.timeout()
        return self.chunks.pop(0)

class FeatureTests(unittest.TestCase):
    def test_fragmented_coalesced_frames_with_header_byte_in_payload(self):
        payload = b'\x00\x03\x01\xaa\x02\x64\x03\x64'
        stream = make_frame(0x8106, 3, payload) + make_frame(0x8404, 4, b'\x00')
        decoder = FrameDecoder()
        frames = []
        for index in range(0, len(stream), 3): frames.extend(decoder.feed(stream[index:index+3]))
        self.assertEqual(frames, [(0x8106, 3, payload), (0x8404, 4, b'\x00')])

    def test_bad_length_header_recovers(self):
        frame = bytearray(make_frame(0x810F, 1, b'\x00\x04'))
        frame[1] = 99
        self.assertEqual(FrameDecoder().feed(bytes(frame) + make_frame(0x810F, 2, b'\x00\x00')),
                         [(0x810F, 2, b'\x00\x00')])

    def test_partial_battery_reports_merge_and_zero_is_valid(self):
        state = {'battery_left': 80, 'battery_right': 81, 'battery_case': 50}
        apply_frame(state, 0x0204, b'\x01\x01\x03\x00')
        self.assertEqual(state['battery_case'], 0)
        self.assertEqual(state['battery_left'], 80)
        self.assertEqual(state['battery_right'], 81)

    def test_truncated_battery_report_keeps_state(self):
        state = {'battery_left': 80}
        apply_frame(state, 0x8106, b'\x00\x02\x01\x64\x02')
        self.assertEqual(state, {'battery_left': 80})

    def test_battery_payload_cannot_be_interpreted_as_noise(self):
        state = {'noise_mode': 'anc'}
        apply_frame(state, 0x0204, b'\x01\x02\x01\x01\x02\x64')
        self.assertEqual(state['noise_mode'], 'anc')

    def test_all_noise_modes_and_smart_realtime(self):
        for raw, setting in [('1000','deep'),('2000','medium'),('4000','light'),('8000','smart'),
                             ('0008','adaptive'),('0001','transparency'),('0800','off')]:
            self.assertEqual(decode_noise(bytes.fromhex('000101'+raw))['noise_setting'], setting)
        observed = decode_noise(bytes.fromhex('0004012000'))
        self.assertEqual(observed['noise_setting'], 'smart')
        self.assertEqual(observed['noise_realtime'], 'medium')

    def test_strict_feature_pairs_and_missing_values(self):
        state = {}
        apply_frame(state, 0x810D, RESPONSES['features'])
        self.assertIs(state['dual_device'], False)
        self.assertIs(state['spatial_sound'], True)
        self.assertEqual(state['game_feature'], 6)
        apply_frame(state, 0x810D, b'\x00\x00')
        self.assertEqual(state['features'], {})

    def test_real_equalizer_signed_gains_and_every_truncation(self):
        payload = RESPONSES['all_eq']
        eq = decode_equalizers(payload)
        self.assertEqual(eq[0]['name'], '测试')
        self.assertEqual([b['gain'] for b in eq[0]['bands']], [-3,4,6,-1,5,0])
        for size in range(len(payload)): self.assertIsNone(decode_equalizers(payload[:size]))

    def test_eq_encoder_rejects_out_of_range_and_oversized_names(self):
        eq = decode_equalizers(RESPONSES['all_eq'])[0]
        eq['bands'][0]['gain'] = 7
        with self.assertRaises(ValueError): encode_equalizer(2, eq)
        eq['bands'][0]['gain'] = -3
        eq['name'] = '耳' * 100
        with self.assertRaises(ValueError): encode_equalizer(2, eq)

    def test_capabilities_require_known_model_and_actual_fields(self):
        state = {'product_id': '068C10', 'command_bitmap': RESPONSES['handshake'][1:].hex()}
        capability_state(state)
        self.assertFalse(state['capabilities']['dual_device'])
        apply_frame(state, 0x810D, RESPONSES['features'])
        capability_state(state)
        self.assertTrue(state['capabilities']['dual_device'])
        state['product_id'] = 'unknown'
        capability_state(state)
        self.assertFalse(state['capabilities']['noise_levels'])

    def session(self, directory, chunks):
        session = Session({'state_file': str(Path(directory)/'state.json')}, '00:00:00:00:00:00')
        session.connection = FakeSocket(chunks)
        session.state.update({'noise_mode': 'anc', 'noise_setting': 'deep',
                              'capabilities': {'noise_levels': True, 'find_device': True},
                              'product_id': '068C10', 'command_bitmap': RESPONSES['handshake'][1:].hex()})
        return session

    def test_rejected_write_never_changes_selected_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            s = self.session(directory, [make_frame(0x8404, 1, b'\x01')])
            result = s.execute('set-anc', 'light')
            self.assertFalse(result['success'])
            self.assertEqual(result['snapshot']['noise_setting'], 'deep')

    def test_write_ack_without_matching_readback_is_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            s = self.session(directory, [make_frame(0x8404, 1, b'\x00'),
                                        make_frame(0x810C, 2, bytes.fromhex('0001012000'))])
            result = s.execute('set-anc', 'light')
            self.assertFalse(result['success'])
            self.assertEqual(result['snapshot']['noise_setting'], 'medium')

    def test_worn_earbuds_cannot_start_find_sound(self):
        with tempfile.TemporaryDirectory() as directory:
            s = self.session(directory, [make_frame(0x8109, 1, bytes.fromhex('000201070207'))])
            s.state.update({'wear_left': 'removed', 'wear_right': 'removed'})
            result = s.execute('find', True, persistent=True)
            self.assertEqual(result['error_code'], 'remove_earbuds')
            self.assertEqual(len(s.connection.sent), 1)
            self.assertEqual(int.from_bytes(s.connection.sent[0][4:6],'little'),0x0109)

    def test_find_deadline_is_set_only_after_an_accepted_command(self):
        with tempfile.TemporaryDirectory() as directory:
            s = self.session(directory, [make_frame(0x8109, 1, bytes.fromhex('000201010201')),
                                        make_frame(0x8400, 2, b'\x00'), make_frame(0x8400, 3, b'\x00')])
            self.assertTrue(s.execute('find', True, persistent=True)['success'])
            self.assertIsNotNone(s.find_deadline)
            self.assertTrue(s.execute('find', False, persistent=True)['success'])
            self.assertIsNone(s.find_deadline)
            self.assertFalse(s.state['finding'])

    def test_find_requires_a_complete_fresh_wear_report(self):
        with tempfile.TemporaryDirectory() as directory:
            s = self.session(directory, [make_frame(0x8109, 1, bytes.fromhex('00010101'))])
            s.state.update({'wear_left':'removed','wear_right':'removed'})
            self.assertEqual(s.execute('find',True,persistent=True)['error_code'],'remove_earbuds')
            self.assertEqual(len(s.connection.sent),1)

    def test_batch_subscription_tag_and_single_event_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            s = self.session(directory, [make_frame(0x8200, 1, bytes.fromhex('0003010203')),
                make_frame(0x8205, 240, bytes.fromhex('0103010002010300')),
                make_frame(0x8201, 240, bytes.fromhex('0002'))])
            s.subscribe()
            self.assertEqual(s.state['registered_notifications'], [1,2,3])
            self.assertIs(s.state['notifications_active'], True)

    def test_game_write_uses_fixed_sequence_and_waits_for_readback(self):
        with tempfile.TemporaryDirectory() as directory:
            s = self.session(directory, [make_frame(0x8403, 240, b'\x00'),
                make_frame(0x810D, 0, bytes.fromhex('00010600')),
                make_frame(0x810D, 0, bytes.fromhex('00010601'))])
            s.state['capabilities']['game_mode'] = True
            from unittest.mock import patch
            with patch('oppo_runtime.time.sleep'):
                result = s.set_feature('game_mode', True)
            self.assertTrue(result['enabled'])
            self.assertEqual(s.connection.sent[0][6], 240)

    def test_removed_earbuds_can_confirm_existing_off_mode_without_write(self):
        with tempfile.TemporaryDirectory() as directory:
            s = self.session(directory, [make_frame(0x810C, 1, bytes.fromhex('0001010800'))])
            s.state.update({'noise_mode':'off','noise_setting':'off','wear_left':'removed','wear_right':'removed'})
            self.assertEqual(s.set_noise('off')['setting'], 'off')
            self.assertEqual(len(s.connection.sent),1)
            self.assertEqual(int.from_bytes(s.connection.sent[0][4:6],'little'),0x010C)

    def test_refresh_request_keeps_command_envelope_for_service(self):
        import contextlib
        import io
        import oppo_ctl
        from unittest.mock import patch
        result = {'success':True,'snapshot':{'connected':True}}
        for command,expected in [(['status'],result['snapshot']),
                (['request','{"action":"status"}'],result)]:
            out = io.StringIO()
            with patch.object(sys,'argv',['oppo_ctl.py',*command]), \
                    patch.object(oppo_ctl,'monitor_request',return_value=result), contextlib.redirect_stdout(out):
                oppo_ctl.main()
            self.assertEqual(json.loads(out.getvalue()),expected)

    def test_configured_address_accepts_auto_and_normalizes_mac(self):
        from oppo_runtime import configured_mac
        self.assertIsNone(configured_mac(''))
        self.assertEqual(configured_mac('02:00:00:00:00:0a'),'02:00:00:00:00:0A')
        for invalid in ['02:00:00:00:00', '$(touch /tmp/file)', False, []]:
            with self.assertRaises(ValueError): configured_mac(invalid)

if __name__ == '__main__': unittest.main()
