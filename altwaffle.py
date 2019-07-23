import websocket
import threading
import time
import json
import random
import sys
import traceback

MASTER_ID = 0

class UpgradeDriver:
  def __init__(self):
    self.awaiting_upgrade = {}
    
  def tick(self):
    for user_id in self.awaiting_upgrade:
      if self.awaiting_upgrade[user_id] > 0:
        self.awaiting_upgrade[user_id] -= 1
        
  def check(self, user_id):
    if user_id not in self.awaiting_upgrade:
      return False
    if self.awaiting_upgrade[user_id] <= 0:
      return True
    return False
  
  def set(self, user_id, count):
    self.awaiting_upgrade[user_id] = count
  
  def init(self, user_id):
    self.set(int(user_id), 0)
  
  def add(self, user_id, count):
    self.awaiting_upgrade[user_id] += count
    
  def get(self, user_id):
    if user_id not in self.awaiting_upgrade:
      return 0
    return self.awaiting_upgrade[user_id]
    
class Bot(threading.Thread):
  def __init__(self, user_id, auth_key, thread_number, upgrade_driver, is_master = False):
    self.thread_number = thread_number
    self.user_id = user_id
    self.auth_key = auth_key  
    
    self.is_master = is_master
    if not self.is_master:
      self.upgrade_driver = upgrade_driver      
  
    super(Bot, self).__init__()
    
  def log(self, message):
    print("[{}] id{} on thread#{}: {}".format(time.strftime("%x %X"), self.user_id, self.thread_number, message))
    
  def websocket_read(self):
    message = self.websocket_driver.recv()
    message = json.loads(message)
    self.log("got message: {}.".format(message))
    return message
  
  def run(self):
    self.log("starting a new thread...")   
    
    self.websocket_connect()
    answer = json.dumps({"action": "connect", "vk_id": self.user_id, "auth_key": self.auth_key})
    self.websocket_driver.send(answer)
    
    try:
      while True:
        message = self.websocket_read()
        
        clicks = random.randint(50, 100)
        
        if not self.is_master:
          if "action" in message:
            action = message["action"]
            if action == "info":
              info = message["msg"]
              if info == "Недостаточно монет":
                self.upgrade_driver.add(self.user_id, 50)
            elif action == "buy":
              if message["new_upd_price"] > float(message["balance"]):
                self.upgrade_driver.add(self.user_id, 100)
      
          if self.upgrade_driver.check(self.user_id):
            answer = json.dumps({"action":"buy", "buy": random.choice([10, 13]), "clicks":100,"vk_id": self.user_id, "auth_key": self.auth_key, "opened_page":"buy"})
            self.log("attempt to buy.")
            self.websocket_driver.send(answer)
            message = self.websocket_read()
         
        if "balance" in message:
          balance = float(message["balance"])                  
          if balance > 10 and self.user_id != MASTER_ID:
            answer = json.dumps({"action": "send", "to": MASTER_ID, "clicks": clicks, "sum": "10", "vk_id": self.user_id, "auth_key": self.auth_key, "opened_page":"tran"})
            self.websocket_driver.send(answer)           
            self.log("send out to master.")   
            message = self.websocket_read()            
        
        answer = json.dumps({"action": "ping", "clicks": clicks, "vk_id": self.user_id, "auth_key": self.auth_key, "opened_page":"none"})
        self.log("do clicks: {}.".format(clicks))
        self.websocket_driver.send(answer)
      
        if not self.is_master:
          self.log("do tick.")
          self.upgrade_driver.tick()
      
        time.sleep(1)
    except Exception as e:
      self.log("exception: {}".format(e))
      
      time.sleep(5)
      self.log("connection closed, reconnecting...")
      return self.run()    
    
  def websocket_connect(self):
    self.log("doing a connection...")
    self.websocket_driver = websocket.create_connection("wss://game.altvkcoin.ru/ws/")
    
    
if __name__ == "__main__":
  upgrade_driver = UpgradeDriver()
  if len(sys.argv) < 2:
    print("usage: з.py <accounts>")
    sys.exit(1)
  
  name = sys.argv[1]
  thread_number = 1
  try: 
    with open(name, 'r') as accounts:
      first = True
      for line in accounts.readlines():
        if len(line) <= 0:
          continue
        if line[0] == '#':
          continue
        account = line.strip().split(" ")
        upgrade_driver.init(account[0])
        
        thread = Bot(account[0], account[1], thread_number, upgrade_driver, first)
        thread.start()
        
        if first:
          MASTER_ID = account[0]
          first = False
        thread_number += 1
  except Exception as e:
    print("fail: {}".format(e))
    traceback.print_last()
    sys.exit(1)