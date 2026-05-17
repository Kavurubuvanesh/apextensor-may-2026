import socket
import sys
import getopt
import os
import time
import threading
import replicate
import math
import json
import re
from dotenv import load_dotenv

# Load the secret API key from your .env file
load_dotenv()
PI= 3.14159265359

data_size = 2**17

ophelp=  'Options:\n'
ophelp+= ' --host, -H <host>    TORCS server host. [localhost]\n'
ophelp+= ' --port, -p <port>    TORCS port. [3001]\n'
ophelp+= ' --id, -i <id>        ID for server. [SCR]\n'
ophelp+= ' --steps, -m <#>      Maximum simulation steps. 1 sec ~ 50 steps. [100000]\n'
ophelp+= ' --episodes, -e <#>   Maximum learning episodes. [1]\n'
ophelp+= ' --track, -t <track>  Your name for this track. Used for learning. [unknown]\n'
ophelp+= ' --stage, -s <#>      0=warm up, 1=qualifying, 2=race, 3=unknown. [3]\n'
ophelp+= ' --debug, -d          Output full telemetry.\n'
ophelp+= ' --help, -h           Show this help.\n'
ophelp+= ' --version, -v        Show current version.'
usage= 'Usage: %s [ophelp [optargs]] \n' % sys.argv[0]
usage= usage + ophelp
version= "20130505-2"

def clip(v,lo,hi):
    if v<lo: return lo
    elif v>hi: return hi
    else: return v

def bargraph(x,mn,mx,w,c='X'):
    if not w: return '' 
    if x<mn: x= mn      
    if x>mx: x= mx      
    tx= mx-mn 
    if tx<=0: return 'backwards' 
    upw= tx/float(w) 
    if upw<=0: return 'what?' 
    negpu, pospu, negnonpu, posnonpu= 0,0,0,0
    if mn < 0: 
        if x < 0: 
            negpu= -x + min(0,mx)
            negnonpu= -mn + x
        else: 
            negnonpu= -mn + min(0,mx) 
    if mx > 0: 
        if x > 0: 
            pospu= x - max(0,mn)
            posnonpu= mx - x
        else: 
            posnonpu= mx - max(0,mn) 
    nnc= int(negnonpu/upw)*'-'
    npc= int(negpu/upw)*c
    ppc= int(pospu/upw)*c
    pnc= int(posnonpu/upw)*'_'
    return '[%s]' % (nnc+npc+ppc+pnc)

