import socket
import threading
import json
import sys

HOST = '127.0.0.1'
PORT = 9999
BOARD_SIZE = 15
client_board = [['.' for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

def print_board(board):
    print("\n" + "="*45)
    header = "   " + " ".join(f"{i:<2}" for i in range(BOARD_SIZE))
    print(header)
    for i, row in enumerate(board):
        row_str = " ".join(f"{cell:<2}" for cell in row)
        print(f"{i:>2} {row_str}")
    print("="*45)

def send_message(sock, message_dict):
    try:
        message_json = json.dumps(message_dict) + '\n'
        sock.sendall(message_json.encode('utf-8'))
    except Exception as e:
        print(f"\n[Error] 메시지 전송 실패: {e}")

def listen_to_server(client_socket):
    buffer = ""
    while True:
        try:
            data = client_socket.recv(2048).decode('utf-8')
            if not data:
                print("\n[System] 서버 연결 종료.")
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if not line: continue
                try:
                    handle_server_message(json.loads(line))
                except json.JSONDecodeError:
                    pass
        except Exception:
            break
    client_socket.close()
    sys.exit() 

def handle_server_message(msg):
    global client_board 
    print()

    msg_type = msg.get('type')

    if msg_type == 'ROOM_LIST':
        print("\n--- [ 방 목록 ] ---")
        rooms = msg.get('rooms', [])
        if not rooms:
            print("생성된 방 없음.")
        else:
            print(f"{'ID':<5} {'상태':<10} {'인원'}")
            print("------------------------------")
            for r in rooms:
                print(f"{r['id']:<5} {r['status']:<10} {r['count']}/2")
        print("-------------------")

    elif msg_type == 'ROOM_JOINED':
        print(f"{msg['room_id']}번 방에 '{msg['player_id']}'(으)로 입장함.")

    elif msg_type == 'GAME_STATE_UPDATE':
        client_board = msg['board']
        print("게임 상태 동기화.")
        print_board(client_board)
        print(f"{msg['turn']}의 턴.")

    elif msg_type == 'STATUS':
        print(f"[상태] {msg['msg']}")

    elif msg_type == 'MOVE_MADE':
        x, y, player = msg['x'], msg['y'], msg['player']
        stone = 'B' if player == 'black' else 'W'
        client_board[y][x] = stone
        print_board(client_board)
        print(f"[{player}]가 ({x}, {y})에 수를 두었음.")

    elif msg_type == 'TURN_CHANGE':
        print(f"{msg['turn']}의 턴.")

    elif msg_type == 'CHAT_MESSAGE':
        print(f"[{msg['sender']}]: {msg['message']}")

    elif msg_type == 'ERROR':
        print(f"[오류] {msg['msg']}")
    
    print("> ", end="", flush=True)

def start_client():
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        my_socket.connect((HOST, PORT))
    except Exception as e:
        print(f"서버 연결 실패: {e}")
        return

    threading.Thread(target=listen_to_server, args=(my_socket,), daemon=True).start()

    print("1. list             : 방 목록 보기")
    print("2. create           : 방 생성하기")
    print("3. join [방ID]      : 방 참여하기")
    print("4. move [x] [y]     : 돌 두기")
    print("5. chat [메시지]    : 채팅")
    print("6. quit             : 종료")

    while True:
        try:
            user_input = input("> ")
            if not user_input: continue
            
            parts = user_input.split(' ', 1)
            command = parts[0].lower()

            if command == 'quit':
                break
            elif command == 'list':
                send_message(my_socket, {"type": "LIST_ROOMS"})
            elif command == 'create':
                send_message(my_socket, {"type": "CREATE_ROOM"})
            elif command == 'join':
                if len(parts) < 2: print("사용법 : join [방ID]"); continue
                try: send_message(my_socket, {"type": "JOIN_ROOM", "room_id": int(parts[1])})
                except: print("오류 : 방 ID는 숫자여야 함.")
            elif command == 'move':
                if len(parts) < 2: print("사용법 : move [x] [y]"); continue
                try:
                    coords = parts[1].split()
                    send_message(my_socket, {"type": "PLACE_STONE", "x": int(coords[0]), "y": int(coords[1])})
                except: print("좌표 오류.")
            elif command == 'chat':
                if len(parts) < 2: print("내용을 입력하세요."); continue
                send_message(my_socket, {"type": "CHAT", "text": parts[1]})
            else:
                print("알 수 없는 명령어.")
        except:
            break
    my_socket.close()

if __name__ == "__main__":
    start_client()