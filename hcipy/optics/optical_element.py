class OpticalElement(object):
	def __call__(self, wavefront):
		raise self.forward(wavefront)
	
	def forward(self, wavefront):
		raise NotImplementedError()
	
	def backward(self, wavefront):
		raise NotImplementedError()
	
	def get_transformation_matrix(self, wavelength=1):
		raise NotImplementedError()

class Detector(object):
	def integrate(self, wavefront, dt, weight=1):
		raise NotImplementedError()
	
	def read_out(self):
		raise NotImplementedError()