class Client():
    def __init__(self,H=None,p=None,i=None,e=None,t=None,s=None,d=None,vision=False):
        self.vision = vision
        self.host= 'localhost'
        self.port= 3001
        self.sid= 'SCR'
        self.maxEpisodes=1 
        self.trackname= 'unknown'
        self.stage= 3 
        self.debug= False
        self.maxSteps= 100000  
        self.parse_the_command_line()
        if H: self.host= H
        if p: self.port= p
        if i: self.sid= i
        if e: self.maxEpisodes= e
        if t: self.trackname= t
        if s: self.stage= s
        if d: self.debug= d
        self.S= ServerState()
        self.R= DriverAction()
        self.setup_connection()

    def setup_connection(self):
        try:
            self.so= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except socket.error as emsg:
            print('Error: Could not create socket...')
            sys.exit(-1)
        self.so.settimeout(1)

        n_fail = 5
        while True:
            a= "-45 -19 -12 -7 -4 -2.5 -1.7 -1 -.5 0 .5 1 1.7 2.5 4 7 12 19 45"
            initmsg='%s(init %s)' % (self.sid,a)

            try:
                self.so.sendto(initmsg.encode(), (self.host, self.port))
            except socket.error as emsg:
                sys.exit(-1)
            sockdata= str()
            try:
                sockdata,addr= self.so.recvfrom(data_size)
                sockdata = sockdata.decode('utf-8')
            except socket.error as emsg:
                print("Waiting for server on %d............" % self.port)
                print("Count Down : " + str(n_fail))
                if n_fail < 0:
                    print("relaunch torcs")
                    os.system('pkill torcs')
                    time.sleep(1.0)
                    if self.vision is False:
                        os.system('torcs -nofuel -nodamage -nolaptime &')
                    else:
                        os.system('torcs -nofuel -nodamage -nolaptime -vision &')
                    time.sleep(1.0)
                    os.system('sh autostart.sh')
                    n_fail = 5
                n_fail -= 1

            identify = '***identified***'
            if identify in sockdata:
                print("Client connected on %d.............." % self.port)
                break

    def parse_the_command_line(self):
        try:
            (opts, args) = getopt.getopt(sys.argv[1:], 'H:p:i:m:e:t:s:dhv',
                       ['host=','port=','id=','steps=',
                        'episodes=','track=','stage=',
                        'debug','help','version'])
        except getopt.error as why:
            print('getopt error: %s\n%s' % (why, usage))
            sys.exit(-1)
        try:
            for opt in opts:
                if opt[0] == '-h' or opt[0] == '--help':
                    print(usage)
                    sys.exit(0)
                if opt[0] == '-d' or opt[0] == '--debug':
                    self.debug= True
                if opt[0] == '-H' or opt[0] == '--host':
                    self.host= opt[1]
                if opt[0] == '-i' or opt[0] == '--id':
                    self.sid= opt[1]
                if opt[0] == '-t' or opt[0] == '--track':
                    self.trackname= opt[1]
                if opt[0] == '-s' or opt[0] == '--stage':
                    self.stage= int(opt[1])
                if opt[0] == '-p' or opt[0] == '--port':
                    self.port= int(opt[1])
                if opt[0] == '-e' or opt[0] == '--episodes':
                    self.maxEpisodes= int(opt[1])
                if opt[0] == '-m' or opt[0] == '--steps':
                    self.maxSteps= int(opt[1])
                if opt[0] == '-v' or opt[0] == '--version':
                    print('%s %s' % (sys.argv[0], version))
                    sys.exit(0)
        except ValueError as why:
            print('Bad parameter \'%s\' for option %s: %s\n%s' % (
                                       opt[1], opt[0], why, usage))
            sys.exit(-1)
        if len(args) > 0:
            print('Superflous input? %s\n%s' % (', '.join(args), usage))
            sys.exit(-1)

    def get_servers_input(self):
        if not self.so: return
        sockdata= str()

        while True:
            try:
                sockdata,addr= self.so.recvfrom(data_size)
                sockdata = sockdata.decode('utf-8')
            except socket.error as emsg:
                print('.', end=' ')
            if '***identified***' in sockdata:
                print("Client connected on %d.............." % self.port)
                continue
            elif '***shutdown***' in sockdata:
                print((("Server has stopped the race on %d. "+
                        "You were in %d place.") %
                        (self.port,self.S.d.get('racePos', 0))))
                self.shutdown()
                return
            elif '***restart***' in sockdata:
                print("Server has restarted the race on %d." % self.port)
                self.shutdown()
                return
            elif not sockdata: 
                continue       
            else:
                self.S.parse_server_str(sockdata)
                if self.debug:
                    sys.stderr.write("\x1b[2J\x1b[H") 
                    print(self.S.fancyout())
                break 

    def respond_to_server(self):
        if not self.so: return
        try:
            message = repr(self.R)
            self.so.sendto(message.encode(), (self.host, self.port))
        except socket.error as emsg:
            print("Error sending to server: %s Message %s" % (emsg[1],str(emsg[0])))
            sys.exit(-1)
        if self.debug: print(self.R.fancyout())

    def shutdown(self):
        if not self.so: return
        print(("Race terminated or %d steps elapsed. Shutting down %d."
               % (self.maxSteps,self.port)))
        self.so.close()
        self.so = None

