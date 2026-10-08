import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from oppo_media import DesktopMedia, PlayerWatch, WearPlaybackBridge, routed_processes

MAC='AA:BB:CC:DD:EE:FF'

class FakeMedia:
 def __init__(self):self.calls=[];self.resumes=[];self.armed=False
 def cancel_resume(self):self.armed=False
 def has_resume(self):return self.armed
 def check_paused(self,mac):return self.armed
 def resume_paused(self,mac):
  self.resumes.append(mac);self.armed=False
  return {'status':'resumed','players':[],'resume_armed':False}
 def pause_routed(self,mac):
  self.calls.append(mac);self.armed=True
  return {'status':'paused','players':[{'name':'org.mpris.MediaPlayer2.Test','before':'Playing','after':'Paused'}],'resume_armed':True}

class WearTests(unittest.TestCase):
 def setUp(self):
  self.now=0;self.media=FakeMedia();self.bridge=WearPlaybackBridge(media=self.media,clock=lambda:self.now,wall=lambda:100+self.now)
  self.state={'connected':True,'mac':MAC,'features':{'wear_detection':True},'wear_left':'worn','wear_right':'worn','wear_observed_at':100}
 def update(self,dt=0,**changes):
  self.now+=dt;self.state.update(changes);self.bridge.update(self.state)
 def test_single_ear_removal_pauses_once_then_rewear_resumes(self):
  self.update();self.update(.1,wear_left='removed');self.update(.2);self.assertEqual(self.media.calls,[])
  self.update(.2);self.assertEqual(self.media.calls,[MAC]);self.assertEqual(self.state['desktop_pause']['status'],'paused')
  self.update(.5,wear_right='removed');self.update(1);self.assertEqual(self.media.calls,[MAC])
  self.update(.1,wear_left='worn');self.update(.6)
  self.assertEqual(self.media.resumes,[MAC])
  self.update(.1,wear_left='removed');self.update(.4)
  self.assertEqual(self.media.calls,[MAC,MAC])
 def test_short_sensor_bounce_does_not_pause(self):
  self.update();self.update(.1,wear_left='removed');self.update(.1,wear_left='worn');self.update(1)
  self.assertEqual(self.media.calls,[])
 def test_disabled_earbud_switch_does_not_pause(self):
  self.update();self.update(.1,wear_left='removed',features={'wear_detection':False});self.update(1)
  self.assertEqual(self.media.calls,[])
 def test_disabled_desktop_setting_does_not_pause(self):
  self.bridge.enabled=False;self.update(wear_left='removed',wear_right='removed');self.update(1)
  self.assertEqual(self.media.calls,[]);self.assertEqual(self.state['desktop_pause']['status'],'disabled')
 def test_unknown_and_stale_reports_do_not_pause(self):
  self.update(wear_left='unknown',wear_right='removed');self.update(1)
  self.update(30,wear_left='removed');self.update(1);self.assertEqual(self.media.calls,[])
 def test_disconnection_does_not_pause_other_outputs(self):
  self.update();self.update(.1,connected=False,wear_left='removed');self.update(1)
  self.assertEqual(self.media.calls,[])
 def test_starting_with_both_removed_pauses_existing_playback(self):
  self.update(wear_left='removed',wear_right='removed');self.update(.4);self.assertEqual(self.media.calls,[MAC])
 def test_single_ear_listening_can_start_with_other_ear_in_case(self):
  self.update(wear_left='in_case',wear_right='worn');self.update(1);self.assertEqual(self.media.calls,[])
 def test_manual_play_while_removed_is_not_repeatedly_overridden(self):
  self.update(wear_left='removed',wear_right='removed');self.update(.4)
  for _ in range(10):self.update(.5)
  self.assertEqual(self.media.calls,[MAC])
 def test_failures_are_reported_and_retries_are_bounded(self):
  self.media.pause_routed=lambda mac: {'status':'failed','players':[]}
  self.update(wear_left='removed',wear_right='removed');self.update(.4);self.update(1);self.update(1);self.update(2)
  self.assertEqual(self.bridge.attempts,3);self.assertTrue(self.bridge.handled)
  self.assertEqual(self.state['desktop_pause']['status'],'failed')
 def test_rewear_bounce_does_not_resume(self):
  self.update();self.update(.1,wear_left='removed');self.update(.4)
  self.update(.1,wear_left='worn');self.update(.1,wear_left='removed');self.update(.4)
  self.assertEqual(self.media.resumes,[])
  self.assertEqual(self.media.calls,[MAC])
  self.update(.1,wear_left='worn');self.update(.6)
  self.assertEqual(self.media.resumes,[MAC])
 def test_disconnect_cancels_pending_resume(self):
  self.update();self.update(.1,wear_left='removed');self.update(.4)
  self.update(.1,connected=False);self.update(.1,connected=True,wear_left='worn');self.update(1)
  self.assertEqual(self.media.resumes,[])
 def test_unknown_wear_cancels_resume(self):
  self.update();self.update(.1,wear_left='removed');self.update(.4)
  self.update(.1,wear_left='unknown');self.update(.1,wear_left='worn');self.update(1)
  self.assertEqual(self.media.resumes,[])
 def test_cancelled_manual_pause_is_not_resumed(self):
  self.update();self.update(.1,wear_left='removed');self.update(.4)
  self.media.armed=False
  self.update(.1,wear_left='worn');self.update(1)
  self.assertEqual(self.media.resumes,[])
 def test_route_uses_client_pid_and_excludes_speaker_stream(self):
  sinks=[{'index':1,'name':'bluez_output.AA_BB_CC_DD_EE_FF.1'},{'index':2,'name':'alsa_output.speaker'}]
  clients=[{'index':44,'properties':{'application.process.id':'12345'}},{'index':55,'properties':{'application.process.id':'22222'}}]
  streams=[{'sink':1,'client':'44','properties':{}},{'sink':2,'client':'55','properties':{}}]
  self.assertEqual(routed_processes(MAC,sinks,streams,clients),{12345})
  self.assertEqual(routed_processes('AA:BB:CC:DD:EE:00',sinks,streams,clients),set())

