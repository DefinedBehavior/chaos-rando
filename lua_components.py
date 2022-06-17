from bizhook import export_lua_components

import os
import shutil

cur_dir = os.getcwd()
components_dir = os.path.join(cur_dir, 'lua_components')
if not os.path.exists(components_dir):
	export_lua_components(cur_dir)

modules_dir = os.path.join(cur_dir, 'lua_components/lua_modules')
if not os.path.exists(os.path.join(cur_dir, 'lua_modules')):
	shutil.move(modules_dir, cur_dir)