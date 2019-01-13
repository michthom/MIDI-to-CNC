#!/usr/bin/env python
# -*- coding: utf-8 -*-
##################################
#
# mid2cnc.py, a MIDI to CNC g-code converter
# by T. R. Gipson <drmn4ea at google mail>
# http://tim.cexx.org/?p=633
# Released under the GNU General Public License
#
##################################
#
# Includes midiparser.py module by Sean D. Spencer
# http://seandon4.tripod.com/
# This module is public domain.
#
##################################
#
# Hacked by Miles Lightwood of TeamTeamUSA to support
# the MakerBot Cupcake CNC - < m at teamteamusa dot com >
#
# Modified to handle multiple axes with the MakerBot 
# by H. Grote <hg at pscht dot com>
#
# Further hacked fully into 3 dimensions and generalised
# for multiple CNC machines by Michael Thomson
# <mike at m-thomson dot net>
# 
##################################
#
# More info on:
# http://groups.google.com/group/makerbotmusic
# 
##################################

# Requires Python 2.7
import argparse

import sys
import os.path
import math

# Import the MIDI parser code from the subdirectory './lib'
import midi as midiparser

active_axes = 3

# Specifications for some machines (Need verification!)
#
machines_dict = dict( {
        'cupcake':[
            'metric',                # Units scheme
            11.767, 11.767, 320.000, # Pulses per unit for X, Y, Z axes
            -20.000, -20.000, 0.000, # Safe envelope minimum for X, Y, Z
            20.000, 20.000, 10.000,  # Safe envelope maximum for X, Y, Z
            'XYZ'                    # Default axes and the order for playing
        ],      

        'thingomatic':[
            'metric',
            47.069852, 47.069852, 200.0,
            -20.000, -20.000, 0.000,
            20.000, 20.000, 10.000,
            'XYZ'
        ],

        'shapercube':[
            'metric',
            10.0, 10.0, 320.0,
            0.000, 0.000, 0.000,
            10.000, 10.000, 10.000,
            'XYZ'
        ],

        'ultimaker':[
            'metric',
            47.069852, 47.069852, 160.0,
            0.000, 0.000, 0.000,
            10.000, 10.000, 10.000,
            'XYZ'
        ],

        'custom':[
            'metric',
            10.0, 10.0, 10.0,
            0.000, 0.000, 0.000,
            10.000, 10.000, 10.000,
            'X'
        ]
    })

# Specifications for the systems of units we know about
#
units_dict = dict( {
        # 'scheme':'units', 'abbreviation', scale_to_mm]
        'metric':[
            'millimetre', 'mm', 1.0
        ],
        'imperial':[
            'inch', 'in', 25.4
        ]
    })

# A way to specify any mix of axes in the order you want to voice them
#
axes_dict = dict( {
          'X':[0],       'Y':[1],       'Z':[2],
         'XY':[0,1],    'YX':[1,0],    'XZ':[0,2],
         'ZX':[2,0],    'YZ':[1,2],    'ZY':[2,1],
        'XYZ':[0,1,2], 'XZY':[0,2,1],
        'YXZ':[1,0,2], 'YZX':[1,2,0],
        'ZXY':[2,0,1], 'ZYX':[2,1,0]
    })

def reached_limit(current, distance, direction, min, max):
    # Returns true if the proposed movement will exceed the
    # safe working limits of the machine but the movement is
    # allowable in the reverse direction
    #
    # Returns false if the movement is allowable in the
    # current direction
    # 
    # Aborts if the movement is not possible in either direction

    if ( ( (current + (distance * direction)) < max ) and 
         ( (current + (distance * direction)) > min ) ):
        # Movement in the current direction is within safe limits,
        return False

    elif ( ( (current + (distance * direction)) >= max ) and 
           ( (current - (distance * direction)) >  min ) ):
        # Movement in the current direction violates maximum safe
        # value, but would be safe if the direction is reversed
        return True

    elif ( ( (current + (distance * direction)) <= min ) and 
           ( (current - (distance * direction)) <  max ) ):
        # Movement in the current direction violates minimum safe
        # value, but would be safe if the direction is reversed
        return True

    else:
        # Movement in *either* direction violates the safe working
        # envelope, so abort.
        # 
        print "\n*** ERROR ***"
        print "The current movement cannot be completed within the safe working envelope of"
        print "your machine. Turn on the --verbose option to see which MIDI data caused the"
        print "problem and adjust the MIDI file (or your safety limits if you are confident"
        print "you can do that safely). Aborting."
        exit(2);
    
