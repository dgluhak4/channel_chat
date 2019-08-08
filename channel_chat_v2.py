#!/usr/bin/python
import sys
import socket
import threading
import logging
import random
from time import sleep

# GLOBALS
logging.basicConfig(level=logging.INFO,
                    format='[%(levelname)s] (%(threadName)-10s) %(message)s',
                   )

### channel/service network parameters
BUFF_SIZE = 2048
#HOST = 'chat.roundtriptime.com'
HOST = sys.argv[1]
LOCALHOST = '127.0.0.1'
PORT = 11235

client_ID = random.randrange(10001,99999)

### message static values definitions 
WELCOME = 'Welcome client '
FAREWELL = 'Farewell client '
CHANNEL_CODE = '\r\nCHANNEL INFO: '

### channel command definitions
EXIT_CODE = 'EXIT'
NAME_CODE = 'NAME'
CODE_LENGTH = 5

### Client object bitwise variable bit definitions
NEW_OUTPUT_MESSAGE_INDICATOR = 0b00000001
NEW_INPUT_MESSAGE_INDICATOR = 0b00000010

class Client:
    def __init__(self, client_handle, client_IP, client_ID, name='Anon'):

### Client object variables
        self.name = name
        self.IP = client_IP
        self.ID = client_ID
        self.client_handle = client_handle
        self.client_handle.setblocking(0)
### Client object message related variables
        self.in_message = ''
        self.out_message = ''
        self.in_message_status = False
        self.out_message_status = False
        self.empty_message = True
        self.count_message = 0
        self.receivers_list = []


    def GetIP(self):
        return self.IP

    def GetMessage(self):
        return self.in_message

    def GetName(self):
        return self.name

    def GetID(self):
        return self.ID

    def GetError(self):
        return self.client_handle.OSerror
#    return self.client_handle.error

    def GetIfEmptyMessage(self):
        return self.empty_message

# proctiaj da li postoji nova poruka za poslati
    def GetOutMsgStatus(self):
        return self.out_message_status

# procitaj da li postoji nova dolazna poruka
    def GetInMsgStatus(self):
        return self.in_message_status

# procitaj listu primatelja poruke
    def GetReceiversList(self):
        return self.receivers_list

# postavi da postoji nova poruka za poslati
    def SetOutMsgStatus(self, status=True):
        self.out_message_status = status

# postavi da postoji nova dolazna poruka
    def SetInMsgStatus (self, status=True):
        self.in_message_status = status

# postavi novo ime na kanalu
    def SetName(self, name_str):
        logging.debug('Name I '+name_str)
        self.ChannelMessage(CHANNEL_CODE+self.name+' changed into '+name_str+'\r\n')
        self.name = name_str

# dodaj novi niz karaktera u buffer za odlaznu poruku
    def OutputQueueMessage(self, msg_str):
        self.out_message += msg_str
        self.out_message_length = len(self.out_message)
        return (len(self.out_message) <= BUFF_SIZE)

# procitaj buffer za dolaynu poruku
    def InputQueueMessage(self):
        return self.in_message

    def ChannelMessage(self, channel_str):
        self.in_message += channel_str
        self.empty_message = False
        logging.debug('Ch_msg I '+self.in_message)

    def AddMessage(self, msg_str):
        logging.debug('Add I '+msg_str)
        if msg_str[:2] != '\r\n':
            logging.debug('Add II ')
            self.in_message += self.name+': '+msg_str
            self.empty_message = False
        return len(self.in_message)

    def RemoveMessage(self, client_list):
        logging.debug('Remove I '+str(self.count_message)+' '+str(len(client_list)))
        if self.count_message == (len(client_list)-1):
            logging.debug('Remove II ')
            self.in_message = ''
            self.count_message = 0
            self.empty_message = True
        return self.count_message

# posalji poruku na klijenta
    def SendMessage(self, msg_str):
        self.client_handle.send(bytes(msg_str, 'utf-8'))
        logging.debug('send msg'+str(self.ID))

# procitaj poruku od klijenta
    def RecvMessage(self):
        logging.debug('recv msg'+str(self.ID))
        return str(self.client_handle.recv(BUFF_SIZE), 'utf-8')

    def CountMessage(self):
        self.count_message += 1

# postavi socket u blocking ili non-blocking stanje
    def SetBlocking(self, state):
        self.client_handle.setblocking(state)

# neagresivno iskljuci socket = kraj rada
    def Shutdown(self):
        self.client_handle.shutdown()

# agresivno iskljuci socket
    def Close(self):
        self.client_handle.close()

# glavni klijentski thread koji kontinuirana cita dolazne poruke i salje odlazne poruke
    def ClientCoreLoop(self):
        logging.info('Joined the channel')
        exit_value = False
