CONFIG_SECRET_FILENAME = "config_secret.py"
OPTION_SECRET_KEY = "SECRET_KEY"
SECRET_KEY_SIZE = 24
OPTION_ADMIN_USERNAME = "ADMIN_USERNAME"
OPTION_ADMIN_PASSWORD = "ADMIN_PASSWORD"
ADMIN_USERNAME_DEFAULT = "admin"

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

option = OPTION_ADMIN_USERNAME
username = getparam(option, ADMIN_USERNAME_DEFAULT)
response = input("Set administrator username [%s]: " % username).strip().lower()
if response:
    username = response
params[option] = username

#---

def hash_password(password):
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password, config.PASSWORD_HASH_METHOD)

option = OPTION_ADMIN_PASSWORD
password = getparam(option)
if password:
    prompt = "Change administrator password [keep current]: "
else:
    prompt = "Set administrator password: "

while True:
    response = input(prompt).strip()
    if response:
        password = hash_password(response)
    if password:
        break
params[option] = password

# ---

with open(CONFIG_SECRET_FILENAME, "w") as f:
    for item in params.items():
        f.write('%s = %r\n' % item)


