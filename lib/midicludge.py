import midi
from collections import namedtuple
from constants import *

NoteDetails = namedtuple('NoteDetails',['note_no','velocity'])
TempoDetails = namedtuple('TempoDetails',['tempo'])
MetaDetails = namedtuple('MetaDetails',['text'])

class Event:
  def __init__(self,event):
    self.event = event
    self.type = self.event.statusmsg
    self.delta = self.event.tick
    self.absolute = None
    if isinstance(self.event,midi.Event):
      self.channel = self.event.channel
    elif isinstance(self.event,midi.MetaEvent):
      self.type=self.event.metacommand
    
    if isinstance(self.event,midi.NoteEvent):
      self.detail = NoteDetails(note_no=self.event.get_pitch(),velocity=self.event.get_velocity())
    elif isinstance(self.event,midi.SetTempoEvent):
      print("??????",self.type, meta.SetTempo)
      self.detail = TempoDetails(tempo=self.event.get_mpqn())
    elif isinstance(self.event,midi.MetaEventWithText):
      self.detail = MetaDetails(text=self.event.text)

class Track:
  def __init__(self,track):
    self.number=None
    self.track = track
    self.events = list(Event(event) for event in self.track)
    t = 0
    for event in self.events:
      t += event.delta
      event.absolute = t

class File:
  def __init__(self,f):
    self.midi = midi.read_midifile(f)
    self.midi.make_ticks_rel()
    self.format = self.midi.format
    self.num_tracks = len(self.midi)
    self.division = self.midi.resolution
    self.tracks = list(Track(track) for track in self.midi)
    for i,track in enumerate(self.tracks):
      track.number = i+1
