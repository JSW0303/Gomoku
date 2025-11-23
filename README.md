# Gomoku
Python 기반 소켓 프로그래밍을 활용한 오목 게임. 클라이언트-서버 구조로 스레딩을 사용하여 다중 접속을 처리합니다.
## How to Run
1. Dependencies : Python
2. Installation steps : socket, threading, json 등은 Python 내장 모듈이므로 별도 설치 필요 없습니다.
3. Startup Commands

   프로젝트 폴더 내에서 powershell을 실행하여 아래 명령어를 입력합니다.
   
   서버 실행 명령어 - python server.py
   
   클라이언트 실행 명령어 - python client.py
   
   클라이언트 실행 명령어는 서버에 접속하는 인원 수만큼 반복 실행합니다. 플레이어1, 플레이어2, 관전자 모두 접속을 위해선 명령어를 3번 반복해야 합니다. 또한, 서버를 클라이언트보다 먼저 실행하여야 합니다.

4. Usage

   클라이언트 접속 후에 여러 명령어가 출력됩니다. list를 사용하여 생성된 방 목록을 확인할 수 있으며, create을 사용하여 방을 생성할 수 있습니다. join을 사용하여 생성된 방에 입장할 수 있습니다.

   방에 접속한 후에 게임이 시작되면 move 명령어를 사용하여 돌을 둘 수 있고, chat 명령어를 사용하여 채팅을 할 수 있습니다.

## Protocol Specification
### 1. 클라이언트 -> 서버

| Command | Format Example | Description |
| :--- | :--- | :--- |
| **list** | `{"type": "LIST_ROOMS"}` | 생성되어 있는 방 목록 출력 |
| **create** | `{"type": "CREATE_ROOM"}` | 신규 방 생성 및 자동입장 |
| **join** | `{"type": "JOIN_ROOM", "room_id": int(parts[1])}` | 생성되어 있는 방에 입장 요청 |
| **move**| `{"type": "PLACE_STONE", "x": int(coords[0]), "y": int(coords[1])}` | (x, y) 좌표에 수 두기 |
| **chat** | `{"type": "CHAT", "text": parts[1]}` | 채팅 전송 |

parts[1]은 명령어 type뒤에 오는 인수입니다. chat message의 경우 parts[0]는 chat, parts[1]은 message입니다.

### 2. 서버 -> 클라이언트

| Type | Format Example | Description |
| :--- | :--- | :--- |
| **ROOM_LIST** | `{"type": "ROOM_LIST", "rooms": room_list}` | 방 목록 전달 |
| **ROOM_JOINED**| `{"type": "ROOM_JOINED", "room_id": room_id, "player_id": my_role}` | 방 입장 및 역할(black/white/spectator) 할당 |
| **GAME_STATE_UPDATE** | `{"type": "GAME_STATE_UPDATE", "board": GAME_ROOMS[room_id]['board'], "turn": "black"}` | 관전자 중간 입장 시 현재 보드 상태 업데이트 |
| **MOVE_MADE** | `{"type": "MOVE_MADE", "x": x, "y": y, "player": my_role}` | 플레이어가 둔 수에 대한 참여자에게 전달 |
| **TURN_CHANGE**| `{"type": "TURN_CHANGE", "turn": room['turn']}` | 다음 턴 돌리기 |
| **STATUS** | `{"type": "STATUS", "msg": "게임종료 {my_role}의 승리!"}` | 게임 상태(시작, 종료, 승리) 알림 |
| **CHAT_MESSAGE**| `{"type": "CHAT_MESSAGE", "sender": my_role, "message": msg.get('text')}` | 채팅 메시지 수신 |
| **ERROR** | `{"type": "ERROR", "msg": "오류 : 둘 수 없는 수"}` | 유효하지 않은 명령 시 출력 |

## Features

1.  Game Rooms
   
    방을 생성(create)할 수 있고, 참여(join)할 수 있으며, 목록을 확인(list)할 수 있습니다. 또한, 최대 2명의 플레이어가 참여 가능합니다. 관전자는 계속 참여 가능합니다.

    
2.  Real-time Two-Player Gameplay
   
    15x15 오목 보드를 사용하며, 실시간으로 플레이어가 둔 수를 모든 플레이어와 관전자가 확인할 수 있습니다.
    
3.  Spectator Mode
 
    관전자가 게임을 실시간으로 관전하며, 중간 입장 시 `GAME_STATE_UPDATE` 프로토콜을 통해 현재 보드 상태를 동기화받습니다.

4. Game Mechanics

   서버가 수가 유효한지 검사하고, 턴을 돌리며, 승리 조건을 실시간으로 확인합니다.
   
    
5. Real-time Interaction & Chat
    플레이어와 관전자가 상대의 수를 실시간으로 확인할 수 있으며, 플레이어는 서로 실시간으로 채팅을 주고받을 수 있으며, 관전자는 이를 확인할 수 있습니다.
