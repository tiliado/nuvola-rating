CONFIG_SECRET_FILENAME = "config_secret.py"
OPTION_SECRET_KEY = "SECRET_KEY"
SECRET_KEY_SIZE = 24

try:
    import config_secret as secret
except ImportError:
    with open(CONFIG_SECRET_FILENAME, "w") as f:
        f.write("# In progress")
    import config_secret as secret

import config

def getparam(name, default=None):
    return getattr(secret, name, default)

params = {}

# ---

def is_secret_key_valid(key):
    return key and len(key) == SECRET_KEY_SIZE

def gen_secret_key():
    import os
    return os.urandom(SECRET_KEY_SIZE)

option = OPTION_SECRET_KEY
key = getparam(option)
if is_secret_key_valid(key):
    response = input("Secret key is valid. Would you like to generate a new one? [y/N] ");
    if response.lower().strip() == "y":
        key = None
if not is_secret_key_valid(key):
    key = gen_secret_key()
    print("Secret key generated: %s" % key)
params[option] = key

#---

with open(CONFIG_SECRET_FILENAME, "w") as f:
    for item in params.items():
        f.write('%s = %r\n' % item)


