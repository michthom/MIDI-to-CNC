class format:
    SingleTrack = 0
    MultipleTracksSync = 1
    MultipleTracksAsync = 2

class voice:
    NoteOff = 0x80
    NoteOn = 0x90
    PolyphonicKeyPressure = 0xA0 # note aftertouch
    ControllerChange = 0xB0
    ProgramChange = 0xC0
    ChannelPressure = 0xD0
    PitchBend = 0xE0

class meta:
    FileMetaEvent = 0xFF
    SMPTEOffsetMetaEvent = 0x54
    SystemExclusive = 0xF0
    SystemExclusivePacket = 0xF7
    SequenceNumber = 0x00
    TextMetaEvent = 0x01
    CopyrightMetaEvent = 0x02
    TrackName = 0x03
    InstrumentName = 0x04
    Lyric = 0x05
    Marker = 0x06
    CuePoint = 0x07
    ChannelPrefix = 0x20
    MidiPort = 0x21
    EndTrack = 0x2F
    SetTempo = 0x51
    TimeSignature = 0x58
    KeySignature = 0x59
    SequencerSpecificMetaEvent = 0x7F