class FakeWatch:
 def __init__(self):self.edited=False;self.closed=False
 def changed(self):return self.edited
 def close(self):self.closed=True

class FakeDesktop(DesktopMedia):
 def __init__(self,accept=True):
  super().__init__();self.calls=[];self.paused=False;self.accept=accept
  self.metadata={'track':'one'};self.position=123000000;self.owner=':1.50';self.routed=True
  self.watches=[];self.accept_play=True
 def watch_player(self,name,owner,metadata):
  watch=FakeWatch();self.watches.append(watch);return watch
 def json_property(self,owner,name):return self.metadata if name=='Metadata' else self.position
 def json_list(self,kind):
  return {'sinks':[{'index':1,'name':'bluez_output.AA_BB_CC_DD_EE_FF.1'}],'sink-inputs':[{'sink':1 if self.routed else 2,'client':'44','properties':{}}],'clients':[{'index':44,'properties':{'application.process.id':'12345'}}]}[kind]
 def run(self,argv):
  self.calls.append(argv)
  if argv[-1]=='list':return 'org.mpris.MediaPlayer2.Test 1 test\norg.mpris.MediaPlayer2.Speaker 2 other\n'
  if 'GetNameOwner' in argv:return 's "'+self.owner+'"' if argv[-1].endswith('Test') else 's ":1.60"'
  if 'GetConnectionUnixProcessID' in argv:return 'u 12345' if argv[-1]==':1.50' else 'u 22222'
  if argv[-1] in ('CanPause','CanPlay'):return 'b true'
  if argv[-1]=='PlaybackStatus':return 's "Paused"' if self.paused else 's "Playing"'
  if argv[-1]=='Pause':self.paused=self.accept;return ''
  if argv[-1]=='Play':self.paused=not self.accept_play;return ''
  raise AssertionError(argv)