class ServerState():
    def __init__(self):
        self.servstr= str()
        self.d= dict()

    def parse_server_str(self, server_string):
        self.servstr= server_string.strip()[:-1]
        sslisted= self.servstr.strip().lstrip('(').rstrip(')').split(')(')
        for i in sslisted:
            w= i.split(' ')
            self.d[w[0]]= destringify(w[1:])

    def __repr__(self):
        return self.fancyout()

    def fancyout(self):
        out= str()
        sensors= [ 
        'stucktimer',
        'fuel',
        'distRaced',
        'distFromStart',
        'opponents',
        'wheelSpinVel',
        'z',
        'speedZ',
        'speedY',
        'speedX',
        'targetSpeed',
        'rpm',
        'skid',
        'slip',
        'track',
        'trackPos',
        'angle',
        ]

        for k in sensors:
            if type(self.d.get(k)) is list: 
                if k == 'track': 
                    strout= str()
                    raw_tsens= ['%.1f'%x for x in self.d['track']]
                    strout+= ' '.join(raw_tsens[:9])+'_'+raw_tsens[9]+'_'+' '.join(raw_tsens[10:])
                elif k == 'opponents': 
                    strout= str()
                    for osensor in self.d['opponents']:
                        if   osensor >190: oc= '_'
                        elif osensor > 90: oc= '.'
                        elif osensor > 39: oc= chr(int(osensor/2)+97-19)
                        elif osensor > 13: oc= chr(int(osensor)+65-13)
                        elif osensor >  3: oc= chr(int(osensor)+48-3)
                        else: oc= '?'
                        strout+= oc
                    strout= ' -> '+strout[:18] + ' ' + strout[18:]+' <-'
                else:
                    strlist= [str(i) for i in self.d.get(k, [])]
                    strout= ', '.join(strlist)
            else: 
                if k == 'gear': 
                    gs= '_._._._._._._._._'
                    p= int(self.d.get('gear', 0)) * 2 + 2  
                    l= '%d'%self.d.get('gear', 0) 
                    if l=='-1': l= 'R'
                    if l=='0':  l= 'N'
                    strout= gs[:p]+ '(%s)'%l + gs[p+3:]
                elif k == 'damage':
                    strout= '%6.0f %s' % (self.d.get(k, 0), bargraph(self.d.get(k, 0),0,10000,50,'~'))
                elif k == 'fuel':
                    strout= '%6.0f %s' % (self.d.get(k, 0), bargraph(self.d.get(k, 0),0,100,50,'f'))
                elif k == 'speedX':
                    cx= 'X'
                    if self.d.get(k, 0)<0: cx= 'R'
                    strout= '%6.1f %s' % (self.d.get(k, 0), bargraph(self.d.get(k, 0),-30,300,50,cx))
                elif k == 'speedY': 
                    strout= '%6.1f %s' % (self.d.get(k, 0), bargraph(self.d.get(k, 0)*-1,-25,25,50,'Y'))
                elif k == 'speedZ':
                    strout= '%6.1f %s' % (self.d.get(k, 0), bargraph(self.d.get(k, 0),-13,13,50,'Z'))
                elif k == 'z':
                    strout= '%6.3f %s' % (self.d.get(k, 0), bargraph(self.d.get(k, 0),.3,.5,50,'z'))
                elif k == 'trackPos': 
                    cx='<'
                    if self.d.get(k, 0)<0: cx= '>'
                    strout= '%6.3f %s' % (self.d.get(k, 0), bargraph(self.d.get(k, 0)*-1,-1,1,50,cx))
                elif k == 'stucktimer': # CRITICAL BUG FIX APPLIED HERE
                    stuck_val = self.d.get(k)
                    if stuck_val:
                        strout= '%3d %s' % (stuck_val, bargraph(stuck_val,0,300,50,"'"))
                    else: strout= 'Not stuck!'
                elif k == 'rpm':
                    g= self.d.get('gear', 0)
                    if g < 0:
                        g= 'R'
                    else:
                        g= '%1d'% g
                    strout= bargraph(self.d.get(k, 0),0,10000,50,g)
                elif k == 'angle':
                    asyms= [
                          "  !  ", ".|'  ", "./'  ", "_.-  ", ".--  ", "..-  ",
                          "---  ", ".__  ", "-._  ", "'-.  ", "'\.  ", "'|.  ",
                          "  |  ", "  .|'", "  ./'", "  .-'", "  _.-", "  __.",
                          "  ---", "  --.", "  -._", "  -..", "  '\.", "  '|."  ]
                    rad= self.d.get(k, 0)
                    deg= int(rad*180/PI)
                    symno= int(.5+ (rad+PI) / (PI/12) )
                    symno= symno % (len(asyms)-1)
                    strout= '%5.2f %3d (%s)' % (rad,deg,asyms[symno])
                elif k == 'skid': 
                    frontwheelradpersec= self.d.get('wheelSpinVel', [0])[0]
                    skid= 0
                    if frontwheelradpersec:
                        skid= .5555555555*self.d.get('speedX', 0)/frontwheelradpersec - .66124
                    strout= bargraph(skid,-.05,.4,50,'*')
                elif k == 'slip': 
                    frontwheelradpersec= self.d.get('wheelSpinVel', [0])[0]
                    slip= 0
                    if frontwheelradpersec and len(self.d.get('wheelSpinVel', [])) >= 4:
                        slip= ((self.d['wheelSpinVel'][2]+self.d['wheelSpinVel'][3]) -
                              (self.d['wheelSpinVel'][0]+self.d['wheelSpinVel'][1]))
                    strout= bargraph(slip,-5,150,50,'@')
                else:
                    strout= str(self.d.get(k, ''))
            out+= "%s: %s\n" % (k,strout)
        return out

