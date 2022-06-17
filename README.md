# Chaos Rando

This is a set of small tools to allow Twitch chat to trigger things inside of your OoT Randomizer.

[Here's a clip of how this plays out.](https://clips.twitch.tv/CourageousFrigidLobsterItsBoshyTime-4bdaFR0Mrm1rqYz8)

## Prerequisites

- An OoT Randomizer-compatible ROM. See Rando documentation for more info.
- A Windows machine
- Python 3 and pip installed
- A copy of the Bizhawk Emulator

## Setup

1. Generate your randomizer seed and ROM with the Chaos Rando fork of OoT Rando: https://github.com/DefinedBehavior/OoT-Randomizer
2. In bizhawk, ensure "Lua+LuaInterface" is selected in Config > Customize > Advanced > Lua Core, and that Mupen64Plus is the selected core (then close bizhawk)
3. Copy the `src` folder, `commands_config.json`, `forward_command.py`, `lua_components.py`, and `play.bat` files from this repo to your bizhawk folder (all 5 should be next to the bizhawk exe)
4. Copy your rando ROM to the same bizhawk folder and rename it `rando.z64`
5. Double click on `play.bat`. This should install requirements, run bizhawk with the required LUA script, and then run the local server after a short delay. When setup is complete, your web browser should navigate to the debug page.

If everything is working properly, starting a new game and triggering a test message from the debug page in Link's house should work. Testing with `message = #freeze` and `amount = 999999` should trigger an ice block.

### Lioranboard button

This repo contains a button for Lioranboard. To use it, import the contents of `lb_button.json` into your Lioranboard deck and setup a trigger for twitch bits. You'll also have to edit the button so that the path at line 6 is the path to the `forward_command.py` file you copied into your bizhawk folder.

There is also a Channel Points version of this button, although you'll need multiple channel points rewards that your users can redeem for different costs. The command is read from the message of the redemption, meaning you should set the reward to allow text entry.

### Custom triggers

If the Lioranboard buttons don't fit your use case, you can create another integration that directly calls the `forward_command.py` script with the correct arguments:

`forward_command.py user_name "message" bit_amount` 

## Configuration

Commands costs are configured in the `commands_config.json` file. The "cost" value is price in bits, and the "explicit" value determines whether the user is required to explicitly type the command in this message. For instance:

`"freeze": { "cost": 111, "explicit": false },`

Means a user cheering 111 bits without entering a command will trigger the freeze command.

`"iron": { "cost": 123, "explicit": true },`

Means a user cheering 123 bits needs to include `#iron` in their message for Iron boots to be equiped for 30 seconds.

Some commands change quantities based on bits donated. For instance:

`"givechus": { "cost": 1, "explicit": true },`

Means a user cheering 20 bits with the message `#givechus` will add 20 chus to the inventory.

Give/Take commands are all quantities-based. Arwing, enemy, freeze, void, age, kill, huge, tiny are one time triggers. The rest are a fixed cost to add 30 seconds to the running timer for this command.

## Debug page

From the debug page, you can

- Reload configuration to update the internal settings after changes to the `commands_config.json` file while chaos rando is running.
- Pause commands until the "Pause commands" button is clicked again, after which all of the commands sent during pause will be triggered.
- Send test commands by entering a message and a cheer amount to simulate a twitch cheer.

## Contact

Drop me a line at chaosrando (at) definedbehaviour (dot) com if you play this :)
