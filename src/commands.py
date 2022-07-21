import random
import re
import os
import sys
from functools import partial

command_regex = re.compile('#([a-zA-Z]+)')
COMMANDS_RAN = []

PAUSED = False
COMMANDS_PAUSED = []

fifo = '/tmp/chaos'
if os.path.exists(fifo):
    os.remove(fifo)

os.mkfifo(fifo, 0o666)
# Since we want non blocking, gotta have the fifo open for reading first. Open it here but don't do anything with it.
throwaway = os.open(fifo, os.O_RDONLY | os.O_NONBLOCK)
fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)

def toggle_pause(memory):
	global PAUSED
	PAUSED = not PAUSED
	if not PAUSED:
		while len(COMMANDS_PAUSED) > 0:
			val = COMMANDS_PAUSED.pop(0)
			exec_command(val, memory)

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

def do_run_command(name, command, amount, commands_config, message):
	encoded = COMMANDS[name]['id'].to_bytes(1, sys.byteorder) + COMMANDS[name]['payload_func'](name, amount, commands_config) + message.encode('ascii')
	l = len(encoded).to_bytes(1, sys.byteorder)
	val = l + encoded

	if PAUSED:
		COMMANDS_PAUSED.append(val)
	else:
		exec_command(val)

def maybe_run_command(cheerer, message, amount, commands_config):
	command = find_explicit_command(message, amount, commands_config)

	if not command:
		print("Couldn't find, going implicit")
		command = find_implicit_command(amount, commands_config)

	if command:
		print('Running ' + command)
		message = COMMANDS[command]['message_func'](cheerer, command, commands_config, amount)
		COMMANDS_RAN.append(message)
		do_run_command(command, COMMANDS[command], amount, commands_config, message)

def exec_command(val):
	print('Running command: ')
	print(list(val))
	os.write(fd, val)

# Payloads
def no_payload(command_name, amount, commands_config):
	return bytearray()

def unit_payload_val(command_name, amount, commands_config):
	return int(amount / commands_config[command_name]['cost'])

def unit_payload(command_name, amount, commands_config):
	return unit_payload_val(command_name, amount, commands_config).to_bytes(4, sys.byteorder)

def hearts_payload(command_name, amount, commands_config):
	return (unit_payload_val(command_name, amount, commands_config) * 16).to_bytes(4, sys.byteorder)

def per_30_sec_payload(command_name, amount, commands_config):
	return int(30).to_bytes(4, sys.byteorder)

def random_enemy_payload(command_name, amount, commands_config):
	payloads = [
		int(0x02).to_bytes(2, sys.byteorder) + int(0x01).to_bytes(2, sys.byteorder),  # Stalfos
		int(0xDD).to_bytes(2, sys.byteorder) + int(0x00).to_bytes(2, sys.byteorder),  # Like-like
		int(0x90).to_bytes(2, sys.byteorder) + int(0xFE).to_bytes(2, sys.byteorder),  # Gibdo
	];
	return random.choice(payloads)


# Messages
def base_message(cheerer_name, message):
	return cheerer_name + ': ' + message

def simple_message(message, cheerer_name, command_name, config, amount):
	return base_message(cheerer_name, message)

def simple(message):
	return partial(simple_message, message)

def timed_action_message(action, cheerer_name, command_name, config, amount):
	# TODO: support other durations
	return base_message(cheerer_name, action + ' +30s')

def timed(action):
	return partial(timed_action_message, action)

def give_or_take_message(cheerer_name, symbol, count, item):
	return base_message(cheerer_name, symbol + count + ' ' + item)

def give_message(item, cheerer_name, command_name, config, amount):
	return give_or_take_message(cheerer_name, '+', str(unit_payload_val(command_name, amount, config)), item)

def give(item):
	return partial(give_message, item)

def take_message(item, cheerer_name, command_name, config, amount):
	return give_or_take_message(cheerer_name, '-', str(unit_payload_val(command_name, amount, config)), item)

def take(item):
	return partial(take_message, item)

CMD_ID = 0x11
def INC_CMD_ID():
	global CMD_ID
	ret = CMD_ID
	CMD_ID += 1
	return ret 

