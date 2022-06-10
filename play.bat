@echo off
echo "Installing requirements"
pip install -r src/requirements.txt
echo "Starting Emu"
START EmuHawk.exe --lua=lua_components/hook.lua rando.z64
echo "Giving bizhawk a few seconds to get its shit together."
timeout 15 > NUL
echo "running serve"
python src/serve.py