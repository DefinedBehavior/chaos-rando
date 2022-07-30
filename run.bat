@echo off
echo "Installing requirements"
pip install -r src/requirements.txt
echo "running serve"
python src/serve.py