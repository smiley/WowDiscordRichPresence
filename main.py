from PIL import ImageGrab
import pypresence
import time
import logging
import traceback

from data import large_image_instanceMapID, name_classID, large_image_mapID, large_image_zone, \
    small_image_classID, size_difficultyID

# config
discord_client_id = '429296102727221258'  # Put your Client ID here
msg_header = "ARW"
max_msg_len = 900
MAX_LEVEL = 110

# logging
logger = logging.getLogger('wowdrp')
hdlr = logging.FileHandler('wowdrp.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
hdlr.setLevel(logging.INFO)

def tweak_color_channel_by_offset(color, offset):
    if color == 0:
        return color
        
    return color + offset

def get_channel_index(channel):
    if channel.lower() == 'r':
        return 0
    elif channel.lower() == 'g':
        return 1
    elif channel.lower() == 'b':
        return 2
    else:
        raise ValueError("Unknown color channel: {0}".format(channel))

# NOTE: Returns separators as well!
def get_next_character(pixels, channel, last_char=None):
    channel_index = get_channel_index(channel)

    if last_char is None:
        return (pixels[0][channel_index], 0)
        
    last_char_value = last_char[0]
    last_char_index = last_char[1]
        
    i = last_char_index + 1
    while i < len(pixels):
        value = pixels[i][channel_index]
        if value == last_char_value:
            i = i + 1
            continue
        else:
            return (value, i)
            
    return None

def iterate_pixels(pixels, channel):
    line = ""
    wait_for_null = False
    channel_index = get_channel_index(channel)

    for p in pixels:
        channels = p
        character_ordinal = channels[channel_index]
        if character_ordinal == 0:
            # We've reached a null separator; look for a character again
            wait_for_null = False
        elif wait_for_null is False:
            # Cool, this is a character. Due to UI Scale, this character may repeat immediately
            # afterwards. Thus, wait for a null separator before continuing to parse.
            line += chr(character_ordinal)
            wait_for_null = True

    return line
    
def calibrate_brightness_offset(pixels):
    # The first expected character is NULL. If it's already null, there's
    # no calibration needed.
    if pixels[0][0] == 0:
        # Already at null.
        return pixels
        
    first_char = get_next_character(pixels, 'r')
    next_char = get_next_character(pixels, 'r', first_char)[0]
    
    # first_char is expected to be NULL, while next_char is expected to be
    # msg_header[0]. If the first ISN'T null, the user upped their brightness
    # and changed the meaning of some colours. Use the offset on msg_header[0]
    # to tweak all the array's values. (Since the user can also LOWER
    # their brightness)
    offset = ord(msg_header[0]) - next_char
    new_pixels = []
    
    for pixel in pixels:
        new_pixel = tuple(map(lambda x: tweak_color_channel_by_offset(x, offset), pixel))
        new_pixels.append(new_pixel)
        
    return new_pixels

# reads message character by character using all 3 color channels
def parse_pixels(pixels):
    pixels = calibrate_brightness_offset(pixels)

    msg = ""
    msg += iterate_pixels(pixels, 'r')
    msg += iterate_pixels(pixels, 'g')
    msg += iterate_pixels(pixels, 'b')
    logger.info("Raw message[{0}]: {1}".format(len(msg), msg))
    return msg


# gets pixel data from screenshot
def read_screen():
    img = ImageGrab.grab(bbox=(0, 0, max_msg_len / 3, 1))
    pixels = list(img.getdata())
    return pixels


def get_msg():
    px = read_screen()
    msg = parse_pixels(px)
    if msg[:3] == msg_header:
        logger.info("Message is valid")
        return msg[3:]
    else:
        logger.info("Message is junk")
        return None


def parse_msg(msg):
    ms = msg.split("|")
    i = 0
    data = dict()
    # basic
    data["name"] = ms[i]; i+=1
    data["realm"] = ms[i]; i+=1
    data["classID"] = int(ms[i]); i+=1
    data["race"] = ms[i]; i+=1
    data["level"] = int(ms[i]); i+=1
    data["itemLevel"] = int(float(ms[i])); i+=1
    # location
    data["mapAreaID"] = int(ms[i]); i+=1
    data["instanceMapID"] = int(ms[i]); i+=1
    data["zone"] = ms[i]; i+=1
    data["miniMapZoneText"] = ms[i]; i+=1
    # group
    data["numGroupMembers"] = int(ms[i]); i+=1
    data["maxGroupMembers"] = int(ms[i]); i+=1
    data["difficultyID"] = int(ms[i]); i+=1
    # status
    data["status"] = ms[i]; i+=1
    data["timeStarted"] = int(float(ms[i])); i+=1
    logger.info("Successfully parsed message into dict")
    return data


def format_state(data):
    return data["status"]


def format_details(data):
    return "%s - %s" % (data["name"], data["realm"])


def format_large_text(data):
    if data["classID"] == 4 and data["level"] > 97 and data["miniMapZoneText"] in large_image_zone:
        return "The Hall of Shadows"
    return data["zone"]


def format_large_image(data):
    try:  # check for rogue class hall
        if data["classID"] == 4 and data["level"] > 97:
            return large_image_zone[data["miniMapZoneText"]]
    except: pass
    try:  # check for other class halls
        if data["level"] > 97:
            return large_image_zone[data["zone"]]
    except: pass
    try:  # check for cities
        return large_image_mapID[data["mapAreaID"]]
    except: pass
    try:  # check for dungeons and raids
        return large_image_instanceMapID[data["instanceMapID"]]
    except: pass
    # default
    return "cont_azeroth"


def format_small_text(data):
    race = data["race"]
    if race == "NightElf":
        race = "Night Elf"
    elif race == "BloodElf":
        race = "Blood Elf"
    elif race == "VoidElf":
        race = "Void Elf"
    elif race == "LightforgedDraenei":
        race = "Lightforged Draenei"
    elif race == "HighmountainTauren":
        race = "Highmountain Tauren"
    level = data["level"]
    if level == MAX_LEVEL:
        level = "ilvl " + str(data["itemLevel"])
    return "%s %s %s" % (str(level), race, name_classID[data["classID"]])


def format_small_image(data):
    try:
        return small_image_classID[data["classID"]]
    except:
        logger.error("Invalid class for small icon")
        return "icon_full"


def format_start(data):
    if data["timeStarted"] != -1:
        return data["timeStarted"]
    return None


def format_party_size(data):
    if data["numGroupMembers"] == 0 or data["maxGroupMembers"] == 0:
        return None
    return [data["numGroupMembers"], data["maxGroupMembers"]]


def start_drp():
    rpc = pypresence.Presence(discord_client_id)
    rpc.connect()
    last_msg = ""
    while True:  # The presence will stay on as long as the program is running
        try:
            msg = get_msg()
            if msg and last_msg != msg:
                print("Msg: " + msg)
                last_msg = msg
                data = parse_msg(msg)
                rpc.update(state=format_state(data),
                                 details=format_details(data),
                                 start=format_start(data),
                                 large_image=format_large_image(data),
                                 large_text=format_large_text(data),
                                 small_image=format_small_image(data),
                                 small_text=format_small_text(data),
                                 party_size=format_party_size(data))
                logger.info("Successfully updated discord activity")
        except Exception:
            logger.exception("Exception in Main Loop")
            logger.exception("Exception: " + traceback.format_exc())
            print("Exception in Main Loop")
            print("Exception: " + traceback.format_exc())
        time.sleep(1)

start_drp()
