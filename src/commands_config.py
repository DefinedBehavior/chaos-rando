import json

def reload_config():
	with open('commands_config.json', 'r') as config_file:
		data = json.loads(config_file.read())
	return data