######################################
# Start of command line parsing code #
######################################

parser = argparse.ArgumentParser(description='Utility to process a Standard MIDI File (*.SMF/*.mid) to "play" it on up to 3 axes of a CNC machine.')

# Show the default values for each argument where available
#
parser.formatter_class = argparse.ArgumentDefaultsHelpFormatter

input=parser.add_argument_group('Input settings')

input.add_argument(
    '-infile', '--infile',
    default = './midi_files/input.mid',
    nargs   = '?',
    type    = argparse.FileType('r'),
    help    = 'the input MIDI filename'
)

input.add_argument(
    '-channels', '--channels',
    default = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    nargs   = '+',
    type    = int,
    choices = xrange(0,16),
    metavar = 'N',
    help    = 'list of MIDI channels you want to scan for event data'
)

input.add_argument(
    '-outfile', '--outfile',
    default = './gcode_files/output.gcode',
    nargs   = '?',
    type    = argparse.FileType('w'),
    help    = 'the output Gcode filename'
)

machines = parser.add_argument_group('Machine settings')

machines.add_argument(
    '-machine', '--machine',
    default = 'cupcake',
    choices = sorted(machines_dict),
    help    = 'sets everything up appropriately for predefined machines, or flags use of custom settings.'
)

custom = parser.add_argument_group('Customised settings')

custom.add_argument(
    '-units', '--units',
    default = 'metric',
    choices = sorted(units_dict),
    help    = 'set the measurement and feed rate units to your preferred scheme.'
)

custom.add_argument(
    '-ppu', '--ppu',
    metavar = ('XXX.XX', 'YYY.YY', 'ZZZ.ZZ'),
    nargs   = 3,
    type    = float,
    help    = 'set arbitrary pulses-per-unit (ppu) for each of the X, Y and Z axes'
)

custom.add_argument(
    '-safemin', '--safemin',
    metavar = ('XXX.XX', 'YYY.YY', 'ZZZ.ZZ'),
    nargs   = 3,
    type    = float,
    help    = 'set minimum edge of the safe envelope for each of the X, Y and Z axes'
)

custom.add_argument(
    '-safemax', '--safemax',
    metavar = ('XXX.XX', 'YYY.YY', 'ZZZ.ZZ'),
    nargs   = 3,
    type    = float,
    help    = 'set maximum edge of the safe envelope for each of the X, Y and Z axes'
)

custom.add_argument(
    '-prefix', '--prefix',
    metavar = 'PRE_FILE',
    nargs   = '?',
    type    = argparse.FileType('r'),
    help    = 'A file containing Gcode to set your machine to a known state before the MIDI is played e.g. homing the axes if supported or required.'
)

custom.add_argument(
    '-postfix', '--postfix',
    metavar = 'POST_FILE',
    nargs   = '?',
    type    = argparse.FileType('r'),
    help    = 'A file containing Gcode to return your machine to a known state after the MIDI is played e.g. homing the axes if supported or required.'
)

output=parser.add_argument_group('Output settings')

output.add_argument(
    '-axes', '--axes',
    default = 'XYZ',
    choices = sorted(axes_dict),
    metavar = 'XYZ',
    help    = 'ordered list of the axes you wish to "play" the MIDI data on. e.g. "X", "ZY", "YZX"'
)

output.add_argument(
    '-transpose', '--transpose',
    metavar = ('Nx', 'Ny', 'Nz'),
    default = ('0', '0', '0'),
    nargs   = 3,
    type    = float,
    help    = 'Transpose each axis N notes up/down, e.g. "12 0 0" will transpose the X axis one octave up the scale.'
)


output.add_argument(
    '-verbose', '--verbose',
    default = False,
    action  = 'store_true',
    help    = 'print verbose output to the terminal')

args = parser.parse_args()

# Get the chosen measurement scheme and the machine definition from the
# dictionaries defined above
#
scheme   =    units_dict.get( args.units   )
settings = machines_dict.get( args.machine )

