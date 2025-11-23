import socket
import threading
import json

HOST = '127.0.0.1'
PORT = 9999
BOARD_SIZE = 15

GAME_ROOMS = {} 
ROOMS_LOCK = threading.Lock()
NEXT_ROOM_ID = 1

def send_message(conn, message_dict):
    try:
        message_json = json.dumps(message_dict) + '\n'
        conn.sendall(message_json.encode('utf-8'))
    except (ConnectionResetError, BrokenPipeError):
        pass
    except Exception as e:
        print(f"[Send Error] {e}")

def broadcast(room_id, message_dict):
    if room_id not in GAME_ROOMS: return
    room = GAME_ROOMS[room_id]
    all_connections = set(room['players'].values()) | set(room['spectators'])
    for conn in all_connections:
        send_message(conn, message_dict)

def check_win(board, x, y, stone):
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    for dx, dy in directions:
        count = 1 
        for i in range(1, 5):
            nx, ny = x + dx*i, y + dy*i
            if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[ny][nx] == stone: count += 1
            else: break
        for i in range(1, 5):
            nx, ny = x - dx*i, y - dy*i
            if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[ny][nx] == stone: count += 1
            else: break
        if count >= 5: return True
    return False


def handle_client(conn, addr):
    print(f"[New Connection] {addr} 연결됨.")
    
    current_room_id = None
    my_role = None 
    buffer = ""
    
    try:
        while True:
            data = conn.recv(1024).decode('utf-8')
            if not data: break
            buffer += data
            
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if not line: continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                msg_type = msg.get('type')

                if msg_type == 'LIST_ROOMS':
                    room_list = []
                    with ROOMS_LOCK:
                        for r_id, r in GAME_ROOMS.items():
                            room_list.append({
                                "id": r_id,
                                "count": len(r['players']),
                                "status": r['status']
                            })
                    send_message(conn, {"type": "ROOM_LIST", "rooms": room_list})

                elif msg_type == 'CREATE_ROOM':
                    with ROOMS_LOCK:
                        if current_room_id is not None:
                            send_message(conn, {"type": "ERROR", "msg": "오류 : 이미 방에 참여 중"})
                            continue

                        global NEXT_ROOM_ID
                        room_id = NEXT_ROOM_ID
                        NEXT_ROOM_ID += 1
                        
                        GAME_ROOMS[room_id] = {
                            'board': [['.' for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)],
                            'players': {'black': conn}, #
                            'spectators': [],
                            'turn': 'black',
                            'status': 'waiting'
                        }
                        
                        current_room_id = room_id
                        my_role = 'black'
                        
                        print(f"[Room {room_id}] 생성됨. Creator: {addr}")
                        send_message(conn, {"type": "ROOM_JOINED", "room_id": room_id, "player_id": my_role})
                        send_message(conn, {"type": "GAME_STATE_UPDATE", "board": GAME_ROOMS[room_id]['board'], "turn": 'black'})
                        broadcast(room_id, {"type": "STATUS", "msg": "대기실 생성됨."})

                elif msg_type == 'JOIN_ROOM':
                    room_id = msg.get('room_id')
                    
                    with ROOMS_LOCK:
                        if room_id not in GAME_ROOMS:
                            send_message(conn, {"type": "ERROR", "msg": "오류 : 생성되지 않은 방."})
                            continue
                            
                        room = GAME_ROOMS[room_id]
                        
                        if conn in room['players'].values() or conn in room['spectators']:
                             send_message(conn, {"type": "ERROR", "msg": "오류 : 이미 방에 참여 중."})
                             continue

                        if 'black' not in room['players']:
                            my_role = 'black'
                            room['players']['black'] = conn
                        elif 'white' not in room['players']:
                            my_role = 'white'
                            room['players']['white'] = conn
                        else:
                            my_role = 'spectator'
                            room['spectators'].append(conn)
                        
                        current_room_id = room_id
                        
                        send_message(conn, {"type": "ROOM_JOINED", "room_id": room_id, "player_id": my_role})
                        send_message(conn, {"type": "GAME_STATE_UPDATE", "board": room['board'], "turn": room['turn']})
                        
                        if room['status'] == 'waiting' and len(room['players']) == 2:
                            room['status'] = 'playing'
                            broadcast(room_id, {"type": "STATUS", "msg": "게임 시작. 흑돌 턴."})
                        else:
                            broadcast(room_id, {"type": "STATUS", "msg": f"'{my_role}'가 방에 참여함."})

                elif msg_type == 'PLACE_STONE':
                    if not current_room_id or my_role not in ('black', 'white'):
                        send_message(conn, {"type": "ERROR", "msg": "오류 : 플레이어만 수를 둘 수 있음."}); continue
                    x, y = msg.get('x'), msg.get('y')
                    with ROOMS_LOCK:
                        room = GAME_ROOMS.get(current_room_id)
                        if not room: continue
                        if room['status'] != 'playing':
                            send_message(conn, {"type": "ERROR", "msg": "오류 : 게임 진행 중 아님."}); continue
                        if room['turn'] != my_role:
                            send_message(conn, {"type": "ERROR", "msg": "오류 : 당신의 턴 아님."}); continue
                        if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE) or room['board'][y][x] != '.':
                            send_message(conn, {"type": "ERROR", "msg": "오류 : 둘 수 없는 수."}); continue
                            
                        stone = 'B' if my_role == 'black' else 'W'
                        room['board'][y][x] = stone
                        broadcast(current_room_id, {"type": "MOVE_MADE", "x": x, "y": y, "player": my_role})
                        if check_win(room['board'], x, y, stone):
                            room['status'] = 'finished'
                            broadcast(current_room_id, {"type": "STATUS", "msg": f"게임 종료 {my_role}의 승리!"})
                        else:
                            room['turn'] = 'white' if my_role == 'black' else 'black'
                            broadcast(current_room_id, {"type": "TURN_CHANGE", "turn": room['turn']})

                elif msg_type == 'CHAT':
                    if not current_room_id:
                        send_message(conn, {"type": "ERROR", "msg": "오류 : 방에서만 채팅 가능."}); continue
                    if my_role in ('black', 'white'):
                        with ROOMS_LOCK:
                            broadcast(current_room_id, {"type": "CHAT_MESSAGE", "sender": my_role, "message": msg.get('text')})

    except Exception as e:
        print(f"[{addr}] 오류: {e}")
    finally:
        print(f"[{addr}] 연결 종료.")
        with ROOMS_LOCK:
            if current_room_id and current_room_id in GAME_ROOMS:
                room = GAME_ROOMS[current_room_id]
                if my_role in room['players'] and room['players'][my_role] == conn:
                    del room['players'][my_role]
                    if room['status'] == 'playing':
                        room['status'] = 'finished'
                        broadcast(current_room_id, {"type": "STATUS", "msg": f"플레이어 {my_role}가 떠나 게임이 종료되었습니다."})
                elif my_role == 'spectator' and conn in room['spectators']:
                    room['spectators'].remove(conn)
        conn.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((HOST, PORT))
        server.listen()
        print(f" 서버 실행 중 ({HOST}:{PORT}) ")
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except Exception as e:
        print(f"서버 오류: {e}")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()