import json
import websocket
from dotenv import load_dotenv

load_dotenv()

WS = os.getenv('VEGA_SERVER')
login = os.getenv('LOGIN')
password = os.getenv('PASSWORD')

token = None


def on_message(ws, message):
    global token
    response = json.loads(message)
    if response['cmd'] == 'auth_resp':  # Если ответ auth_resp
        if response['status']:
            token = response.get('token')
            command_list = response.get('command_list')
            print("Authentication successful. Token:", token)
            print("Command list: ", command_list)
            # Подтверждаем аутентификацию токеном
            confirm_auth(ws, token)
        else:
            print("Authentication failed:", response.get('err_string'))
    elif response['cmd'] == 'token_auth_resp':    # Если ответ confirm_auth_resp
        if response['status']:
            print("Authentication confirmed.")
            # Добавьте вашу логику обработки сообщений здесь
        else:
            print("Failed to confirm authentication:", response.get('err_string'))
    elif response['cmd'] == 'console':
        get_data(ws)
    elif response['cmd'] == 'get_devices_resp':
        dev_list = response.get('devices_list')
        for i in dev_list:
            print({'devEui': i.get('devEui'),
                   'devName': i.get('devName')})
    else:
        print("Received message:", response)

def get_data(ws):
    message = {'cmd': 'get_devices_req'}
    ws.send(json.dumps(message))

def on_error(ws, error):
    print(error)


def on_close(ws, close_status_code, close_msg):
    print("### closed ###")


def on_open(ws):
    auth_data = {
        'cmd': 'auth_req',
        'login': login,
        'password': password
    }
    ws.send(json.dumps(auth_data))


def confirm_auth(ws, token):
    confirm_data = {
        'cmd': 'token_auth_req',
        'token': token
    }
    ws.send(json.dumps(confirm_data))


if __name__ == '__main__':
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp(WS,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()
