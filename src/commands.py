from config import COMMAND_BUFFER_ADDRESS, COMMAND_BUFFER_INSERTION_INDEX_ADDRESS

import random
import re

command_regex = re.compile('#([a-zA-Z]+)')
COMMANDS_RAN = []

def find_explicit_command(message, amount, commands_config):
	match = command_regex.search(message)
	if match:
		command = match.group(1)
		print('Got a match ' + command)
		if command in commands_config and commands_config[command]['cost'] <= amount:
			return command
	return None

def find_implicit_command(amount, commands_config):
	highest_price = 0
	best_command_name = None
	for k, v in commands_config.items():
		if highest_price < v['cost'] and not v['explicit'] and v['cost'] <= amount:
			highest_price = v['cost']
			best_command_name = k
	return best_command_name

def do_run_command(name, command, amount, commands_config, memory):
	exec_command((COMMANDS[name]['id'] << 24) | (COMMANDS[name]['payload_func'](name, amount, commands_config) & 0xFFFFFF), memory)

def maybe_run_command(cheerer, message, amount, commands_config, memory):
	command = find_explicit_command(message, amount, commands_config)

	if not command:
		print("Couldn't find, going implicit")
		command = find_implicit_command(amount, commands_config)

	if command:
		print('Running ' + command)
		COMMANDS_RAN.append(COMMANDS[command]['message_func'](cheerer, command, commands_config, amount))
		do_run_command(command, COMMANDS[command], amount, commands_config, memory)

def exec_command(val, memory):
	print('Running command: ' + format(val, '032b'))
	
	insertion_index = memory.read_u8(COMMAND_BUFFER_INSERTION_INDEX_ADDRESS)

	val_address = COMMAND_BUFFER_ADDRESS + (insertion_index * 4)
	print('Insertion at: ' + str(insertion_index) + " -> " + format(val_address, 'x'))
	
	current_val = memory.read_u32_be(val_address)
	if current_val != 0xDEADBEEF:
		# We wrote all the way around the ring buffer and will start overwriting commands if we write here. Drop this one axellScam.
		print('Dropping command')
		return

	memory.write_u32_be(val_address, val)
	memory.write_u8(COMMAND_BUFFER_INSERTION_INDEX_ADDRESS, (insertion_index + 1) % 16)

def mask_payload(payload):
	return payload & 0xFFFFFF

def no_payload(command_name, amount, commands_config):
	return 0

def unit_payload(command_name, amount, commands_config):
	return int(amount / commands_config[command_name]['cost'])

def hearts_payload(command_name, amount, commands_config):
	return unit_payload(command_name, amount, commands_config) * 16

def frames_payload(command_name, amount, commands_config):
	return unit_payload(command_name, amount, commands_config) * 20

def per_30_sec_payload(command_name, amount, commands_config):
	return 30 * 20

def random_enemy_payload(command_name, amount, commands_config):
	payloads = [
		0x023201, # Stalfos
		0xDDD400, # Like-like
		0x9098FE, # Gibdo
		0x110B01, # wallmaster
	];
	return random.choice(payloads)

COMMANDS = {
	# Instant
	'freeze': 	  	{ 'id': 0x00, 'payload_func': no_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': freeze' },
	'void': 	  	{ 'id': 0x01, 'payload_func': no_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': void out' },
	'age': 		  	{ 'id': 0x02, 'payload_func': no_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': change age' },
	'kill': 	  	{ 'id': 0x03, 'payload_func': no_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': kill' },
	'huge': 	  	{ 'id': 0x04, 'payload_func': no_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': huge' },
	'tiny': 	  	{ 'id': 0x05, 'payload_func': no_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': tiny' },

	# Timed
	'ohko': 	  	{ 'id': 0x06, 'payload_func': per_30_sec_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': OHKO +30s' },
	'nohud': 	  	{ 'id': 0x07, 'payload_func': per_30_sec_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': no HUD +30s' },
	'noz': 	 	  	{ 'id': 0x08, 'payload_func': per_30_sec_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': no Z +30s' },
	'turbo': 	  	{ 'id': 0x09, 'payload_func': per_30_sec_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': turbo +30s' },
	'invert': 	  	{ 'id': 0x0A, 'payload_func': per_30_sec_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': invert ctrls +30s' },

	# Spawn
	'arwing': 	  	{ 'id': 0x0B, 'payload_func': no_payload, 			'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': spawn arwing' },
	'enemy': 	  	{ 'id': 0x0C, 'payload_func': random_enemy_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': spawn random enemy' },

	# HP/rupees
	'givehearts': 	{ 'id': 0x0D, 'payload_func': hearts_payload, 	'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': +' + str(unit_payload(command_name, amount, config)) + ' hearts' },
	'takehearts': 	{ 'id': 0x0E, 'payload_func': hearts_payload, 	'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': -' + str(unit_payload(command_name, amount, config)) + ' hearts' },
	'giverupees': 	{ 'id': 0x0F, 'payload_func': unit_payload, 	'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': +' + str(unit_payload(command_name, amount, config)) + ' rupees' },
	'takerupees': 	{ 'id': 0x10, 'payload_func': unit_payload, 	'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': -' + str(unit_payload(command_name, amount, config)) + ' rupees' },

	# Add ammo
	'givechus':   	{ 'id': 0x80, 'payload_func': unit_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': +' + str(unit_payload(command_name, amount, config)) + ' chus' },
	'givesticks': 	{ 'id': 0x81, 'payload_func': unit_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': +' + str(unit_payload(command_name, amount, config)) + ' sticks' },
	'givenuts':   	{ 'id': 0x82, 'payload_func': unit_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': +' + str(unit_payload(command_name, amount, config)) + ' nuts' },
	'givebombs':  	{ 'id': 0x83, 'payload_func': unit_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': +' + str(unit_payload(command_name, amount, config)) + ' bombs' },
	'givearrows': 	{ 'id': 0x84, 'payload_func': unit_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': +' + str(unit_payload(command_name, amount, config)) + ' arrows' },
	'giveseeds':  	{ 'id': 0x85, 'payload_func': unit_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': +' + str(unit_payload(command_name, amount, config)) + ' seeds' },

	# Take ammo
	'takechus':   	{ 'id': 0xC0, 'payload_func': unit_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': -' + str(unit_payload(command_name, amount, config)) + ' chus' },
	'takesticks': 	{ 'id': 0xC1, 'payload_func': unit_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': -' + str(unit_payload(command_name, amount, config)) + ' sticks' },
	'takenuts':   	{ 'id': 0xC2, 'payload_func': unit_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': -' + str(unit_payload(command_name, amount, config)) + ' nuts' },
	'takebombs':  	{ 'id': 0xC3, 'payload_func': unit_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': -' + str(unit_payload(command_name, amount, config)) + ' bombs' },
	'takearrows': 	{ 'id': 0xC4, 'payload_func': unit_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': -' + str(unit_payload(command_name, amount, config)) + ' arrows' },
	'takeseeds':  	{ 'id': 0xC5, 'payload_func': unit_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': -' + str(unit_payload(command_name, amount, config)) + ' seeds' },

	# Boots
	'iron': 	  	{ 'id': 0xE2, 'payload_func': per_30_sec_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': iron boots +30s' },
	'hover': 	  	{ 'id': 0xE3, 'payload_func': per_30_sec_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': hover boots +30s' },
	'fboots':	  	{ 'id': 0xEF, 'payload_func': per_30_sec_payload, 'message_func': lambda cheerer_name, command_name, config, amount: cheerer_name + ': fboots +30s' },

}