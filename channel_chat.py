#!/usr/bin/python
import sys
import socket
import threading
import logging
from time import sleep

# GLOBALS
logging.basicConfig(level=logging.INFO,
                    format='[%(levelname)s] (%(threadName)-10s) %(message)s',
                    )

BUFF_SIZE=1024
HOST='chat.roundtriptime.com'
PORT=11235
WELCOME='Welcome client '
FAREWELL='Farewell client '
EXIT_CODE='EXIT'
NAME_CODE='NAME'
CODE_LENGTH=4
CHANNEL_CODE='\r\nCHANNEL INFO: '

def client_channel(channel_client,client_list):
  logging.info('Joined the channel')
  exit_value=False
# receving client message
  while not exit_value:
    client_msg=''
    try:
      client_msg=channel_client.RecvMessage()
      logging.debug('try '+str(channel_client.GetID())+client_msg)
    except channel_client.GetError():
      logging.debug('except '+str(channel_client.GetID())+client_msg)
      channel_client.RemoveMessage(client_list)
      sleep(1)
    else:
      logging.debug('else '+str(channel_client.GetID())+client_msg)
      if len(client_msg) >= CODE_LENGTH:
        if client_msg[:len(EXIT_CODE)] == EXIT_CODE:
          exit_value = True
          channel_client.ChannelMessage(CHANNEL_CODE+channel_client.GetName()+' leaves the channel\r\n')
        elif client_msg[:len(NAME_CODE)] == NAME_CODE:
          channel_client.SetName(client_msg[(len(NAME_CODE)+1):(len(client_msg)-2)])
        else:
          logging.debug('Adding: '+client_msg)
          channel_client.AddMessage(client_msg)
      else:
        logging.debug('Adding: '+client_msg)
        channel_client.AddMessage(client_msg)
# sending other clients messages
    for peers in client_list:
      if peers.GetID() != channel_client.GetID() and not peers.GetIfEmptyMessage():
#        channel_client.SendMessage(peers.GetName()+': '+peers.GetMessage())
        channel_client.SendMessage(peers.GetMessage())
        peers.CountMessage()
  client_list.remove(channel_client)
  channel_client.SendMessage(FAREWELL+channel_client.GetName()+'\r\nHope to see you soon\r\n')
  channel_client.Close()
  return (True)


class Client:
  def __init__(self,client_handle,client_IP,client_ID,name='Anon'):
#    global in_message

    self.name=name
    self.client_handle=client_handle
    self.client_handle.setblocking(0)
    self.in_message=''
    self.empty_message=True
    self.count_message=0
    self.IP=client_IP
    self.ID=client_ID

  def GetIP(self):
    return self.IP

  def GetMessage(self):
    return self.in_message

  def GetName(self):
    return self.name

  def GetID(self):
    return self.ID

  def GetError(self):
    return socket.error
#    return self.client_handle.error
  
  def GetIfEmptyMessage(self):
    return self.empty_message

  def SetName(self,name_str):
    logging.debug('Name I '+name_str)
    self.ChannelMessage(CHANNEL_CODE+self.name+' changed into '+name_str+'\r\n')
    self.name=name_str
  
  def ChannelMessage(self,channel_str):
    self.in_message+=channel_str
    self.empty_message=False
    logging.debug('Ch_msg I '+self.in_message)

  def AddMessage(self,msg_str):
    logging.debug('Add I '+msg_str)
    if msg_str[:2] != '\r\n':
      logging.debug('Add II ')
      self.in_message+=self.name+': '+msg_str
      self.empty_message=False
    return (len(self.in_message))

  def RemoveMessage(self,client_list):
    logging.debug('Remove I '+str(self.count_message)+' '+str(len(client_list)))
    if self.count_message == (len(client_list)-1):
      logging.debug('Remove II ')
      self.in_message=''
      self.count_message=0
      self.empty_message=True
    return self.count_message

  def SendMessage(self,msg_str):
    self.client_handle.send(bytes(msg_str,'utf-8'))
    logging.debug('send msg'+str(self.ID))

  def RecvMessage(self):
    return str(self.client_handle.recv(BUFF_SIZE),'utf-8')
    logging.debug('recv msg'+str(self.ID))

  def CountMessage(self):
    self.count_message+=1

  def SetBlocking(self,state):
    self.client_handle.setblocking(state)

  def Close(self):
    self.client_handle.close()


class Channel:
  def __init__(self):
    global channel_threads,sck
    
# initialize chat-server
    channel_threads=[]
    sck=socket.socket()
    SERVER=(socket.gethostbyname(HOST),PORT)
    sck.bind(SERVER)
    sck.listen(5)

  def EndOfWork(self):
    for channel in channel_threads:
      channel.join(1)
    logging.shutdown()
    sck.shutdown()
    sck.close()
    return (True)

  def CoreLoop(self):
    client_list=[]
    client_ID=0
    peers_message=''
# petlja za cekanje i aktiviranje klijenata
    while True:
      (client_handle, client_IP) = sck.accept()
      client_ID=client_ID+1
      cl=Client(client_handle, client_IP, client_ID,"User#"+str(client_ID))
      client_list.append(cl)
# pokretanje novog threada
      channel=threading.Thread(name='User#'+str(client_IP),target=client_channel, args=(cl, client_list,))
      channel_threads.append(channel)
      channel.start()
# welcoming notes
      client_handle.send(bytes(WELCOME+'User#'+str(client_ID)+'\r\nType '+EXIT_CODE+' to end\r\nType '+NAME_CODE+' <chosen name> to 
identify yourself\r\n','utf-8'))
      peers_message=''
      for peers in client_list:
        peers_message+=str(peers.GetName())+' '
      client_handle.send(bytes('Currently on channel: '+peers_message+'\r\n','utf-8'))
    return (True)


ch=Channel()
ch.CoreLoop()
ch.EndOfWork()