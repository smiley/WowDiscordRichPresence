from PIL import ImageGrab
import pypresence
import time
import logging

# config
discord_client_id = '429296102727221258'  # Put your Client ID here
msg_header = "ARW"
max_msg_len = 900

# data
class_names = {
    0: "None",
    1: "Warrior",
    2: "Paladin",
    3: "Hunter",
    4: "Rogue",
    5: "Priest",
    6: "Death Knight",
    7: "Shaman",
    8: "Mage",
    9: "Warlock",
    10: "Monk",
    11: "Druid",
    12: "Demon Hunter",
}

class_images = {
    0: "icon_full",
    1: "class_warrior",
    2: "class_paladin",
    3: "class_hunter",
    4: "class_rogue",
    5: "class_priest",
    6: "class_deathknight",
    7: "class_shaman",
    8: "class_mage",
    9: "class_warlock",
    10: "class_monk",
    11: "class_druid",
    12: "class_demonhunter",
}

continent_names = {
    -1: "Unknown",
    0: "Azeroth",
    1: "Kalimdor",
    2: "Eastern Kingdoms",
    3: "Outland",
    4: "Northrend",
    5: "Maelstrom",
    6: "Pandaria",
    7: "Draenor",
    8: "Broken Isles",
    9: "Argus",
}

continent_images = {
    -1: "default",
    0: "default",
    1: "kalimdor",
    2: "easternkingdoms",
    3: "outland",
    4: "northrend",
    5: "maelstrom",
    6: "pandaria",
    7: "draenor",
    8: "brokenisles",
    9: "argus",
}

city_images = {
    301: "stormwind",
    321: "orgrimmar",
    341: "ironforge",
    362: "thunderbluff",
    381: "darnassus",
    382: "undercity",
    471: "exodar",
    480: "silvermoon",
    481: "shattrath",
    504: "dalaran",
    903: "shrineoftwomoons",
    905: "shrineofsevenstars",
    971: "garrison_alliance",
    976: "garrison_horde",
    1009: "stormshield",
    1011: "warspear",
    1014: "dalaran_legion",
}

classhall_images = {
    "Trueshot Lodge": "ch_hunter",
    "Acherus: The Ebon Hold": "ch_deathknight",
    "Mardum, the Shattered Abyss": "ch_demonhunter",
    "The Dreamgrove": "ch_druid",
    "Hall of the Guardian": "ch_mage",
    "The Wandering Isle": "ch_monk",
    "Light's Hope Chapel": "ch_paladin",
    "Netherlight Temple": "ch_priest",
    "The Maelstrom": "ch_shaman",
    "Dreadscar Rift": "ch_warlock",
    "Skyhold": "ch_warrior",
    # mini map texts
    "The Hall of Shadows": "ch_rogue",
    "Uncrowned Vault": "ch_rogue",
    "Den of Thieves": "ch_rogue",
}

# reads message character by character using all 3 color channels
def parse_pixels(pixels):
    msg = ""
    for p in pixels:
        r, g, b = p
        if r != 0:
            msg += chr(r)
    for p in pixels:
        r, g, b = p
        if g != 0:
            msg += chr(g)
    for p in pixels:
        r, g, b = p
        if b != 0:
            msg += chr(b)
    return msg

# gets pixel data from screenshot
def read_screen():
    img = ImageGrab.grab(bbox=(0, 0, max_msg_len / 3, 1))
    pixels = list(img.getdata())
    return pixels

def get_msg():
    px = read_screen()
    msg = parse_pixels(px)
    if msg[:3] != msg_header:
        return None
    return msg[3:]

def parse_msg(msg):
    ms = msg.split("|")
    return {
        "name": ms[0],
        "realm": ms[1],
        "zone": ms[2],
        "groupSize": int(ms[3]),
        "inRaidGroup": bool(int(ms[4])),
        "mapID": int(ms[5]),
        "classID": int(ms[6]),
        "race": ms[7],
        "continentID": int(ms[8]),
        "minimapZone": ms[9],
        "level": int(ms[10]),
        "status": ms[11],
        "queueStarted": int(float(ms[12])),
    }

def format_state(data):
    return data["status"]

def format_details(data):
    return "%s - %s" % (data["name"], data["realm"])

def format_large_text(data):
    try:  # check for rogue class hall
        if data["classID"] == 4 and data["level"] > 97:
            x = classhall_images[data["minimapZone"]]
            return "The Hall of Shadows"
    except:
        pass
    return data["zone"]

def format_large_image(data):
    try:  # check for rogue class hall
        if data["classID"] == 4 and data["level"] > 97:
            return classhall_images[data["minimapZone"]]
    except:
        pass
    try:  # check for other class halls
        if data["level"] > 97:
            return classhall_images[data["zone"]]
    except:
        pass
    try:  # check for cities
        return city_images[data["mapID"]]
    except:
        pass
    # default to continent
    return continent_images[data["continentID"]]

def format_small_text(data):
    return "%d %s %s" % (data["level"], data["race"], class_names[data["classID"]])

def format_small_image(data):
    try:
        return class_images[data["classID"]]
    except:
        return "icon_full"

def format_start(data):
    if data["queueStarted"] != 0:
        return data["queueStarted"]
    return int(time.time())

def format_party_size(data):
    return None
    if data["groupSize"] == 0:
        return None
    return data["groupSize"]

def format_party_max(data):
    return None
    if data["groupSize"] == 0:
        return None
    if data["inRaidGroup"]:
        return 20
    return 5

def start_drp():
    rpc = pypresence.client(discord_client_id)
    rpc.start()
    last_msg = ""
    while True:  # The presence will stay on as long as the program is running
        try:
            msg = get_msg()
            if msg and last_msg != msg:
                print("Raw Msg: " + msg)
                data = parse_msg(msg)
                rpc.set_activity(state=format_state(data),
                                 details=format_details(data),
                                 start=format_start(data),
                                 large_image=format_large_image(data),
                                 large_text=format_large_text(data),
                                 small_image=format_small_image(data),
                                 small_text=format_small_text(data),
                                 party_size=format_party_size(data),
                                 party_max=format_party_max(data))
                last_msg = msg
        except Exception as e:
            logging.exception("Exception in Main Loop")
            print("Exception: " + str(e))
        time.sleep(1)

start_drp()
