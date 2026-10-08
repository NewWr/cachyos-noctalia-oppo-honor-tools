"""Wear control for MPRIS players routed to the selected earbuds."""
import json
import os
import re
import shlex
import shutil
import subprocess
import time

MPRIS_PATH = '/org/mpris/MediaPlayer2'
MPRIS_PLAYER = 'org.mpris.MediaPlayer2.Player'
OUT = {'removed', 'in_case'}
ERRORS = (OSError, subprocess.SubprocessError, ValueError, RuntimeError, IndexError)


class PlayerWatch:
    """Keep only playback events for one player; never save bus message contents."""
    def __init__(self, name, owner, metadata):
        self.metadata, self.buffer = metadata, b''
        base = f"path='{MPRIS_PATH}'"
        rules = [f"type='method_call',{base},interface='{MPRIS_PLAYER}',destination='{dest}'"
                 for dest in (name, owner)]
        rules += [f"type='signal',{base},sender='{owner}',interface='{iface}'"
                  for iface in ('org.freedesktop.DBus.Properties', MPRIS_PLAYER)]
        self.process = subprocess.Popen(['busctl', '--user', '--json=short'] +
                                        ['--match=' + rule for rule in rules] + ['monitor'],
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        os.set_blocking(self.process.stdout.fileno(), False)
        time.sleep(.1)
        if self.process.poll() is not None:
            self.close()
            raise RuntimeError('Playback event monitoring unavailable')

    def changed(self):
        if self.process.poll() is not None:
            return True
        while True:
            try:
                chunk = os.read(self.process.stdout.fileno(), 65536)
            except BlockingIOError:
                break
            if not chunk:
                return True
            self.buffer += chunk
        if len(self.buffer) > 1048576:
            return True
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            try:
                event = json.loads(line)
            except ValueError:
                return True
            member = event.get('member')
            if event.get('type') == 'method_call' and member in {
                    'Play', 'Pause', 'PlayPause', 'Stop', 'Next', 'Previous', 'Seek', 'SetPosition', 'OpenUri'}:
                return True
            if member == 'Seeked':
                return True
            if member == 'PropertiesChanged':
                data = event.get('payload', {}).get('data', [])
                if len(data) != 3 or data[0] != MPRIS_PLAYER:
                    continue
                props, invalid = data[1:]
                if any(key in invalid for key in ('PlaybackStatus', 'Metadata', 'Position')):
                    return True
                if ('PlaybackStatus' in props and props['PlaybackStatus'].get('data') != 'Paused'
                        or 'Metadata' in props and props['Metadata'].get('data') != self.metadata
                        or 'Position' in props):
                    return True
        return False

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=.5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=.5)
        self.process.stdout.close()


def routed_processes(mac, sinks, streams, clients):
    """Pulse's native PipeWire clients carry the PID even when stream props do not."""
    if not isinstance(mac, str) or not re.fullmatch(r'[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}', mac):
        return set()
    prefix = 'bluez_output.' + mac.upper().replace(':', '_') + '.'
    target = {str(x['index']) for x in sinks if (x.get('name', '').upper().startswith(prefix.upper())
              or str(x.get('properties', {}).get('api.bluez5.address', '')).upper() == mac.upper())}
    owners = {str(x['index']): x.get('properties', {}) for x in clients}
    result = set()
    for stream in streams:
        if str(stream.get('sink')) not in target:
            continue
        props = stream.get('properties', {})
        owner = owners.get(str(stream.get('client')), {})
        pid = props.get('application.process.id') or owner.get('application.process.id') or owner.get('pipewire.sec.pid')
        try:
            pid = int(pid)
            if pid > 0:
                result.add(pid)
        except (TypeError, ValueError):
            pass
    return result