class DriverAction():
    def __init__(self):
       self.actionstr= str()
       self.d= { 'accel':0.2,
                   'brake':0,
                  'clutch':0,
                    'gear':1,
                   'steer':0,
                   'focus':[-90,-45,0,45,90],
                    'meta':0
                    }

    def clip_to_limits(self):
        self.d['steer']= clip(self.d['steer'], -1, 1)
        self.d['brake']= clip(self.d['brake'], 0, 1)
        self.d['accel']= clip(self.d['accel'], 0, 1)
        self.d['clutch']= clip(self.d['clutch'], 0, 1)
        if self.d['gear'] not in [-1, 0, 1, 2, 3, 4, 5, 6]:
            self.d['gear']= 0
        if self.d['meta'] not in [0,1]:
            self.d['meta']= 0
        if type(self.d['focus']) is not list or min(self.d['focus'])<-180 or max(self.d['focus'])>180:
            self.d['focus']= 0

    def __repr__(self):
        self.clip_to_limits()
        out= str()
        for k in self.d:
            out+= '('+k+' '
            v= self.d[k]
            if not type(v) is list:
                out+= '%.3f' % v
            else:
                out+= ' '.join([str(x) for x in v])
            out+= ')'
        return out

    def fancyout(self):
        out= str()
        od= self.d.copy()
        od.pop('gear','') 
        od.pop('meta','') 
        od.pop('focus','') 
        for k in sorted(od):
            if k == 'clutch' or k == 'brake' or k == 'accel':
                strout=''
                strout= '%6.3f %s' % (od[k], bargraph(od[k],0,1,50,k[0].upper()))
            elif k == 'steer': 
                strout= '%6.3f %s' % (od[k], bargraph(od[k]*-1,-1,1,50,'S'))
            else:
                strout= str(od[k])
            out+= "%s: %s\n" % (k,strout)
        return out

def destringify(s):
    if not s: return s
    if type(s) is str:
        try:
            return float(s)
        except ValueError:
            print("Could not find a value in %s" % s)
            return s
    elif type(s) is list:
        if len(s) < 2:
            return destringify(s[0])
        else:
            return [destringify(i) for i in s]

#############################################
# MODULAR DRIVE LOGIC WITH USER PARAMETERS  #
#############################################

# ================= USER CONFIGURABLE PARAMETERS =================
TARGET_SPEED = 50  
STEER_GAIN = 40     
CENTERING_GAIN = 0.40  
BRAKE_THRESHOLD = 0.5  
GEAR_SPEEDS = [0, 20, 40, 80, 100, 180]  
ENABLE_TRACTION_CONTROL = True
TARGET_LANE = 0.0
# --- PID CONTROL STATE ---
STEERING_INTEGRAL = 0.0
PREV_STEERING_ERROR = 0.0 

# --- PIT-WALL AI STRATEGIST (MULTI-THREADED JSON BRAIN) ---
LAST_AI_CALL = 0  
RADIO_IS_BUSY = False  
IS_FIRST_BOOT = True  

# NEW: THE TEMPORAL CONTEXT BUFFER
TELEMETRY_HISTORY = []  # Stores the last 3 AI decisions to calculate momentum  

# STATE MACHINE FOR RECOVERY
RECOVERY_STATE = 0  

CURRENT_STRATEGY_PARAMS = {
    "TARGET_SPEED": 80.0,
    "BRAKE_THRESHOLD": 0.5,
    "CENTERING_GAIN": 0.5,
    "TARGET_LANE": 0.0
}

