#!/usr/bin/python

import MySQLdb as MySQL
import smbus
import time
import sys
import requests

import pdb


LOCALHOST = "localhost"
ID_TEMP = 0
ID_HUM = 1
MAGNITUDES = {
			ID_TEMP : "Temperatura",
			ID_HUM : "Humedad"
}
MOCKED_VALUES = [(ID_TEMP,1),(ID_TEMP,2),(ID_HUM,3),(ID_TEMP,4),(ID_HUM,5),(ID_HUM,6)]

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
 select {value},(select sensores.idsensor from sensores where sensores.address = {address}),\
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
			sql_query = "select campos.uuid, mediciones.fecha, mediciones.valor, magnitudes.nombre, magnitudes.unidad\
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
			measurement["id_campo"] = medicion[0]
			measurement["fecha_hora"] = str(medicion[1])
			measurement["valor"] = medicion[2]
			measurement["magnitud"] = medicion[3]
			measurement["unidad"] = str(medicion[4])
			measurementsToSend.append(measurement)
		
		protocol = 'https' if is_https else 'http'
		req = requests.post("{proto}://{address}/api/topSecret".format(proto=protocol, address=self.server_address), json=measurementsToSend)

		if req.status_code != 200:
			raise Exception('Fail to send data to remote DB')

		sql_query = "delete from mediciones"
		self.SendMessageToDB(sql_query=sql_query)		
		
	def SendData(self, data):
		self.SaveToLocalDB(mediciones=data)
		self.SaveToRemoteDB()

	def SetupDB(self):
		sql_query = "insert into campos (uuid) select * from (select {id_field}) as IDs where not exists (select * from campos) limit 1;".format(id_field=self.id_field)
		self.SendMessageToDB(sql_query=sql_query)
		for device in self.devices:
			sql_query = "insert into sensores (idCampo,address,gpsLat,gpsLong)\
 select * from (select idCampo, {address} as address, null as gpsLat, null as gpsLong from campos where campos.uuid = {id_field}) as dataToAdd\
 where not exists (select * from sensores where address = {address});".format(id_field=self.id_field, address=device)
 			self.SendMessageToDB(sql_query=sql_query)
		

def main(argv):
	print "I need: "
	print "		   -The id of the field"
	print "		   -The server IP address"
	print "		   -The number of devices"
	print "		   -MOCKED_VALUES 1 or REAL_VALUES 0"
	print "		   -The i2c_address of the device"
	
	if len(argv) < 5:
		print "Not enough parameters"
		sys.exit()
	# Extra Data
	dev_i2c_address = []
	id_field = argv[0]
	server_address = argv[1]
	number_of_devices = int(argv[2])
	mock_or_real = int(argv[3])
	dev_i2c_address = [ int(argv[i + 4]) for i in range(number_of_devices)]

	# I2C bus
	bus = smbus.SMBus(1)

	# Autentication local and remote DB
	user = "root"
	password = "grapes123"

	data_manager = DataManager(user=user, password=password, id_field=id_field, server_address=server_address, devices=dev_i2c_address)
	data_manager.SetupDB()

	pdb.set_trace()
	
	while True:
		data = []
		i = 0
		for device in dev_i2c_address:	
			sub_data = {}
			if mock_or_real == 1:
				# Read mock values
				sub_data["magnitude"] = MAGNITUDES[MOCKED_VALUES[i][0]]
				sub_data["value"] = MOCKED_VALUES[i][1]
				i += 1
			else:
				# Read values from device
				sub_data["magnitude"] = MAGNITUDES[bus.read_byte(device)]
				sub_data["value"] = bus.read_byte(device)
			
			sub_data["address"] = device
			# Append device
			data += [sub_data]

		data_manager.SendData(data=data)
		time.sleep(2)

if __name__ == "__main__":
   main(sys.argv[1:])
