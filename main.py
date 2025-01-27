import logging
import os.path
import subprocess
import pathlib
import time

import gi

import bt_tools

gi.require_version('Gdk', '3.0')

from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.client.Extension import Extension
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem

logger = logging.getLogger(__name__)
extension_home = str(pathlib.Path(__file__).parent.resolve())

description_active = "{}  |  ACTIVE  |  {}"
description_inactive = "{}"


class BluetoothManagerExtension(Extension):
    def __init__(self):
        super(BluetoothManagerExtension, self).__init__()

        # Subscribe plugin listeners to launcher
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        search_query = event.get_argument()
        devices = bt_tools.get_devices()
        devices = sorted(devices, key=lambda d: d["name"].lower())

        items = []
        for device in devices:
            name = device["name"]
            if search_query is not None and search_query not in name.lower():
                continue

            icon_name = "{}_{}".format(device["icon"], device["active"])
            icon_path = 'images/{}.png'.format(icon_name)
            description = description_active if device["active"] else description_inactive
            description = description.format(device["uuid"], get_battery_percentage(device["battery"], extension))

            if not os.path.isfile(extension_home + "/" + icon_path):
                logger.warning("Icon not found: " + icon_path)
                icon_path = "images/default_{}.png".format(device["active"])

            def on_click(reset = False):
                device['reset'] = reset and device["active"]
                return ExtensionCustomAction(device, keep_app_open=False)
            
            item_row = ExtensionResultItem(icon=icon_path,
                                           name=name,
                                           description=description,
                                           on_enter=on_click(),
                                           on_alt_enter=on_click(True))
            items.append(item_row)

        return RenderResultListAction(items)


class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        device = event.get_data()
        path = device["dbus_path"]

        if device["reset"]:
            result, log = bt_tools.reset(path)
        elif device["active"]:
            result, log = bt_tools.disconnect(path)
        else:
            result, log = bt_tools.connect(path)

        logging.debug(log)

        # Notification
        if extension.preferences.get("enable_notifications") == "true":
            if not result:
                # Operation failed
                send_notification("ERROR: ", log)
            elif device["reset"]:
                # Success, reseted
                send_notification(device["name"], "Device connection reseted.")
            elif device["active"]:
                # Success, disconnected
                send_notification(device["name"], "Device disconnected.")
            else:
                time.sleep(2)

                # Notify battery percentage if successfully connected
                battery = bt_tools.get_device(path).get("battery")
                
                # Success, connected
                send_notification(device["name"], "Device connected." +
                    (" Battery: {}".format(get_battery_percentage(battery, extension)) if battery is not None else ""))

        # Run script if successfully connected and script isn't empty
        script = extension.preferences.get("script_on_connect")
        if not device["active"] and script != "" and result:
            subprocess.run([script, device["name"], device["uuid"]], stdout=subprocess.PIPE)


def send_notification(title, message):
    logger.debug("Sent notification: " + title, message)
    subprocess.run(["notify-send",
                    "-h", "int:transient:1",
                    "--icon=" + os.path.dirname(os.path.realpath(__file__)) + "/images/icon.png",
                    title, message])

def get_battery_percentage(battery, extension):
    try:
        low_battery = int(extension.preferences.get("low_battery"))

        if battery is None: return ""
        return "{} {}%".format("🔋" if battery > low_battery else "🪫", battery)
    except:
        return ""


if __name__ == '__main__':
    BluetoothManagerExtension().run()
