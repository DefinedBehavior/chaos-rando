(function () {
	console.log("loaded")
	let commandCount = 0;
	let ranCommands = [];

	function doRequest(command, amount) {
		let req = new Request('/command/', {
				method: 'POST', 
				headers: {
			      'Content-Type': 'application/json',
			    },
			    body: JSON.stringify({
			    	cheerer: "debug",
			    	message: command,
			    	amount: amount,
			    })
			});

		fetch(req)
			.then(res => {
				if (res.status === 200) {
					// Do something? 
				} else {
					console.error("woops");
				}
			});
	}

	function reloadConfig() {
		 let req = new Request('/reload/', {
				method: 'POST',
			});

		fetch(req)
			.then(res => {
				if (res.status === 200) {
					return res.json();
				} else {
					console.error("woops");
				}
			})
			.then(c => {
				let textField = document.getElementById('config-text');
				let configStr = "";
				for (let [k, v] of Object.entries(c)) {
					configStr += "#"
					configStr += k;
					configStr += ": ";
					configStr += v['cost'];
					configStr += "bits.";
					if (v['explicit']) configStr += " Requires explicit command in message";
					configStr += "\n";
				}
				textField.value = configStr;
			});
	}

	document.getElementById('button-send-command').onclick = function(e) {
		doRequest(
			document.getElementById('command-input-body').value,
			parseInt(document.getElementById('command-input-amount').value));
	};

	document.getElementById('button-send-reload').onclick = reloadConfig;
	document.getElementById('button-send-pause').onclick = function(e) {
		let req = new Request('/pause/', {
				method: 'POST',
			});
		fetch(req)
			.then(res => {
				if (res.status === 200) {
					// Do something? 
				} else {
					console.error("couldn't pause :(");
				}
			});
	}

	function process_timeout() {
		for (let command of ranCommands) {
			command['time'] -= 1;
		}

		ranCommands = ranCommands.filter(c => c['time'] > 0);

		fetch('/ran/' + commandCount)
			.then(res => {
				if (res.status === 200) {
					return res.json();
				} else {
					console.error("can't get ran commands");
				}
			})
			.then(c => {
				let commands = c['commands'];
				commandCount += commands.length;
				for (let command of commands) {
					ranCommands.push({'text': command, 'time': 10});
				}

			});
		document.getElementById('cheerers-container').innerHTML = ranCommands.reduce((p, c) => p + " ~ " + c['text'], "");
		setTimeout(process_timeout, 1000);
	}

	setTimeout(process_timeout, 1000);

	reloadConfig();
})();