# CLOUD STRATEGY ENGINE
def fetch_strategy_from_cloud(current_speed, track_position, track_radar, opponent_radar):
    global CURRENT_STRATEGY_PARAMS, RADIO_IS_BUSY, IS_FIRST_BOOT, TELEMETRY_HISTORY
    
    distance_ahead = track_radar[9] if len(track_radar) > 9 else 200
    safe_distance = 0 if distance_ahead == -1 else distance_ahead
    
    if len(opponent_radar) >= 36:
        center_opp = min(opponent_radar[0], opponent_radar[1], opponent_radar[35])
        left_opp = min(opponent_radar[2:6])
        right_opp = min(opponent_radar[30:34])
    else:
        center_opp = left_opp = right_opp = 200

    if IS_FIRST_BOOT:
        print("\n[PIT-WALL] Cloud AI is booting (Takes 60-90s). Local Sub-Brain taking control of the race...\n")

    # Format the Temporal Memory Buffer for the AI
    history_text = "No history available (System Booting)."
    if TELEMETRY_HISTORY:
        history_text = ""
        for idx, (h_spd, h_pos, h_cmd) in enumerate(TELEMETRY_HISTORY):
            history_text += f"   - T-minus {(idx+1)*12.5}s: Speed {h_spd:.1f}, Pos {h_pos:.2f} | Commanded Speed: {h_cmd:.1f}\n"

    # UPGRADED PROMPT: Now includes Time Context and Predictive Drift rules
    prompt = f"""
    You are an advanced autonomous racing AI.
    
    CURRENT STATE:
    Speed: {current_speed:.1f} km/h | Track Position: {track_position:.2f} (-1 left, 1 right, 0 center)
    Clear Track Ahead: {safe_distance:.1f}m
    Opponents - Left: {left_opp:.1f}m | Center: {center_opp:.1f}m | Right: {right_opp:.1f}m

    TEMPORAL MEMORY (Past 3 Cycles):
    {history_text}

    STRATEGY RULES:
    1. target_speed: If Clear Track > 120m AND Center Opponent > 80m, value is 140.0. If Center Opponent < 50m, value is 90.0. If Clear Track < 60m, value is 40.0.
    2. target_lane: If Center Opponent < 60m, value is 0.5 if Right space > Left space, or -0.5 if Left space > Right space. Otherwise, value is 0.0.
    3. brake_threshold & centering_gain: 0.9 and 0.15 for straights. 0.3 and 0.9 for sharp turns.
    4. PREDICTIVE MOMENTUM: Look at the Temporal Memory. If your past positions show you drifting further away from 0.0 over time, you MUST increase centering_gain to 0.8 to stop the slide.

    Output ONLY a valid JSON object. Replace the brackets with your calculated numbers:
    {{"target_speed": [speed], "brake_threshold": [brake], "centering_gain": [gain], "target_lane": [lane]}}
    """
    
    try:
        output = replicate.run(
            "ibm-granite/granite-3.1-8b-instruct", 
            input={"prompt": prompt, "max_tokens": 200}
        )
        response_text = "".join(output).strip()
        
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            json_str = match.group(0)
            data = json.loads(json_str)
            
            CURRENT_STRATEGY_PARAMS["TARGET_SPEED"] = float(data.get("target_speed", 80))
            CURRENT_STRATEGY_PARAMS["BRAKE_THRESHOLD"] = float(data.get("brake_threshold", 0.5))
            CURRENT_STRATEGY_PARAMS["CENTERING_GAIN"] = float(data.get("centering_gain", 0.5))
            CURRENT_STRATEGY_PARAMS["TARGET_LANE"] = float(data.get("target_lane", 0.0))
            
            # UPGRADE 2: Update the Temporal Memory Buffer
            TELEMETRY_HISTORY.insert(0, (current_speed, track_position, CURRENT_STRATEGY_PARAMS["TARGET_SPEED"]))
            if len(TELEMETRY_HISTORY) > 3:  # Only keep the last 3 cycles (37.5 seconds of memory)
                TELEMETRY_HISTORY.pop()
            
            IS_FIRST_BOOT = False 
            print(f"\n[PIT-WALL] Clear: {safe_distance:.0f}m | Pos: {track_position:.2f} | AI Speed Commanded: {CURRENT_STRATEGY_PARAMS['TARGET_SPEED']}\n")
        else:
            print(f"\n[PIT-WALL] Invalid Payload Format Received: {response_text}\n")
            
    except Exception as e:
        print(f"\n[PIT-WALL] RADIO INTERFERENCE (API Error): {e}\n")
    finally:
        RADIO_IS_BUSY = False

