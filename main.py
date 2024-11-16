import os
DEFAULT_LOCKFILE_PATH = "C:/Riot Games/League of Legends/lockfile"

def parse_lockfile():
    lockfile = {}
    try:
        with open(DEFAULT_LOCKFILE_PATH) as f:
            contents = f.read()
            contents = contents.split(":")
            lockfile["pid"] = contents[1]
            lockfile["port"] = contents[2]
            lockfile["password"] = contents[3]
            lockfile["protocol"] = contents[4]

    except FileNotFoundError:
        raise FileNotFoundError("Lockfile couldn't be found, did you install league to a custom directory?")
    except Exception as e:
        raise Exception(f"Failed to parse lockfile: {str(e)}")
    return lockfile


lockfile = parse_lockfile()
print(lockfile)