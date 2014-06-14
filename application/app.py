# /usr/bin/python

import json
import gevent
from gevent import monkey
from datetime import datetime
from gevent.queue import Queue
from gevent.wsgi import WSGIServer
from bson.objectid import ObjectId
from flask.ext.pymongo import PyMongo
from flask import Flask, Response, render_template, request

monkey.patch_all()
app = Flask(__name__)
mongo = PyMongo(app)
subscriptions = []

class JSONEncoderExt(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif isinstance(obj, ObjectId):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)

def msg_to_sse_msg(message):
    # Convierte un diccionario que representa el mensaje de un usuario
    # a un evento compatible con clientes SSE con el mensaje del usuario
    # condificado en una cadena JSON.
    sse_message = 'event:message\n'
    sse_message = sse_message + 'id: %s\n' % message['_id']
    sse_message = sse_message + 'data: %s\n\n' % json.dumps(message, cls=JSONEncoderExt)
    return sse_message

@app.route('/')
def index():
    template_data = {
        'messages': mongo.db.messages.find().sort([('_id', 0)])
    }
    return render_template('index.html', **template_data)

@app.route('/post', methods=['POST'])
def post_message():
    # Recibe un nuevo mensaje del usario. Lo guarda en la DB y notifica
    # del nuevo mensaje al resto de usuarios por medio de SSE.
    message = json.loads(request.data)
    message['time'] = datetime.now()
    new_msg_id = mongo.db.messages.insert(message)
    message['_id'] = new_msg_id

    # Enviar al resto de usuarios el nuevo mensaje por medio de SSE
    # Lo hacemos en segundo plano porque la lista de subscriptores
    # puede ser larga y algunas colas pueden bloquear la peticion.
    def notify_users():
        for subscription in subscriptions:
            subscription.put(message)
    gevent.spawn(notify_users)

    # Devolvemos el nuevo mensaje al usuario que lo ha creado.
    return Response(json.dumps(message, cls=JSONEncoderExt), mimetype='application/json')

@app.route('/events')
def yield_events():
    def events(headers):
        with app.app_context():
            if headers.get('Last-Event-ID', False):
                # Enviar todos los mensajes que no ha recibido el usuario
                def previous_messages():
                    last_msg_received = headers.get('Last-Event-ID')
                    messages = mongo.db.messages.find({'_id': {'$gt': ObjectId(last_msg_received)}})
                    return '\n'.join(map(lambda m: msg_to_sse_msg(m), messages))

                yield previous_messages()

        queue = Queue()
        subscriptions.append(queue)
        try:
            while True:
                message = queue.get()
                yield msg_to_sse_msg(message)
        except:
            subscriptions.remove(queue)

    return Response(events(request.headers), mimetype='text/event-stream')


# Iniciar la configuracion
app.config['MONGO_HOST']    = 'localhost'
app.config['MONGO_DBNAME']  = 'sse'

if __name__ == '__main__':
    app.debug = True
    server = WSGIServer(('192.168.1.103', 5000), app)
    server.serve_forever()