def ask_pit_wall_async(current_speed, track_position, track_radar, opponent_radar):
    global LAST_AI_CALL, RADIO_IS_BUSY
    current_time = time.time()
    
    if current_time - LAST_AI_CALL < 12.5 or RADIO_IS_BUSY:
        return 
        
    LAST_AI_CALL = current_time
    RADIO_IS_BUSY = True  
    
    thread = threading.Thread(target=fetch_strategy_from_cloud, args=(current_speed, track_position, track_radar, opponent_radar))
    thread.daemon = True
    thread.start()

# ================= HELPER FUNCTIONS =================
def calculate_steering(S):
    global TARGET_LANE, CENTERING_GAIN, STEERING_INTEGRAL, PREV_STEERING_ERROR
    
    # 1. Spatial Error (Meters)
    lane_error = S.get('trackPos', 0) - TARGET_LANE
    
    # 2. PID Constants
    Kp = CENTERING_GAIN  
    Ki = 0.005           
    Kd = 0.3             
    
    # 3. Integral Calculus (Accumulate past drifting)
    STEERING_INTEGRAL += lane_error
    STEERING_INTEGRAL = max(-2.0, min(2.0, STEERING_INTEGRAL)) # Anti-windup
    
    # 4. Derivative Calculus (Predict future position)
    derivative = lane_error - PREV_STEERING_ERROR
    
    # 5. The Ultimate Steering Equation (Align nose, then apply PID correction)
    base_alignment = S.get('angle', 0) * 0.5 / math.pi
    pid_correction = (Kp * lane_error) + (Ki * STEERING_INTEGRAL) + (Kd * derivative)
    
    steer = base_alignment - pid_correction
    
    PREV_STEERING_ERROR = lane_error
    
    return max(-1.0, min(1.0, steer))

def calculate_pedals(S, target_speed, steer):
    current_speed = S.get('speedX', 0)
    speed_error = current_speed - target_speed
    
    accel = 0.0
    brake = 0.0
    
    # 1. Proportional Speed Control (Eliminates the stutter)
    if speed_error > 3.0:
        # Too fast: Apply smooth braking proportional to how fast we are going
        brake = min(1.0, speed_error / 25.0) 
    elif speed_error < -2.0:
        # Too slow: Apply smooth acceleration
        accel = min(1.0, abs(speed_error) / 15.0)
    else:
        # Coasting Zone: If we are exactly at the target speed, just maintain momentum
        accel = 0.05
        
    # 2. Trail Braking (Add a tiny bit of brake if we are turning hard to shift weight to the front tires)
    if abs(steer) > 0.2 and current_speed > 40:
        brake = max(brake, abs(steer) * 0.3)

    # 3. Dynamic Traction Control (Friction Circle)
    wheel_speeds = S.get('wheelSpinVel', [0, 0, 0, 0])
    if len(wheel_speeds) >= 4 and accel > 0:
        front_speed = (wheel_speeds[0] + wheel_speeds[1]) / 2.0
        rear_speed = (wheel_speeds[2] + wheel_speeds[3]) / 2.0
        slip_delta = rear_speed - front_speed
        
        max_allowed_slip = max(0.5, 2.5 - (abs(steer) * 2.0))
        if slip_delta > max_allowed_slip:
            # Smoothly roll off the throttle if tires start spinning
            accel = max(0.0, accel - ((slip_delta - max_allowed_slip) * 0.3))
            
    return accel, brake

def shift_gears(S):
    gear = 1
    GEAR_SPEEDS = [40, 80, 120, 160, 200]
    for i, speed in enumerate(GEAR_SPEEDS):
        if S.get('speedX', 0) > speed:
            gear = i + 1
    return min(gear, 6)