class TransportTests(unittest.TestCase):
 def pause(self,d):
  with patch('oppo_media.shutil.which',return_value='/usr/bin/tool'):
   return d.pause_routed(MAC)
 def test_only_matching_owner_gets_idempotent_pause_and_readback(self):
  d=FakeDesktop()
  with patch('oppo_media.shutil.which',return_value='/usr/bin/tool'):
   result=d.pause_routed(MAC)
  actions=[x for x in d.calls if x[-1]=='Pause']
  self.assertEqual(len(actions),1);self.assertEqual(actions[0][3],':1.50')
  self.assertEqual(result['status'],'paused');self.assertEqual(result['players'][0]['after'],'Paused')
  self.assertFalse(any('PlayPause' in x or 'Play' in x for x in d.calls))
 def test_accepted_dbus_call_without_pause_readback_is_failure(self):
  d=FakeDesktop(False)
  with patch('oppo_media.shutil.which',return_value='/usr/bin/tool'),patch('oppo_media.time.sleep'):
   result=d.pause_routed(MAC)
  self.assertEqual(result['status'],'failed');self.assertEqual(result['players'],[])
 def test_owned_pause_resumes_exact_owner_and_consumes_ownership(self):
  d=FakeDesktop();self.assertTrue(self.pause(d)['resume_armed'])
  self.assertEqual(d.resume_paused(MAC)['status'],'resumed')
  self.assertEqual([x[3] for x in d.calls if x[-1]=='Play'],[':1.50'])
  self.assertFalse(d.has_resume());self.assertTrue(d.watches[0].closed)
  d.resume_paused(MAC);self.assertEqual(len([x for x in d.calls if x[-1]=='Play']),1)
 def test_preexisting_manual_pause_is_never_owned(self):
  d=FakeDesktop();d.paused=True;self.assertFalse(self.pause(d)['resume_armed'])
  d.resume_paused(MAC);self.assertFalse(any(x[-1]=='Play' for x in d.calls))
 def test_manual_command_cancels_resume_even_when_status_is_still_paused(self):
  d=FakeDesktop();self.pause(d);d.watches[0].edited=True
  self.assertEqual(d.resume_paused(MAC)['status'],'cancelled')
  self.assertFalse(any(x[-1]=='Play' for x in d.calls));self.assertTrue(d.watches[0].closed)
 def test_player_track_route_and_position_changes_each_cancel_resume(self):
  for attr,value in [('metadata',{'track':'two'}),('position',124000000),('owner',':1.99'),('routed',False),('paused',False)]:
   with self.subTest(attr=attr):
    d=FakeDesktop();self.pause(d);setattr(d,attr,value)
    self.assertFalse(d.check_paused(MAC));d.resume_paused(MAC)
    self.assertFalse(any(x[-1]=='Play' for x in d.calls));self.assertTrue(d.watches[0].closed)
 def test_resume_failure_is_reported_and_not_retried(self):
  d=FakeDesktop();self.pause(d);d.accept_play=False
  with patch('oppo_media.time.sleep'):
   self.assertEqual(d.resume_paused(MAC)['status'],'resume_failed')
  d.resume_paused(MAC);self.assertEqual(len([x for x in d.calls if x[-1]=='Play']),1)
 def test_missing_event_monitor_preserves_pause_but_does_not_arm_resume(self):
  d=FakeDesktop();d.watch_player=lambda *args: (_ for _ in ()).throw(RuntimeError('no monitor'))
  result=self.pause(d);self.assertEqual(result['status'],'paused');self.assertFalse(result['resume_armed'])

class WatchTests(unittest.TestCase):
 def changed(self,event):
  from types import SimpleNamespace
  watch=PlayerWatch.__new__(PlayerWatch);watch.buffer=b'';watch.metadata={'track':'one'}
  watch.process=SimpleNamespace(poll=lambda:None,stdout=SimpleNamespace(fileno=lambda:7))
  with patch('oppo_media.os.read',side_effect=[json.dumps(event).encode()+b'\n',BlockingIOError()]):
   return watch.changed()
 def test_idempotent_manual_pause_is_detected(self):
  self.assertTrue(self.changed({'type':'method_call','member':'Pause'}))
 def test_own_paused_notification_does_not_cancel(self):
  self.assertFalse(self.changed({'type':'signal','member':'PropertiesChanged','payload':{'data':['org.mpris.MediaPlayer2.Player',{'PlaybackStatus':{'data':'Paused'}},[]]}}))
 def test_playing_signal_cancels_even_if_it_was_paused_again_between_polls(self):
  self.assertTrue(self.changed({'type':'signal','member':'PropertiesChanged','payload':{'data':['org.mpris.MediaPlayer2.Player',{'PlaybackStatus':{'data':'Playing'}},[]]}}))
 def test_metadata_changes_and_seek_cancel_resume(self):
  self.assertTrue(self.changed({'type':'signal','member':'PropertiesChanged','payload':{'data':['org.mpris.MediaPlayer2.Player',{'Metadata':{'data':{'track':'two'}}},[]]}}))
  self.assertTrue(self.changed({'type':'signal','member':'Seeked'}))

if __name__=='__main__':unittest.main()