# receving client message
        while not exit_value:
            client_msg = ''
            try:
                client_msg = self.RecvMessage()
                logging.debug('try '+str(self.GetID())+client_msg)
            #except channel_client.GetError():
            except OSError:
                logging.debug('except '+str(self.GetID())+client_msg)
                self.RemoveMessage(client_list)
                sleep(1)
            else:
                logging.debug('else '+str(self.GetID())+client_msg)
                if len(client_msg) >= CODE_LENGTH:
                    if client_msg[:len(EXIT_CODE)] == EXIT_CODE:
                        exit_value = True
                        self.ChannelMessage(CHANNEL_CODE+self.GetName()+' leaves the channel\r\n')
                    elif client_msg[:len(NAME_CODE)] == NAME_CODE:
                        self.SetName(client_msg[(len(NAME_CODE)+1):(len(client_msg)-2)])
                    else:
                        logging.debug('Adding: '+client_msg)
                        self.AddMessage(client_msg)
                else:
                    logging.debug('Adding: '+client_msg)
                    self.AddMessage(client_msg)
# sending other clients messages
            for peers in client_list:
                if peers.GetID() != self.GetID() and not peers.GetIfEmptyMessage():
#        channel_client.SendMessage(peers.GetName()+': '+peers.GetMessage())
                    self.SendMessage(peers.GetMessage())
                    peers.CountMessage()
                    client_list.remove(self)
                    self.SendMessage(FAREWELL+self.GetName()+'\r\nHope to see you soon\r\n')
                    self.Close()
        return True


class Channel:
    """Class that defines behaviour of the communication channel"""
    def __init__(self):
        """Constructor of the Channel class object

        Consists of:
        - list of threads
        - communication socket
        """

# initialize chat-server
        self.channel_threads = []
        self.channel_sck = socket.socket()
        self.client_list = {}        
        try:
            SERVER = (socket.gethostbyname(HOST), PORT)
        except OSError:
            SERVER = (LOCALHOST, PORT)
        print(SERVER)
        self.channel_sck.bind(SERVER)
        self.channel_sck.listen(5)

    def EndOfWork(self):
        """Function that clears the Channel class object

        Consists of:
        - logging removal
        - socket deletion and closure

        Returns:
        - always True
        """
        for channel in self.client_list.values():
            channel.join(1)
            logging.shutdown()
            self.channel_sck.shutdown()
            self.channel_sck.close()
        return True

    def NewClientAccept(self):
        global client_ID
        peers_message = ''
        (client_handle, client_IP) = self.channel_sck.accept()
        client_ID = client_ID+1
        new_client = Client(client_handle, client_IP, client_ID, "User#"+str(client_ID))
        #client_list.append(cl)
# pokretanje novog threada
        channel = threading.Thread(name='User#'+str(client_ID), target=new_client.ClientCoreLoop, args=())
        #self.channel_threads.append(channel)
        channel.start()
        self.client_list[new_client] = channel
# welcoming notes
        new_client.OutputQueueMessage(WELCOME+'User#'+str(client_ID)+'\r\nType '+EXIT_CODE+' to end\r\nType '+NAME_CODE+' <chosen name> to identify yourself\r\n')
        #client_handle.send(bytes(WELCOME+'User#'+str(client_ID)+'\r\nType '+EXIT_CODE+' to end\r\nType '+NAME_CODE+' <chosen name> to identify yourself\r\n', 'utf-8'))
        clients_message = ''
        for client in self.client_list:
            clients_message += str(client.GetName())+' '
        new_client.OutputQueueMessage('Currently on channel: '+clients_message+'\r\n')
        new_client.out_message_status == True
        #client_handle.send(bytes('Currently on channel: '+peers_message+'\r\n', 'utf-8'))

    def DispatchChannelMessages(self):
        for client in self.client_list:
            if client.GetInMsgStatus():
                for client_peer in client.GetReceiversList():
                    client_peer.SetOutputQueueMessage(client.GetInputQueueMessage())
                    client_peer.SetOutMsgStatus(True)
                client.SetInMsgStatus(False)

    def CoreLoop(self):
        """Function that represents engine of the channel.
        Responsible for accepting new clients and maintaining the list of successfully joined clients.
        """
# petlja za cekanje i aktiviranje klijenata i distribuciju poruka
        while True:
            self.NewClientAccept()
### message dispatcher between clients
            self.DispatchChannelMessages()
        return True

def main():
    """Main function of the messaging program.
    Initializes a Channel class object, runs the engine of the channel and finally closes the channel.
    """
    comm_channel = Channel()
    comm_channel.CoreLoop()
    comm_channel.EndOfWork()

if __name__ == '__main__':
    main()
