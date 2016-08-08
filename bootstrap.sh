export PATH="$PATH:/opt/python/bin"

VENV="$1"
[ ! -z "$VENV" ] || VENV=env

if [ ! -d "$VENV" ]; then
    pyvenv "$VENV"
fi

. "$VENV"/bin/activate && pip3 install -r requirements.txt