# ================= MAIN DRIVE FUNCTION =================
def drive_modular(c):
    global TARGET_SPEED, BRAKE_THRESHOLD, CENTERING_GAIN, TARGET_LANE, RECOVERY_STATE
    
    S, R = c.S.d, c.R.d
    current_speed = S.get('speedX', 0)
    track_radar = S.get('track', [200] * 19)
    distance_ahead = track_radar[9] if len(track_radar) > 9 else 200
    
    # ---------------------------------------------------------
    # SYSTEM 1: 3-PHASE KINEMATIC RECOVERY MACHINE
    # ---------------------------------------------------------
    if RECOVERY_STATE > 0:
        if RECOVERY_STATE > 80:
            R['gear'] = 1; R['brake'] = 1.0; R['accel'] = 0.0; R['steer'] = 0.0
        elif RECOVERY_STATE > 40:
            R['gear'] = -1; R['brake'] = 0.0; R['accel'] = 0.8
            R['steer'] = math.copysign(1.0, S.get('trackPos', 0)) 
        else:
            R['gear'] = 1; R['brake'] = 0.0; R['accel'] = 0.8
            R['steer'] = -math.copysign(1.0, S.get('trackPos', 0)) 
            
        RECOVERY_STATE -= 1
        return  
    
    # ---------------------------------------------------------
    # SYSTEM 2: TELEMETRY & SUB-BRAIN PROTOCOL
    # ---------------------------------------------------------
    opponent_radar = S.get('opponents', [200] * 36)
    ask_pit_wall_async(current_speed, S.get('trackPos', 0), track_radar, opponent_radar)
    
    if IS_FIRST_BOOT:
        # THE DETERMINISTIC SUB-BRAIN: Actively race while waiting for the cloud
        TARGET_SPEED = min(100.0, max(30.0, distance_ahead * 0.8)) # Dynamic radar speed
        BRAKE_THRESHOLD = 0.5
        CENTERING_GAIN = 0.8
        TARGET_LANE = 0.0
    else:
        # THE HARDWARE GOVERNOR: Cap the AI
        ai_speed = CURRENT_STRATEGY_PARAMS.get("TARGET_SPEED", 80)
        TARGET_SPEED = min(120.0, ai_speed)  
        BRAKE_THRESHOLD = CURRENT_STRATEGY_PARAMS.get("BRAKE_THRESHOLD", 0.5)
        CENTERING_GAIN = CURRENT_STRATEGY_PARAMS.get("CENTERING_GAIN", 0.5)
        TARGET_LANE = CURRENT_STRATEGY_PARAMS.get("TARGET_LANE", 0.0)

    # ---------------------------------------------------------
    # SYSTEM 4: PROPORTIONAL CORNERING (Replaces Bang-Bang Brakes)
    # ---------------------------------------------------------
    dynamic_brake_zone = max(50.0, current_speed * 0.8) 

    if distance_ahead < dynamic_brake_zone:
        # Smoothly roll off the target speed as we get closer to the wall
        speed_factor = max(0.3, distance_ahead / dynamic_brake_zone)
        TARGET_SPEED = TARGET_SPEED * speed_factor
        # Minimum cornering speed of 45 km/h so we NEVER crawl or stop
        TARGET_SPEED = max(45.0, TARGET_SPEED)
        CENTERING_GAIN = 1.0    
    elif abs(S.get('trackPos', 0)) > 0.75:
        # Off-track panic mode
        TARGET_SPEED = 40.0
        CENTERING_GAIN = 1.2

    # ---------------------------------------------------------
    # SYSTEM 5: STANDARD KINEMATICS
    # ---------------------------------------------------------
    R['steer'] = calculate_steering(S)
    
    # Fire the unified pedal matrix
    R['accel'], R['brake'] = calculate_pedals(S, TARGET_SPEED, R['steer'])
    
    R['gear'] = shift_gears(S)
    
    # TRIGGER 3-PHASE RECOVERY
    if current_speed < 3 and abs(S.get('trackPos', 0)) > 0.7:
        RECOVERY_STATE = 100  
        
    return

# ================= MAIN LOOP =================
if __name__ == "__main__":
    C = Client(p=3001)
    for step in range(C.maxSteps, 0, -1):
        C.get_servers_input()
        drive_modular(C)
        C.respond_to_server()
    C.shutdown()