COMMANDS = {
	# Instant
	'freeze': 	  	{ 'id': 0x00, 'payload_func': no_payload, 'message_func': simple('freeze') },
	'void': 	  	{ 'id': 0x01, 'payload_func': no_payload, 'message_func': simple('void out') },
	'age': 		  	{ 'id': 0x02, 'payload_func': no_payload, 'message_func': simple('change age') },
	'kill': 	  	{ 'id': 0x03, 'payload_func': no_payload, 'message_func': simple('kill') },
	'huge': 	  	{ 'id': 0x04, 'payload_func': no_payload, 'message_func': simple('huge') },
	'tiny': 	  	{ 'id': 0x05, 'payload_func': no_payload, 'message_func': simple('tiny') },

	# Timed
	'ohko': 	  	{ 'id': 0x06, 'payload_func': per_30_sec_payload, 'message_func': timed('OHKO') },
	'nohud': 	  	{ 'id': 0x07, 'payload_func': per_30_sec_payload, 'message_func': timed('no HUD') },
	# 'noz': 	 	  	{ 'id': 0x08, 'payload_func': per_30_sec_payload, 'message_func': timed('no Z') },
	'turbo': 	  	{ 'id': 0x09, 'payload_func': per_30_sec_payload, 'message_func': timed('turbo') },
	'invert': 	  	{ 'id': 0x0A, 'payload_func': per_30_sec_payload, 'message_func': timed('invert ctrls') },

	# Spawn
	'arwing': 	  	{ 'id': 0x0B, 'payload_func': no_payload, 			'message_func': simple('spawn arwing') },
	'enemy': 	  	{ 'id': 0x0C, 'payload_func': random_enemy_payload, 'message_func': simple('spawn random enemy') },

	# HP/rupees
	'givehearts': 	{ 'id': 0x0D, 'payload_func': hearts_payload, 	'message_func': give('hearts') },
	'takehearts': 	{ 'id': 0x0E, 'payload_func': hearts_payload, 	'message_func': take('hearts') },
	'giverupees': 	{ 'id': 0x0F, 'payload_func': unit_payload, 	'message_func': give('rupees') },
	'takerupees': 	{ 'id': 0x10, 'payload_func': unit_payload, 	'message_func': take('rupees') },

	# CDi-Fails magic
	'healthbars': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Health bars') },
	'fps': 			{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('FPS view') },
	'normalarrows': { 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Only normal arrows') },
	'noledge': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('No ledge climb') },
	'lava': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Floor is lava') },
	'rollplosion': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Exploding rolls') },
	'iceroll': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Freezing rolls') },
	'noz': 			{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('No Z') },
	'letterbox': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Mega letterbox') },
	'noturn': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('No turning') },
	'jail': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Jail') },
	'hold': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('On hold') },
	'sonic': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Sonic roll') },
	'navi': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Navi spam') },
	'scuffed': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Scuffed Link') },
	'rave': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Rave Mode') },
	'invis': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Invisibility') },
	'slip': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Slippery floor') },
	'ice': 			{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Ice damage') },
	'electric': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Electric damage') },
	'knockback': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Knockback damage') },
	'fire': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Fire damage') },
	'jump': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('No roll just jump') },
	'bighead': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Big head') },
	'smallhead': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Small head') },
	'dark': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Darken') },
	'spin': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Chaos spin') },
	'nomelee': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('No melee') },
	'invisenemies': { 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('No enemy draw') },
	'sandstorm': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Sandstorm') },
	'sink': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Sinking floor') },
	'cows': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Cow ritual') },
	'rocks': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Fire rocks rain') },
	'cuccos': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Cucco attack') },
	'bombrupees': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Exploding rupee challenge') },
	'nopickup': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('No item pickup') },
	'brokenchus': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Broken chus') },
	'annoy': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Annoying Item Get') },


	'lowgrav': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Low gravity') },
	'highgrav': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('High gravity') },
	'slowclimb': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Slow climb') },
	'shortshot': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Shortshot') },

	'explode': 		{ 'id': INC_CMD_ID(), 'payload_func': no_payload, 'message_func': simple('Explosion') },
	'restrain': 	{ 'id': INC_CMD_ID(), 'payload_func': no_payload, 'message_func': simple('Restrain Link') },
	'space': 		{ 'id': INC_CMD_ID(), 'payload_func': no_payload, 'message_func': simple('Trip to space') },

	# Add ammo
	'givechus':   	{ 'id': 0x80, 'payload_func': unit_payload, 'message_func': give('chus') },
	'givesticks': 	{ 'id': 0x81, 'payload_func': unit_payload, 'message_func': give('sticks') },
	'givenuts':   	{ 'id': 0x82, 'payload_func': unit_payload, 'message_func': give('nuts') },
	'givebombs':  	{ 'id': 0x83, 'payload_func': unit_payload, 'message_func': give('bombs') },
	'givearrows': 	{ 'id': 0x84, 'payload_func': unit_payload, 'message_func': give('arrows') },
	'giveseeds':  	{ 'id': 0x85, 'payload_func': unit_payload, 'message_func': give('seeds') },

	# Take ammo
	'takechus':   	{ 'id': 0xC0, 'payload_func': unit_payload, 'message_func': take('chus') },
	'takesticks': 	{ 'id': 0xC1, 'payload_func': unit_payload, 'message_func': take('sticks') },
	'takenuts':   	{ 'id': 0xC2, 'payload_func': unit_payload, 'message_func': take('nuts') },
	'takebombs':  	{ 'id': 0xC3, 'payload_func': unit_payload, 'message_func': take('bombs') },
	'takearrows': 	{ 'id': 0xC4, 'payload_func': unit_payload, 'message_func': take('arrows') },
	'takeseeds':  	{ 'id': 0xC5, 'payload_func': unit_payload, 'message_func': take('seeds') },

	# Boots
	'iron': 	  	{ 'id': 0xE2, 'payload_func': per_30_sec_payload, 'message_func': timed('iron boots') },
	'hover': 	  	{ 'id': 0xE3, 'payload_func': per_30_sec_payload, 'message_func': timed('hover boots') },
	'fboots':	  	{ 'id': 0xEF, 'payload_func': per_30_sec_payload, 'message_func': timed('fboots') },

}