def same_process_family(stream_pid, player_pid):
    """Browsers can emit audio from a child of their MPRIS-owning process."""
    current, seen = stream_pid, set()
    while current > 1 and current not in seen:
        if current == player_pid:
            return True
        seen.add(current)
        try:
            with open(f'/proc/{current}/stat') as handle:
                current = int(handle.read().rsplit(')', 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
    return False


class DesktopMedia:
    def __init__(self):
        self.owned = {}

    def cancel_resume(self):
        for token in self.owned.values():
            token['watch'].close()
        self.owned.clear()

    def has_resume(self):
        return bool(self.owned)

    def run(self, argv):
        result = subprocess.run(argv, capture_output=True, text=True, timeout=2)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or 'Desktop media command failed')
        return result.stdout

    def json_list(self, kind):
        value = json.loads(self.run(['pactl', '--format=json', 'list', kind]))
        if not isinstance(value, list):
            raise ValueError('Invalid audio route response')
        return value

    def dbus_call(self, bus, interface, method, signature=None, value=None):
        path = '/org/freedesktop/DBus' if bus == 'org.freedesktop.DBus' else MPRIS_PATH
        argv = ['busctl', '--user', 'call', bus, path, interface, method]
        if signature:
            argv += [signature, str(value)]
        return shlex.split(self.run(argv))

    def property(self, owner, name):
        data = shlex.split(self.run(['busctl', '--user', 'get-property', owner, MPRIS_PATH, MPRIS_PLAYER, name]))
        return data[1] if len(data) == 2 else None

    def json_property(self, owner, name):
        return json.loads(self.run(['busctl', '--user', '--json=short', 'get-property',
                                   owner, MPRIS_PATH, MPRIS_PLAYER, name]))['data']

    def watch_player(self, name, owner, metadata):
        return PlayerWatch(name, owner, metadata)

    def route_pids(self, mac):
        return routed_processes(mac, self.json_list('sinks'), self.json_list('sink-inputs'), self.json_list('clients'))

    def check_paused(self, mac):
        """Cancel ownership on user commands, route changes, player replacement or edits."""
        if not self.owned:
            return False
        try:
            pids = self.route_pids(mac)
        except ERRORS:
            self.cancel_resume()
            return False
        for owner, token in list(self.owned.items()):
            try:
                unchanged = (not token['watch'].changed()
                             and self.dbus_call('org.freedesktop.DBus', 'org.freedesktop.DBus',
                                                'GetNameOwner', 's', token['name'])[1] == owner
                             and any(same_process_family(stream_pid, token['pid']) for stream_pid in pids)
                             and self.property(owner, 'PlaybackStatus') == 'Paused'
                             and self.json_property(owner, 'Metadata') == token['metadata']
                             and abs(int(self.json_property(owner, 'Position')) - token['position']) <= 250000)
            except ERRORS:
                unchanged = False
            if not unchanged:
                token['watch'].close()
                self.owned.pop(owner)
        return bool(self.owned)

    def resume_paused(self, mac):
        self.check_paused(mac)
        resumed, failed = [], []
        for owner, token in list(self.owned.items()):
            # Consume before Play: a failed command must never override later user actions.
            self.owned.pop(owner)
            try:
                if token['watch'].changed() or self.property(owner, 'CanPlay') != 'true':
                    continue
                token['watch'].close()
                self.dbus_call(owner, MPRIS_PLAYER, 'Play')
                after = None
                for _ in range(6):
                    after = self.property(owner, 'PlaybackStatus')
                    if after == 'Playing':
                        break
                    time.sleep(.08)
                if after != 'Playing':
                    raise RuntimeError('Player did not confirm resume')
                resumed.append({'name': token['name'], 'pid': token['pid'], 'before': 'Paused', 'after': after})
            except ERRORS as error:
                failed.append({'name': token['name'], 'error': str(error)})
            finally:
                token['watch'].close()
        return {'status': 'resume_failed' if failed else ('resumed' if resumed else 'cancelled'),
                'players': resumed, 'errors': failed, 'resume_armed': False}

    def pause_routed(self, mac):
        self.cancel_resume()
        if not all(shutil.which(x) for x in ['busctl', 'pactl']):
            return {'status': 'unavailable', 'players': []}
        pids = self.route_pids(mac)
        if not pids:
            return {'status': 'no_player', 'players': []}
        names = [line.split()[0] for line in self.run(['busctl', '--user', '--no-pager', 'list']).splitlines()
                 if line.startswith('org.mpris.MediaPlayer2.')]
        paused, failed = [], []
        for name in names:
            try:
                owner = self.dbus_call('org.freedesktop.DBus', 'org.freedesktop.DBus', 'GetNameOwner', 's', name)[1]
                pid = int(self.dbus_call('org.freedesktop.DBus', 'org.freedesktop.DBus', 'GetConnectionUnixProcessID', 's', owner)[1])
                if not any(same_process_family(stream_pid, pid) for stream_pid in pids):
                    continue
                if self.property(owner, 'CanPause') != 'true':
                    continue
                before = self.property(owner, 'PlaybackStatus')
                if before not in ('Playing', 'Paused'):
                    continue
                # Pause is idempotent. Never toggle a player that firmware already paused.
                self.dbus_call(owner, MPRIS_PLAYER, 'Pause')
                after = None
                for _ in range(6):
                    after = self.property(owner, 'PlaybackStatus')
                    if after in ('Paused', 'Stopped'):
                        break
                    time.sleep(.08)
                if after not in ('Paused', 'Stopped'):
                    raise RuntimeError('Player did not confirm pause')
                player = {'name': name, 'pid': pid, 'before': before, 'after': after}
                paused.append(player)
                if before == 'Playing' and after == 'Paused' and self.property(owner, 'CanPlay') == 'true':
                    try:
                        metadata = self.json_property(owner, 'Metadata')
                        position = int(self.json_property(owner, 'Position'))
                        watch = self.watch_player(name, owner, metadata)
                        self.owned[owner] = {'name': name, 'pid': pid, 'metadata': metadata,
                                             'position': position, 'watch': watch}
                    except ERRORS as error:
                        player['resume_error'] = str(error)
            except (OSError, subprocess.SubprocessError, ValueError, RuntimeError, IndexError) as error:
                failed.append({'name': name, 'error': str(error)})
        return {'status': 'failed' if failed else ('paused' if paused else 'no_player'),
                'players': paused, 'errors': failed, 'resume_armed': self.has_resume()}


class WearPlaybackBridge:
    """Debounce wear transitions and resume only this bridge's still-owned pauses."""
    def __init__(self, enabled=True, media=None, clock=time.monotonic, wall=time.time):
        self.enabled = enabled
        self.media = media or DesktopMedia()
        self.clock, self.wall = clock, wall
        self.reset()

    def reset(self):
        self.media.cancel_resume()
        self.previous = None
        self.mac = None
        self.pending = None
        self.handled = False
        self.attempts = 0
        self.resume_pending = None
        self.next_check = 0

    def update(self, state):
        now = self.clock()
        observed = state.get('wear_observed_at', 0)
        if (not self.enabled or state.get('connected') is not True
                or state.get('features', {}).get('wear_detection') is not True
                or not observed or not 0 <= self.wall() - observed <= 20):
            self.reset()
            state['desktop_pause'] = {'enabled': self.enabled, 'status': 'disabled' if not self.enabled else 'waiting'}
            return
        current = (state.get('wear_left'), state.get('wear_right'))
        if any(x not in OUT | {'worn'} for x in current):
            self.reset()
            state['desktop_pause'] = {'enabled': True, 'status': 'waiting'}
            return
        if state.get('mac') != self.mac:
            self.reset()
            self.mac = state.get('mac')
        if self.previous is None:
            if all(x in OUT for x in current):
                self.pending = now
        else:
            if current.count('worn') > self.previous.count('worn'):
                self.pending = None
                self.resume_pending = now
            removed = any(old == 'worn' and new in OUT for old, new in zip(self.previous, current))
            if removed:
                self.resume_pending = None
            if removed and not self.handled and self.pending is None:
                self.pending = now
        self.previous = current
        state.setdefault('desktop_pause', {'enabled': True, 'status': 'ready'})
        if self.media.has_resume() and now >= self.next_check:
            self.next_check = now + 1
            if not self.media.check_paused(self.mac):
                state['desktop_pause'].update({'resume_armed': False, 'status': 'cancelled'})
        if self.resume_pending is not None and now - self.resume_pending >= .5 and 'worn' in current:
            self.handled = False
            self.attempts = 0
            if self.media.has_resume():
                result = self.media.resume_paused(self.mac)
                result.update({'enabled': True, 'timestamp': int(self.wall())})
                state['desktop_pause'] = result
            self.resume_pending = None
        if self.pending is None or now - self.pending < .35:
            return
        try:
            result = self.media.pause_routed(self.mac)
        except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as error:
            result = {'status': 'failed', 'players': [], 'error': str(error)}
        result.update({'enabled': True, 'timestamp': int(self.wall())})
        state['desktop_pause'] = result
        self.attempts += 1
        if result['status'] == 'failed' and self.attempts < 3:
            self.pending = now + .65
        else:
            self.pending = None
            self.handled = True
