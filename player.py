import os
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
import tensorflow as tf
import h5py

from keras.models import Sequential
from keras.layers import Dense, Activation
from keras.optimizers import SGD
import numpy as np
import json

# input nodes: 
# 	- distance of bird from closest vertical pipe
# 	- height of the bird from the vertical level of the closest pipe

class Player():
	def __init__(self):
		self.id = 0
		self.model = self.initModel()
		self.fitness = -1000
		self.score = 0
		self.dist = 0
		self.active = True

		self.playerIndex = 0
		self.playerx = 0
		self.playery = 0

		self.playerVelY    =  0   
		self.playerMaxVelY =  0   
		self.playerMinVelY =  0   
		self.playerAccY    =  0   
		self.playerFlapAcc =  0   
		self.playerFlapped = False 
		self.playerShmVals = None
		self.playerIndexGen = None
		self.loopIter = 0

	def initModel(self):
		model = Sequential()
		model.add(Dense(output_dim=7, input_dim=2))
		model.add(Activation("sigmoid"))
		model.add(Dense(output_dim=1))
		model.add(Activation("sigmoid"))

		sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
		model.compile(loss="mse", optimizer=sgd, metrics=["accuracy"])
		return model

	def predict(self, dist1, dist2):
		neural_input = np.asarray([dist1, dist2])
		neural_input = np.atleast_2d(neural_input)
		pred = self.model.predict(neural_input)[0]
		if pred < 0.5:
			return 1
		return 0

	def setFitness(self):
		self.fitness = np.mean([self.score*100, self.dist])

	def saveModel(self, gen):
		path = "models/gen" + str(gen) 
		if not os.path.exists(path):
			os.makedirs(path)
		self.model.save_weights(path + '/' + str(self.id) + ".keras")

	def loadModel(self, gen, id_):
		self.id = id_
		path = "models/gen" + str(gen) 
		self.model.load_weights(path + '/' + str(id_) + ".keras")










