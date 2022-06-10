from flask import Flask, render_template, request

from commands import maybe_run_command, toggle_pause, COMMANDS_RAN
from commands_config import reload_config

from bizhook import Memory

import webbrowser

app = Flask(__name__)
sdram = Memory('RDRAM')
commands_config = {}

@app.route("/")
def home():
    return render_template('debug.html')

@app.route("/command/", methods=['POST'])
def command():
    content = request.get_json()

    print('Got a command: ' + str(content['message']) + ' $-> ' + str(content['amount']))
    maybe_run_command(content['cheerer'], content['message'], content['amount'], commands_config, sdram)

    return ('', 200)

@app.route('/reload/', methods=['POST'])
def reload():
  commands_config = reload_config()
  return commands_config

@app.route('/ran/<f>', methods=['GET'])
def ran(f):
    ret = { 'commands': COMMANDS_RAN[int(f):] }
    return ret

@app.route('/shutdown/', methods=['GET'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

@app.route('/pause/', methods=['POST'])
def pause():
    toggle_pause(sdram)
    return ('', 200)

if __name__ == '__main__':
    commands_config = reload_config()
    webbrowser.open("http://localhost:5000", new=0, autoraise=True)
    app.run(debug=True, threaded=False, use_reloader=False)