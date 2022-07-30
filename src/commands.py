import random
import re
import os
import sys
import win32pipe
import win32file
from functools import partial

command_regex = re.compile('#([a-zA-Z]+)')
COMMANDS_RAN = []

PAUSED = False
COMMANDS_PAUSED = []

pipe_name = r"\\.\pipe\chaos"
pipe = win32pipe.CreateNamedPipe(
	pipe_name, 
	win32pipe.PIPE_ACCESS_DUPLEX,
	win32pipe.PIPE_TYPE_BYTE | 
			win32pipe.PIPE_READMODE_BYTE,
	1, 65536, 65536, 0, None)

win32pipe.ConnectNamedPipe(pipe, None)

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
	win32file.WriteFile(pipe, val)

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

def per_60_sec_payload(command_name, amount, commands_config):
	return int(60).to_bytes(4, sys.byteorder)

def random_enemy_payload(command_name, amount, commands_config):
	payloads = [
		int(10).to_bytes(4, sys.byteorder) + int(0x13).to_bytes(2, sys.byteorder) + int(0x04).to_bytes(2, sys.byteorder),  # Bunch of ice keese
		int(3).to_bytes(4, sys.byteorder) + int(0x1AF).to_bytes(2, sys.byteorder) + int(0x01).to_bytes(2, sys.byteorder),  # White Wolfos
		int(1).to_bytes(4, sys.byteorder) + int(0x113).to_bytes(2, sys.byteorder) + int(0x02).to_bytes(2, sys.byteorder),  # Iron Knuckle
		int(1).to_bytes(4, sys.byteorder) + int(0x1D).to_bytes(2, sys.byteorder) + int(0x00).to_bytes(2, sys.byteorder),  # Peahat
		int(2).to_bytes(4, sys.byteorder) + int(0x02).to_bytes(2, sys.byteorder) + int(0x01).to_bytes(2, sys.byteorder),  # Stalfos
		int(1).to_bytes(4, sys.byteorder) + int(0xDD).to_bytes(2, sys.byteorder) + int(0x00).to_bytes(2, sys.byteorder),  # Like-like
		int(4).to_bytes(4, sys.byteorder) + int(0x90).to_bytes(2, sys.byteorder) + int(0xFE).to_bytes(2, sys.byteorder),  # Gibdo
	];
	return random.choice(payloads)