# Check defaults and scaling of inputs
#
if args.ppu == None:
    # No manual setting of the axis scaling
    # 'scheme':'units', 'abbreviation', scale_to_mm]
    args.ppu    = [ 0, 0, 0 ]
    args.ppu[0] = ( settings[1] * scheme[2] )
    args.ppu[1] = ( settings[2] * scheme[2] )
    args.ppu[2] = ( settings[3] * scheme[2] )

if args.safemin == None:
    # No manual setting of the minimum safe edges
    # 'machine':[units, xppu, yppu, zppu, xmin, ymin, zmin, xmax, ymax, zmax, axes]
    args.safemin    = [ 0, 0, 0 ]
    args.safemin[0] = ( settings[4] / scheme[2] )
    args.safemin[1] = ( settings[5] / scheme[2] )
    args.safemin[2] = ( settings[6] / scheme[2] )

if args.safemax == None:
    # No manual setting of the maximum safe edges
    args.safemax    = [ 0, 0, 0 ]
    args.safemax[0] = ( settings[7] / scheme[2] )
    args.safemax[1] = ( settings[8] / scheme[2] )
    args.safemax[2] = ( settings[9] / scheme[2] )

if os.path.getsize(args.infile.name) == 0:
    msg="Input file %s is empty! Aborting." % os.path.basename(args.infile.name)
    raise argparse.ArgumentTypeError(msg)

print "MIDI input file:\n    %s" % args.infile.name
print "Gcode output file:\n     %s" % args.outfile.name

# Default is Cupcake, so check the others first

if args.machine == 'shapercube':
    print "Machine type:\n    Shapercube"
elif args.machine == 'ultimaker':
    print "Machine type:\n    Ultimaker"
elif args.machine == 'thingomatic':
    print "Machine type:\n    Makerbot Thing-O-Matic"
elif args.machine == 'custom':
    print "Machine type:\n    Bespoke machine"
elif args.machine == 'cupcake':
    print "Machine type:\n    Makerbot Cupcake CNC"

if args.axes != 'XYZ':
   active_axes = len(args.axes)

# Default is metric, so check the non-default case first
print "Units and Feed rates:\n    %s and %s/minute" % ( scheme[0], scheme[1] )
print "Minimum safe limits [X, Y, Z]:\n    [%.3f, %.3f, %.3f]" % (args.safemin[0], args.safemin[1], args.safemin[2])
print "Maximum safe limits [X, Y, Z]:\n    [%.3f, %.3f, %.3f]" % (args.safemax[0], args.safemax[1], args.safemax[2])

print "Pulses per %s [X, Y, Z] axis:\n    [%.3f, %.3f, %.3f]" % (scheme[0], args.ppu[0], args.ppu[1], args.ppu[2])

if active_axes > 1:
    print "Generate Gcode for:\n    %d axes in the order %s" % (active_axes, args.axes)
else:
    print "Generate Gcode for:\n    %s axis only" % args.axes

# Set up an array to allow processing inside the loop to take account of the
# difference in feed rates required on each axis

suppress_comments = 0 # Set to 1 if your machine controller does not handle ( comments )

tempo=None # should be set by your MIDI...

def main(argv):

    x=0.0
    y=0.0
    z=0.0

    x_dir=1.0;
    y_dir=1.0;
    z_dir=1.0;

    midi = midiparser.read_midifile(args.infile.name)
    midi.make_ticks_abs()
    
    print "\nMIDI file:\n    %s" % os.path.basename(args.infile.name)
    print "MIDI format:\n    %d" % midi.format
    print "Number of tracks:\n    %d" % len(midi)
    print "Timing division:\n    %d" % midi.resolution

    noteEventList=[]
    all_channels=set()

    for track in midi:
        channels=set()
        for event in track:
            if isinstance(event,midiparser.SetTempoEvent):
                tempo=event.get_mpqn()
                if args.verbose:
                    print "Tempo change: " + str(event.get_mpqn())
            if (isinstance(event,midiparser.NoteOnEvent) and (event.channel in args.channels)): # filter undesired instruments

                if event.channel not in channels:
                    channels.add(event.channel)

                # NB: looks like some use "note on (vel 0)" as equivalent to note off, so check for vel=0 here and treat it as a note-off.
                if event.velocity > 0:
                    noteEventList.append([event.tick, 1, event.pitch, event.velocity])
                    if args.verbose:
                        print("Note on  (time, channel, note, velocity) : %6i %6i %6i %6i" % (event.tick, event.channel, event.pitch, event.velocity) )
                else:
                    noteEventList.append([event.tick, 0, event.pitch, event.velocity])
                    if args.verbose:
                        print("Note off (time, channel, note, velocity) : %6i %6i %6i %6i" % (event.tick, event.channel, event.pitch, event.velocity) )
            if isinstance(event,midiparser.NoteOffEvent) and (event.channel in args.channels):

                if event.channel not in channels:
                    channels.add(event.channel)

                noteEventList.append([event.tick, 0, event.pitch, event.velocity])
                if args.verbose:
                    print("Note off (time, channel, note, velocity) : %6i %6i %6i %6i" % (event.tick, event.channel, event.pitch, event.velocity) )
            if isinstance(event,midiparser.TrackNameEvent): 
                if args.verbose:
                    print event.text.strip()
