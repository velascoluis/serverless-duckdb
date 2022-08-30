cd src
pip3 install --upgrade pip
python3 -m venv local_test_env
source local_test_env/bin/activate
pip3 install -r requirements.txt
python3 main.py