def enemy_payload(count, id, params, command_name, amount, commands_config):
	return int(count).to_bytes(4, sys.byteorder) + int(id).to_bytes(2, sys.byteorder) + int(params).to_bytes(2, sys.byteorder)

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
	'enlarge': 	  	{ 'id': 0x04, 'payload_func': no_payload, 'message_func': simple('enlarge') },
	'shrink': 	  	{ 'id': 0x05, 'payload_func': no_payload, 'message_func': simple('shrink') },

	# Timed
	'ohko': 	  	{ 'id': 0x06, 'payload_func': per_30_sec_payload, 'message_func': timed('OHKO') },
	'nohud': 	  	{ 'id': 0x07, 'payload_func': per_30_sec_payload, 'message_func': timed('no HUD') },
	# 'noz': 	 	  	{ 'id': 0x08, 'payload_func': per_30_sec_payload, 'message_func': timed('no Z') },
	'invert': 	  	{ 'id': 0x0A, 'payload_func': per_30_sec_payload, 'message_func': timed('invert ctrls') },

	# Spawn
	'arwing': 	  	{ 'id': 0x0B, 'payload_func': no_payload, 			'message_func': simple('spawn arwing') },
	'enemy': 	  	{ 'id': 0x0C, 'payload_func': random_enemy_payload, 'message_func': simple('spawn random enemy') },

	'keese': 			{ 'id': 0x0C, 'payload_func': partial(enemy_payload, 10, 0x13, 0x04), 'message_func': simple('Ice keese') },
	'wolfos': 		{ 'id': 0x0C, 'payload_func': partial(enemy_payload, 3, 0x1AF, 0x01), 'message_func': simple('Wolfos') },
	'ironknuckle':{ 'id': 0x0C, 'payload_func': partial(enemy_payload, 1, 0x113, 0x02), 'message_func': simple('Iron Knuckle') },
	'peahat': 		{ 'id': 0x0C, 'payload_func': partial(enemy_payload, 1, 0x1D, 0x00), 'message_func': simple('Peahat') },
	'stalfos': 		{ 'id': 0x0C, 'payload_func': partial(enemy_payload, 2, 0x02, 0x01), 'message_func': simple('Stalfos') },
	'likelike': 	{ 'id': 0x0C, 'payload_func': partial(enemy_payload, 1, 0xDD, 0x00), 'message_func': simple('Like-like') },
	'gibdo': 			{ 'id': 0x0C, 'payload_func': partial(enemy_payload, 4, 0x90, 0xFE), 'message_func': simple('Gibdo') },

	# HP/rupees
	'givehearts': 	{ 'id': 0x0D, 'payload_func': hearts_payload, 	'message_func': give('hearts') },
	'takehearts': 	{ 'id': 0x0E, 'payload_func': hearts_payload, 	'message_func': take('hearts') },
	'giverupees': 	{ 'id': 0x0F, 'payload_func': unit_payload, 	'message_func': give('rupees') },
	'takerupees': 	{ 'id': 0x10, 'payload_func': unit_payload, 	'message_func': take('rupees') },

	# CDi-Fails magic
	'nofps': 			{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('No FPS view') },
	'normalarrows': { 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Only normal arrows') },
	'noledge': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('No ledge climb') },
	'lava': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Floor is lava') },
	'rollplosion': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Exploding rolls') },
	'iceroll': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Freezing rolls') },
	'noz': 			{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('No Z') },
	'letterbox': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Mega letterbox') },
	'noturn': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('No turning') },
	'jail': 		{ 'id': INC_CMD_ID(), 'payload_func': per_60_sec_payload, 'message_func': simple('Jail +60s') },
	'hold': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('On hold') },
	'sonic': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Sonic roll') },
	'navi': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Navi spam') },
	'scuffed': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Scuffed Link') },
	'rave': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Rave Mode') },
	'invis': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Invisibility') },
	'slip': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Slippery floor') },
	'ice': 			{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Ice damage') },
	'electric': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Electric damage') },
	'knockback': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Knockback damage') },
	'fire': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Fire damage') },
	'jump': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('No roll just jump') },
	'bighead': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Big head') },
	'smallhead': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Small head') },
	'dark': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Darken') },
	'spin': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Chaos spin') },
	'nomelee': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('No melee') },
	'invisenemies': { 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('No enemy draw') },
	'sandstorm': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Sandstorm') },
	'sink': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Sinking floor') },
	'cows': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Cow ritual') },
	'rocks': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Fire rocks rain') },
	'cuccos': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Cucco attack') },
	'bombrupees': 	{ 'id': INC_CMD_ID(), 'payload_func': no_payload, 'message_func': simple('Exploding rupee challenge') },
	'nopickup': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('No item pickup') },
	'brokenchus': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Broken chus') },
	'annoy': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': timed('Annoying Item Get') },

	'lowgrav': 		{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Low gravity') },
	'highgrav': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('High gravity') },
	'slowclimb': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Slow climb') },
	'shortshot': 	{ 'id': INC_CMD_ID(), 'payload_func': per_30_sec_payload, 'message_func': simple('Shortshot') },

	'explode': 		{ 'id': INC_CMD_ID(), 'payload_func': no_payload, 'message_func': simple('Explosion') },
	'restrain': 	{ 'id': INC_CMD_ID(), 'payload_func': no_payload, 'message_func': simple('Restrain Link') },
	'space': 		{ 'id': INC_CMD_ID(), 'payload_func': no_payload, 'message_func': simple('Trip to space') },
	'reset': 		{ 'id': INC_CMD_ID(), 'payload_func': no_payload, 'message_func': simple('This run sucks, reset.') },

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
}