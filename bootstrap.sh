if [ ! -d env ]; then
    pyvenv env
fi

. env/bin/activate && pip3 install -r requirements.txt
