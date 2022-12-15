import dbus
from dbus.mainloop.glib import DBusGMainLoop

DBusGMainLoop(set_as_default=True)


def connect(path):
    system = dbus.SystemBus()
    device1 = dbus.Interface(system.get_object("org.bluez", path),
                             "org.bluez.Device1")

    try:
        device1.Connect()
        return True, ""
    except dbus.exceptions.DBusException as e:
        return False, str(e)


def disconnect(path):
    system = dbus.SystemBus()
    device1 = dbus.Interface(system.get_object("org.bluez", path),
                             "org.bluez.Device1")

    try:
        device1.Disconnect()
        return True, ""
    except dbus.exceptions.DBusException as e:
        return False, str(e)


def reset(path):
    system = dbus.SystemBus()
    device1 = dbus.Interface(system.get_object("org.bluez", path),
                             "org.bluez.Device1")

    try:
        device1.Disconnect()
        device1.Connect()
        return True, ""
    except dbus.exceptions.DBusException as e:
        return False, str(e)


def get_devices():
    system = dbus.SystemBus()
    bluez = dbus.Interface(system.get_object("org.bluez", "/"),
                           "org.freedesktop.DBus.ObjectManager")
    all_objects = bluez.GetManagedObjects()

    devices = []
    for path in all_objects:
        if "org.bluez.Device1" in all_objects[path]:
            devices.append(get_device(path, system))

    return devices

def get_device(path, system = None):
    system = system if system is not None else dbus.SystemBus()
    device1 = dbus.Interface(system.get_object("org.bluez", path),
                                     "org.freedesktop.DBus.Properties")

    props = dbus_to_python(device1.GetAll("org.bluez.Device1"))

    return {
        "name": props.get("Name", "Unnamed device"),
        "uuid": props.get("Address", "Unknown address"),
        "icon": props.get("Icon", "default"),
        "active": props.get("Connected", False),
        "battery": get_battery_percentage(device1) if props.get("Connected", False) else None,
        "dbus_path": str(path)
    }


def get_battery_percentage(device1):
    try:
        return int(device1.GetAll("org.bluez.Battery1")["Percentage"])
    except:
        return None

# From https://stackoverflow.com/questions/11486443/dbus-python-how-to-get-response-with-native-types
def dbus_to_python(data):
    """convert dbus data types to python native data types"""
    if isinstance(data, dbus.String):
        data = str(data)
    elif isinstance(data, dbus.Boolean):
        data = bool(data)
    elif isinstance(data, dbus.Int64):
        data = int(data)
    elif isinstance(data, dbus.Double):
        data = float(data)
    elif isinstance(data, dbus.Array):
        data = [dbus_to_python(value) for value in data]
    elif isinstance(data, dbus.Dictionary):
        new_data = dict()
        for key in data.keys():
            new_key = dbus_to_python(key)
            new_data[new_key] = dbus_to_python(data[key])
        data = new_data
    return data


if __name__ == "__main__":
    devs = get_devices()
    for a in devs:
        print(a)
