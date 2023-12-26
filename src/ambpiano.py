import time

## Midi Driver
import mido

## Led driver
from rpi_ws281x import PixelStrip, Color


# LED strip configuration
LED_COUNT = 81        # Number of leds in the strip
LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
LED_FREQ_HZ = 1000000 # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 128  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

##
# @brief Lowest MIDI note id
LOWEST_NOTE = 21

##
# @brief Highest MIDI note id
HIGHEST_NOTE = 108

##
# @brief Lowest Decay time [s]
LOWEST_DECAY = 1

##
# @brief Highest decay time [s]
HIGHEST_DECAY = 20

#
## @brief Minimum number of cycles for fading-off
FADE_OFF = 10

#
## @brief Cycle
CYCLE = 0.05

def noteToPixel(note, lowestNote=LOWEST_NOTE, highestNote=HIGHEST_NOTE):
    """! Get the pixel that should light up according to the note pressed

        @param[in] note The note pressed

        @return The Pixel ID to light up
        """

    slope = (LED_COUNT - 1) / (highestNote - lowestNote)
    offset = (lowestNote * (LED_COUNT - 1)) / (highestNote - lowestNote)

    return round((note * slope) - offset)


def decay(note, minDecay=LOWEST_DECAY, maxDecay=HIGHEST_DECAY, cycle=CYCLE):
    """! Obtain the decay offset to appy in each cycle
        The idea is that the lower notes take longer to decay than the high pich ones

        @param[in] note The note pressed
        @param[in] minDecay The minimum time to decay [s] (default: LOWEST_DECAY)
        @param[in] maxDecay The maximum time to decay [s] (default: HIGHEST_DECAY)
        @param[in] cycle Cycle time used for interal calculation [s] (default: CYCLE)
    """    

    # Compute function slope
    slope = ((-maxDecay + minDecay)/(88-1))

    # Compute the function offset
    offset = maxDecay

    # Return specific value according to the pixel provided
    return 255/((note * slope + offset)/cycle)



strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)

# Intialize the library (must be called once before other functions).
strip.begin()

for i in range(LED_COUNT):
    strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()


# Midi port
midi = ''

# Get the list o USB ports available
ports = mido.get_input_names()

# Temporal variable to store the ID of the CASIO-MIDI port
# also useful for controlling the operation
casioId = -1

for port in ports:
    if (port.find('CASIO') != -1):
        casioId = ports.index(port)
        break
if (casioId == -1):
    raise Exception("CASIO device not found")
else:
    # In the case the CASIO-MIDI port is found, just open the handler
    midi = mido.open_input(ports[casioId])


pedal = 0
notes = [0] * 88 
leds = [0] * LED_COUNT

# Main loop
while True:

    # List of midi events in queue
    midiEvents = []

    # Flag for continue reading MIDI messages in case of control change
    incomingNote = False;

    # Non-blocking call to get midi events
    for msg in midi.iter_pending():
        ## @todo Format the messages:
        #
        # After control_change=88 there will be a note_on/note_off message
        # control_change=64 is a  pedal_value message
        # Manage only channel = 0
        # Maximum value of pedal is 127, minimum 0
        if (msg.channel == 0):
            if (msg.is_cc() and msg.control == 88):
                incomingNote = True
                continue

            if (incomingNote):
                incomingNote = False
                midiEvents.append([msg.type, msg.note, msg.velocity])

            if (msg.is_cc() and msg.control == 64):
                midiEvents.append(['pedal', msg.value, 0])

    if (len(midiEvents) > 0):

        # Find first for the last pedal event of this cycle
        for event in midiEvents:
            if event[0] == 'pedal':
                pedal = event[1]
                       
        for event in midiEvents:
            if event[0] == 'note_on':
                notes[event[1] - LOWEST_NOTE] = 255 # event[2]
            elif event[0] == 'note_off':
                notes[event[1] - LOWEST_NOTE] = FADE_OFF

    # Build the LEDs array
    for i in range(88):
        # Decay    
        if (notes[i] > 0):
            notes[i] = max(round(notes[i] - (decay(i))), 0)
            
        if (pedal > 0):
            if (notes[i] > FADE_OFF):    
                leds[noteToPixel(i, 0, HIGHEST_NOTE-LOWEST_NOTE)] = notes[i]
        else:
            leds[noteToPixel(i, 0, HIGHEST_NOTE-LOWEST_NOTE)] = notes[i]


    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, leds[i], 0))

    strip.show()
    time.sleep(CYCLE)
