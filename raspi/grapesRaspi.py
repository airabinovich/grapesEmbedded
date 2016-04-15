#!/usr/bin/python

import MySQLdb as MySQL
import smbus
import time
import sys
import requests

import pdb


MOCKED_VALUES = [1,2,3,4,5,6]

class DataManager(object):

	def __init__(self, user, password, id_field, server_address, devices):
		assert isinstance(devices, list)
		self.password = password
		self.user = user
		self.id_field = id_field
		self.devices = devices
		self.server_address = server_address

	def SendMessageToDB(self, sql_query):
		pdb.set_trace()
		db = MySQL.connect(host="localhost", user=self.user, passwd=self.password, db="grapesEmbedded")
		db_cursor = db.cursor()
		try:
			db_cursor.execute(sql_query)
			db.commit()
		except:
			db.rollback()
		db.close()

	def SaveToLocalDB(self, mediciones):
		for medicion in mediciones:
			sql_query = "insert into mediciones(valor, idsensor, fecha, idmagnitud) select {value}, sensores.idsensor, now(), sensores.idmagnitud from sensores where sensores.address = {address}".format(value=medicion['value'], address=medicion['address'])
			self.SendMessageToDB(sql_query)
			
	def SaveToRemoteDB(self, is_https=False):		
		# Delete data from DB
		db = MySQL.connect(host="localhost", user=self.user, passwd=self.password, db="grapesEmbedded")
		db_cursor = db.cursor()		
		data = ''
		try:
			sql_query = "select campos.idcampo, mediciones.fecha, mediciones.valor, magnitudes.unidad, magnitudes.nombre from mediciones join sensores on mediciones.idsensor=sensores.idsensor join campos on sensores.idcampo=campos.idcampo join magnitudes on mediciones.idmagnitud=magnitudes.idmagnitud"
			db_cursor.execute(sql_query)
			data = db_cursor.fetchall()
		except:
			data = "Error reading data from local data base"
		db.close()
		
		protocol = 'https' if is_https else 'http'
		req = requests.post("{proto}://{address}/api/topSecret".format(proto=protocol, address=self.server_address), data=data)

		if req.status_code != 200:
			raise Exception('Fail to send data to remote DB')

		sql_query = "delete from mediciones"
		self.SendMessageToDB(sql_query)		
		
	def SendData(self, mediciones):
		self.SaveToLocalDB(mediciones)
		self.SaveToRemoteDB()

	def SetupDB(self):
		sql_query = "insert into campos (descripcion) select * from (select {id_field}) where not exists (select * from campos) limit 1;".format(id_field=self.id_field)
		self.SendMessageToDB(sql_query)
		for device in self.devices:
			sql_query = "insert into sensores (idCampo,address,gpLat,gpsLong) select {id_field}, {address}, null, null".format(id_field=self.id_field, address=device)
			self.SendMessageToDB(sql_query)
		

def main(argv):
	print "I need: "
	print "		   -The id of the field"
	print "		   -The server IP address"
	print "		   -The number of devices"
	print "		   -The i2c_address of the device"
	
	if len(argv) < 4:
		sys.exit()
	# Extra Data
	devices = []
	id_field = argv[0]
	server_address = argv[1]
	number_of_devices = int(argv[2])
	devices = [ int(argv[i + 3]) for i in range(number_of_devices)]

	# I2C bus
	bus = smbus.SMBus(1)

	# Autentication local and remote DB
	user = "root"
	password = "grapes123"

	data_manager = DataManager(user, password, id_field, server_address, devices)

	data_manager.SetupDB()

	while True:
		data = []
		for device in devices:	
			sub_data = {}
			i = 0
			# Read values from device
			#sub_data["value"] = bus.read_byte(device)
			sub_data["value"] = MOCKED_VALUES[i]
			i += 1
			sub_data["address"] = device
			data += [sub_data]
		
		pdb.set_trace()
		data_manager.SendData(data)
		time.sleep(2)

if __name__ == "__main__":
   main(sys.argv[1:])
