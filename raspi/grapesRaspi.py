#!/usr/bin/python

import MySQLdb as MySQL
import smbus
import time
import sys
import requests
import serial
import json 

import pdb


LOCALHOST = "localhost"

MAGNITUDE_CODE = {
	"TEMP": 1,
	"HUM": 2
}

ID_TEMP = 0
ID_HUM = 1
MOCKED_VALUES = [(ID_TEMP,1),(ID_TEMP,2),(ID_HUM,3),(ID_TEMP,4),(ID_HUM,5),(ID_HUM,6)]

class InvalidConfigException(Exception):
	'''raised when config data is invalid '''

	def __init__(self, message):
		self.message = message

	def __str__(self):
		return repr(self.message)

class ErrorRecievingData(Exception):
	'''raised when it can't recieve data '''

	def __init__(self, message):
		self.message = message

	def __str__(self):
		return repr(self.message)

class DataManager(object):

	def __init__(self, user, password, id_field, server_address, devices):
		assert isinstance(devices, list)
		self.password = password
		self.user = user
		self.id_field = id_field
		self.devices = devices
		self.server_address = server_address
		self.localhost = LOCALHOST

	def SendMessageToDB(self, sql_query):
		db = MySQL.connect(host=self.localhost, user=self.user, passwd=self.password, db="grapesEmbedded")
		db_cursor = db.cursor()
		try:
			db_cursor.execute(sql_query)
			db.commit()
		except:
			db.rollback()
		db.close()

	def SaveToLocalDB(self, mediciones):
		for medicion in mediciones:
			sql_query = "insert into mediciones(valor, idsensor, fecha, idmagnitud)\
 select {value},(select sensores.idsensor from sensores where sensores.address like '{address}'),\
 now(), (select magnitudes.IdMagnitud from magnitudes where magnitudes.nombre like '{magnitude}');".format(value=medicion['value'],
																									 address=medicion['address'],
																									 magnitude=medicion["magnitude"])
			self.SendMessageToDB(sql_query=sql_query)
			
	def SaveToRemoteDB(self, is_https=False):		
		# Fetch all measurements stored in local database
		db = MySQL.connect(host=self.localhost, user=self.user, passwd=self.password, db="grapesEmbedded")
		db_cursor = db.cursor()		
		data = ''
		try:
			sql_query = "select campos.uuid, sensores.address, mediciones.fecha, mediciones.valor, magnitudes.nombre\
 from mediciones\
 join sensores on mediciones.idsensor=sensores.idsensor\
 join campos on sensores.idcampo=campos.idcampo\
 join magnitudes on mediciones.idmagnitud=magnitudes.idmagnitud;"
			db_cursor.execute(sql_query)
			data = db_cursor.fetchall()
		except:
			data = "Error reading data from local data base"
		db.close()
		
		measurementsToSend = list()
		for medicion in data:
			measurement = dict()
			measurement["uuid_campo"] = medicion[0]
			measurement["sensor_address"] = str(medicion[1])
			measurement["fecha_hora"] = str(medicion[2])
			measurement["valor"] = medicion[3]
			measurement["magnitud"] = MAGNITUDE_CODE[medicion[4]]
			measurementsToSend.append(measurement)
		
		protocol = 'https' if is_https else 'http'
		
		try:
			req = requests.post("{proto}://{address}/api/topSecret".format(proto=protocol, address=self.server_address), json=measurementsToSend)
		except:
			print "Conection refused"

		if req.status_code != 200:
			raise Exception('Fail to send data to remote DB')

		sql_query = "delete from mediciones"
		self.SendMessageToDB(sql_query=sql_query)		
		
	def SendData(self, data):
		self.SaveToLocalDB(mediciones=data)
		self.SaveToRemoteDB()

	def SetupDB(self):
		sql_query = "insert into campos (uuid) select * from (select '{id_field}') as IDs where not exists (select * from campos) limit 1;".format(id_field=self.id_field)
		self.SendMessageToDB(sql_query=sql_query)
		for device in self.devices:
			sql_query = "insert into sensores (idCampo,address,gpsLat,gpsLong)\
 select * from (select idCampo, '{address}' as address, null as gpsLat, null as gpsLong from campos where campos.uuid = '{id_field}') as dataToAdd\
 where not exists (select * from sensores where address = '{address}');".format(id_field=self.id_field, address=device)
 			self.SendMessageToDB(sql_query=sql_query)

class CommunicationManager(object):

	def __init__(self, devices = ["/dev/ttyACM0"], protocol = "serial"):
		assert isinstance(devices, list)
		self.protocol = protocol
		self.devices = devices
		self.device_amount = len(devices)

	def Setup(self, *args, **kwargs):
		if self.protocol == "serial":
			self.serialPorts = [serial.Serial(
				port = self.devices[i],
				baudrate = kwargs["baudrate"] or 9600,
				parity = serial.PARITY_NONE,
				stopbits = serial.STOPBITS_ONE,
				bytesize = serial.EIGHTBITS,
				timeout = 1
			) for i in range(self.device_amount)]
		elif self.protocol == "i2c":
			self.bus = smbus.SMBus(1)
			self.devices_addr = self.devices
		else:
			raise InvalidConfigException("protocol {} not supported".format(self.protocol));
		
	def RecieveSerial(self, device):
		for serial in self.serialPorts:
			if serial.port == device:
				return serial.readline().strip('\r\n')
		raise ErrorRecievingData("cannot recieve data from serial port {}".format(device))
	
	def RecieveI2C(self, device):
		tries = 10
		while tries > 0:
			try:
				time.sleep(2)
				data = bus.read_byte(device)
			except IOError:
				tries -= 1
			else:
				return data
		raise ErrorRecievingData("cannot recieve data from i2c port {}".format(device))
	
	def Recieve(self, device):
		if self.protocol == "serial":
			return self.RecieveSerial(device)
		elif self.protocol == "i2c":
			return self.RecieveI2C(device)
		else:
			raise InvalidConfigException("bad protocol {}".format(self.protocol))
	
def main(argv):
	
	mock = False
	if len(argv) > 0:
		mock = True if argv[0] == "--mock" else False
	
	# Read config File
	with open("config.json") as config_file:
		config = json.load(config_file)

		id_field = config["field_uuid"]
		server_address = config["server"]
		protocol = config["protocol"]
		devices = config["devices"]

		# Autentication local and remote DB
		user = config["database"]["user"]
		password = config["database"]["password"]

	data_manager = DataManager(user=user, password=password, id_field=id_field, server_address=server_address, devices=devices)
	data_manager.SetupDB()

	comm_manager = CommunicationManager(devices = devices, protocol = protocol)
	comm_manager.Setup(baudrate = 9600)

	#pdb.set_trace()

	while True:
		data = []
		i = 0
		for device in devices:	
			sub_data = {}
			if mock:
				# Read mock values
				sub_data["magnitude"] = MOCKED_VALUES[i][0]
				sub_data["value"] = MOCKED_VALUES[i][1]
				data += [sub_data]
				i += 1
			else:
				# Read values from device
				try_again = True
				while(try_again):
					try:
						time.sleep(1)
						new_data_list = comm_manager.Recieve(device).split(",")
						for new_data in new_data_list:
							sub_data = dict()
							(magnitude, value) = new_data.split(":")
							sub_data["magnitude"] = magnitude
							sub_data["value"] = value
							sub_data["address"] = device
							# Append measurement
							data += [sub_data]
							try_again = False
					except:
						try_again = True

		data_manager.SendData(data=data)
		time.sleep(2)

if __name__ == "__main__":
   main(sys.argv[1:])
