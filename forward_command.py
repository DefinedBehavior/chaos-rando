import sys
import json
from urllib import request, parse

if __name__ == '__main__':
    cheerer = sys.argv[1]
    command = sys.argv[2]
    amount = sys.argv[3]

    payload = {
      'cheerer': cheerer,
      'message': command,
      'amount': int(amount),
    }

    print(payload)

    req =  request.Request('http://localhost:5000/command/', data=json.dumps(payload).encode('utf-8'))
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    resp = request.urlopen(req)