#            if event.type == midiparser.meta.CuePoint: 
#                if args.verbose:
#                    print event.detail.text.strip()
#            if event.type == midiparser.meta.Lyric: 
#                if args.verbose:
#                    print event.detail.text.strip()
                #if event.type == midiparser.meta.KeySignature: 
                # ...

        # Finished with this track
        if len(channels) > 0:
            msg=', ' . join(['%2d' % ch for ch in sorted(channels)])
            # print 'Processed track %d, containing channels numbered: [%s ]' % (track.number, msg)
            all_channels = all_channels.union(channels)

    # List all channels encountered
    if len(all_channels) > 0:
        msg=', ' . join(['%2d' % ch for ch in sorted(all_channels)])
        print 'The file as a whole contains channels numbered: [%s ]' % msg

    # We now have entire file's notes with abs time from all channels
    # We don't care which channel/voice is which, but we do care about having all the notes in order
    # so sort event list by abstime to dechannelify

    noteEventList.sort()
    # print noteEventList
    # print len(noteEventList)

    last_time=-0
    active_notes={} # make this a dict so we can add and remove notes by name

    # Start the output to file...
    # It would be nice to add some metadata here, such as who/what generated the output, what the input file was,
    # and important playback parameters (such as steps/in assumed and machine envelope).
    # Unfortunately G-code comments are not 100% standardized...

    if suppress_comments == 0:
        args.outfile.write ("( Input file was " + os.path.basename(args.infile.name) + " )\n")
        
    # Code for everyone
    if args.units == 'imperial':
        args.outfile.write ("G20 (Imperial Hegemony Forevah!)\n")
    elif args.units == 'metric':
        args.outfile.write ("G21 (Metric FTW)\n")
    else:
        print "\nWARNING: Gcode metric/imperial setting undefined!\n"

    args.outfile.write ("G90 (Absolute posiitioning)\n")
    args.outfile.write ("G92 X0 Y0 Z0 (set origin to current position)\n")
    args.outfile.write ("G0 X0 Y0 Z0 F2000.0 (Pointless move to origin to reset feed rate to a sane value)\n")

    # Handle the prefix Gcode, if present
    if args.prefix != None:
        # Read file and dump to outfile
        for line in args.prefix:
            args.outfile.write (line) 

    for note in noteEventList:
        # note[timestamp, note off/note on, note_no, velocity]
        if last_time < note[0]:
        
            freq_xyz=[0,0,0]
            feed_xyz=[0,0,0]
            distance_xyz=[0,0,0]
            duration=0

            # "i" ranges from 0 to "the number of active notes *or* the number of active axes, 
            # whichever is LOWER". Note that the range operator stops
            # short of the maximum, so this means 0 to 2 at most for a 3-axis machine.
            # E.g. only look for the first few active notes to play despite what
            # is going on in the actual score.

            for i in range(0, min(len(active_notes.values()), active_axes)): 

                # Which axis are should we be writing to?
                # 
                j = axes_dict.get(args.axes)[i]

                # Debug
                # print"Axes %s: item %d is %d" % (axes_dict.get(args.axes), i, j)

                # Sound higher pitched notes first by sorting by pitch then indexing by axis
                #
                nownote=sorted(active_notes.values(), reverse=True)[i]

                # MIDI note 69     = A4(440Hz)
                # 2 to the power (69-69) / 12 * 440 = A4 440Hz
                # 2 to the power (64-69) / 12 * 440 = E4 329.627Hz
                #
                freq_xyz[j] = pow(2.0, (nownote-69 + int(args.transpose[j]))/12.0)*440.0

                # Here is where we need smart per-axis feed conversions
                # to enable use of X/Y *and* Z on a Makerbot
                #
                # feed_xyz[0] = X; feed_xyz[1] = Y; feed_xyz[2] = Z;
                #
                # Feed rate is expressed in mm / minutes so 60 times
                # scaling factor is required.
                
                feed_xyz[j] = ( freq_xyz[j] * 60.0 ) / args.ppu[j]

                # Get the duration in seconds from the MIDI values in divisions, at the given tempo
                duration = ( ( ( note[0] - last_time ) + 0.0 ) / ( midi.resolution + 0.0 ) * ( tempo / 1000000.0 ) )

                # Get the actual relative distance travelled per axis in mm
                distance_xyz[j] = ( feed_xyz[j] * duration ) / 60.0 

            # Now that axes can be addressed in any order, need to make sure
            # that all of them are silent before declaring a rest is due.
            if distance_xyz[0] + distance_xyz[1] + distance_xyz[2] > 0: 
                # At least one axis is playing, so process the note into
                # movements
                #
                combined_feedrate = math.sqrt(feed_xyz[0]**2 + feed_xyz[1]**2 + feed_xyz[2]**2)
                
                if args.verbose:
                    print "Chord: [%7.3f, %7.3f, %7.3f] in Hz for %5.2f seconds at timestamp %i" % (freq_xyz[0], freq_xyz[1], freq_xyz[2], duration, note[0])
                    print " Feed: [%7.3f, %7.3f, %7.3f] XYZ %s/min and %8.2f combined" % (feed_xyz[0], feed_xyz[1], feed_xyz[2], scheme[1], combined_feedrate )
                    print "Moves: [%7.3f, %7.3f, %7.3f] XYZ relative %s" % (distance_xyz[0], distance_xyz[1], distance_xyz[2], scheme[0] )

                # Turn around BEFORE crossing the limits of the 
                # safe working envelope
                #
                if reached_limit( x, distance_xyz[0], x_dir, args.safemin[0], args.safemax[0] ):
                    x_dir = x_dir * -1
                x = (x + (distance_xyz[0] * x_dir))
               
                if reached_limit( y, distance_xyz[1], y_dir, args.safemin[1], args.safemax[1] ):
                    y_dir = y_dir * -1
                y = (y + (distance_xyz[1] * y_dir))
               
                if reached_limit( z, distance_xyz[2], z_dir, args.safemin[2], args.safemax[2] ):
                    z_dir = z_dir * -1
                z = (z + (distance_xyz[2] * z_dir))
               
                if args.verbose:
                    print "G01 X%.10f Y%.10f Z%.10f F%.10f\n" % (x, y, z, combined_feedrate)
                args.outfile.write("G01 X%.10f Y%.10f Z%.10f F%.10f\n" % (x, y, z, combined_feedrate))

            else:
                if duration > 0:
                    # Handle 'rests' in addition to notes.
                    # How standard is this pause gcode, anyway?
                    args.outfile.write("G04 P%0.4f\n" % duration )
                    if args.verbose:
                        print "Pause for %.2f seconds" % duration
                        print "G04 P%0.4f\n" % duration

            # finally, set this absolute time as the new starting time
            last_time = note[0]

        if note[1]==1: # Note on
            if active_notes.has_key(note[2]):
                if args.verbose:
                    print "Warning: tried to turn on note already on!"
            else:
                # key and value are the same, but we don't really care.
                active_notes[note[2]]=note[2]
        elif note[1]==0: # Note off
            if(active_notes.has_key(note[2])):
                active_notes.pop(note[2])
            else:
                if args.verbose:
                    print "Warning: tried to turn off note that wasn't on!"

    # Handle the postfix Gcode, if present
    if args.postfix != None:
        # Read file and dump to outfile
        for line in args.postfix:
            args.outfile.write (line) 
    
if __name__ == "__main__":
    main(sys.argv)
