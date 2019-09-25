import numpy as np 
from hcipy import *

def test_statistics_noisy_detector():
	N = 256
	grid = make_pupil_grid(N)

	field = Field(np.ones(N**2), grid)
	
	#First we test photon noise, dark current noise and read noise.
	flat_field = 0
	dark_currents = np.logspace(1, 6, 6)
	read_noises = np.logspace(1, 6, 6)
	photon_noise = True

	for dc in dark_currents:
		for rn in read_noises: 
			#The test detector.
			detector = NoisyDetector(input_grid=grid, include_photon_noise=photon_noise, flat_field=flat_field, dark_current_rate=dc, read_noise=rn)

			#The integration times we will test.
			integration_time = np.logspace(1,6,6)

			for t in integration_time:
				# integration
				detector.integrate(field, t)

				# read out
				measurement = detector.read_out()

				# The std of the data by the detector.
				std_measurement = np.std(measurement)

				# The std that we expect given the input.
				expected_std = np.sqrt(field[0] * t + rn**2 + dc * t)

				assert np.isclose(expected_std, std_measurement, rtol=2e-02, atol=1e-05)

	#Now we test the flat field separately.
	flat_fields = np.linspace(0, 1, 100)
	dark_current = 0
	read_noise = 0
	photon_noise = False

	for ff in flat_fields:
		#The test detector.
		detector = NoisyDetector(input_grid=grid, include_photon_noise=photon_noise, flat_field=ff, dark_current_rate=dark_current, read_noise=read_noise)

		#The integration times we will test.
		integration_time = np.logspace(1, 6, 6)

		for t in integration_time:
			# integration
			detector.integrate(field, t)

			# read out 
			measurement = detector.read_out()

			# The std of the data by the detector.
			std_measurement = np.std(measurement)

			# The std that we expect given the input.
			expected_std = ff * field[0] * t 

			assert np.isclose(expected_std, std_measurement, rtol=2e-02, atol=1e-05)

def test_segmented_deformable_mirror():
	num_pix = 256
	grid = make_pupil_grid(num_pix)

	for num_rings in [2, 4, 5]:
		num_segments_expected = 3 * (num_rings + 1) * num_rings + 1

		segment_positions = make_hexagonal_grid(0.5 / num_rings * np.sqrt(3) / 2, num_rings)
		aperture, segments = make_segmented_aperture(hexagonal_aperture(0.5 / num_rings - 0.003, np.pi / 2), segment_positions, return_segments=True)

		aperture = evaluate_supersampled(aperture, grid, 2)
		segments = evaluate_supersampled(segments, grid, 2)

		# Check number of generated segments
		assert len(segments) == num_segments_expected

		segmented_mirror = SegmentedDeformableMirror(segments)

		# Mirror should start out flattened.
		assert np.std(segmented_mirror.surface) < 1e-12

		for i in np.random.randint(0, num_segments_expected, size=10):
			piston = np.random.randn(1)

			while np.abs(piston) < 1e-5:
				piston = np.random.randn(1)

			segmented_mirror.set_segment_actuators(i, piston, 0, 0)

			# Mirror should have the correct piston
			assert np.abs(segmented_mirror.get_segment_actuators(i)[0] - piston) / piston < 1e-5
			assert np.abs(np.ptp(segmented_mirror.surface) - piston) / piston < 1e-5

			tip, tilt = np.random.randn(2)

			while np.abs(tip) < 1e-5:
				tip = np.random.randn(1)

			while np.abs(tilt) < 1e-5:
				tilt = np.random.randn(1)

			segmented_mirror.set_segment_actuators(i, 0, tip, tilt)

			# Mirror should be distorted with tip and tilt on a segment
			assert np.std(segmented_mirror.surface > 1e-12)

			# Return segment to zero position
			segmented_mirror.set_segment_actuators(i, 0, 0, 0)

def test_wavefront_stokes():
	N = 4
	grid = make_pupil_grid(N)

	stokes = np.random.uniform(-1,1,4)
	stokes[0] = np.abs(stokes[0])+np.linalg.norm(stokes[1:])

	amplitude = np.random.uniform(0, 1, (2,2,N**2))
	phase = np.random.uniform(0, 2 * np.pi, (2,2,N**2))

	jones_field = Field(amplitude * np.exp(1j * phase), grid)

	determinants = field_determinant(jones_field)
	jones_field[:, :, determinants > 1] *= np.random.uniform(0, 1, np.sum(determinants > 1)) / determinants[determinants > 1]

	jones_element = JonesMatrixOpticalElement(jones_field)

	mueller_field = jones_to_mueller(jones_field)

	field = Field(np.ones(N**2), grid)
	stokes_wavefront = Wavefront(field, stokes_vector=stokes)

	jones_element_forward = jones_element.forward(stokes_wavefront)
	mueller_forward = field_dot(mueller_field, stokes)

	assert np.allclose(jones_element_forward.I, mueller_forward[0])
	assert np.allclose(jones_element_forward.Q, mueller_forward[1])
	assert np.allclose(jones_element_forward.U, mueller_forward[2])
	assert np.allclose(jones_element_forward.V, mueller_forward[3])

def test_degree_and_angle_of_polarization():
	grid = make_pupil_grid(16)

	wf = Wavefront(grid.ones(), stokes_vector=[1, 0, 0, 0])
	assert np.allclose(wf.degree_of_polarization, 0)
	assert np.allclose(wf.degree_of_linear_polarization, 0)
	assert np.allclose(wf.degree_of_circular_polarization, 0)

	wf = Wavefront(grid.ones(), stokes_vector=[1, 1, 0, 0])
	assert np.allclose(wf.degree_of_polarization, 1)
	assert np.allclose(wf.degree_of_linear_polarization, 1)
	assert np.allclose(wf.angle_of_linear_polarization, 0)
	assert np.allclose(wf.degree_of_circular_polarization, 0)

	wf = Wavefront(grid.ones(), stokes_vector=[1, 0.5, 0, 0])
	assert np.allclose(wf.degree_of_polarization, 0.5)
	assert np.allclose(wf.degree_of_linear_polarization, 0.5)
	assert np.allclose(wf.angle_of_linear_polarization, 0)
	assert np.allclose(wf.degree_of_circular_polarization, 0)

	wf = Wavefront(grid.ones(), stokes_vector=[1, -1, 0, 0])
	assert np.allclose(wf.degree_of_polarization, 1)
	assert np.allclose(wf.degree_of_linear_polarization, 1)
	assert np.allclose(wf.angle_of_linear_polarization, np.pi / 2)
	assert np.allclose(wf.degree_of_circular_polarization, 0)

	wf = Wavefront(grid.ones(), stokes_vector=[1, 0, 1, 0])
	assert np.allclose(wf.degree_of_polarization, 1)
	assert np.allclose(wf.degree_of_linear_polarization, 1)
	assert np.allclose(wf.angle_of_linear_polarization, np.pi / 4)
	assert np.allclose(wf.degree_of_circular_polarization, 0)

	wf = Wavefront(grid.ones(), stokes_vector=[1, 0, 0, 1])
	assert np.allclose(wf.degree_of_polarization, 1)
	assert np.allclose(wf.degree_of_linear_polarization, 0)
	assert np.allclose(wf.degree_of_circular_polarization, 1)

	wf = Wavefront(grid.ones(), stokes_vector=[1, 0, 0, 0.5])
	assert np.allclose(wf.degree_of_polarization, 0.5)
	assert np.allclose(wf.degree_of_linear_polarization, 0)
	assert np.allclose(wf.degree_of_circular_polarization, 0.5)

	wf = Wavefront(grid.ones(), stokes_vector=[1, 0, 0, -1])
	assert np.allclose(wf.degree_of_polarization, 1)
	assert np.allclose(wf.degree_of_linear_polarization, 0)
	assert np.allclose(wf.degree_of_circular_polarization, -1)

	wf = Wavefront(grid.ones(), stokes_vector=[2, np.sqrt(2), 0, np.sqrt(2)])
	assert np.allclose(wf.degree_of_polarization, 1)
	assert np.allclose(wf.degree_of_linear_polarization, 1 / np.sqrt(2))
	assert np.allclose(wf.degree_of_circular_polarization, 1 / np.sqrt(2))

def test_polarization_elements():
	'''Tests to check if polarization elements have correct behaviour. 

	Using analytical Mueller matrices and set input Stokes vectors we check if 
	the polarization elements generate the expected output Stokes vectors.

	'''

	def general_linear_retarder(theta, delta):
		''' Analytic expression Mueller matrix linear retarder. 

		Parameters
		----------
		theta : scaler
		    rotation angle optic in radians 
		delta : scalar 
		    retardance optic in radians 
		'''

		retarder = np.zeros((4,4))

		retarder[0,0] = 1

		retarder[1,1] = np.cos(2*theta)**2 + np.sin(2*theta)**2 * np.cos(delta)
		retarder[1,2] = np.cos(2*theta) * np.sin(2*theta) * (1 - np.cos(delta))
		retarder[1,3] = np.sin(2*theta) * np.sin(delta)

		retarder[2,1] = np.cos(2*theta) * np.sin(2*theta) * (1 - np.cos(delta))
		retarder[2,2] = np.cos(2*theta)**2 * np.cos(delta) + np.sin(2*theta)**2
		retarder[2,3] = -np.cos(2*theta) * np.sin(delta)

		retarder[3,1] = -np.sin(2*theta) * np.sin(delta)
		retarder[3,2] = np.cos(2*theta) * np.sin(delta)
		retarder[3,3] = np.cos(delta)

		return retarder

	def general_linear_polarizer(theta):
		''' Analytic expression Mueller matrix linear polarizer. 

		Parameters
		----------
		theta : scaler
		    rotation angle optic in radians 
		'''
		polarizer = np.zeros((4,4))

		polarizer[0,0] = 1
		polarizer[0,1] = np.cos(2*theta)
		polarizer[0,2] = np.sin(2*theta)

		polarizer[1,0] = np.cos(2*theta)
		polarizer[1,1] = np.cos(2*theta) ** 2
		polarizer[1,2] = 0.5 * np.sin(4*theta)

		polarizer[2,0] = np.sin(2*theta)
		polarizer[2,1] = 0.5 * np.sin(4*theta)
		polarizer[2,2] = np.sin(2*theta) ** 2

		polarizer *= 0.5

		return polarizer

	N = 1
	grid = make_pupil_grid(N)

	test_field = grid.ones()

	# Stokes vectors used for testing. 
	stokes_vectors = [None,
					np.array([1,0,0,0]), #unpolarized 
					np.array([1,1,0,0]), # +Q polarized  
					np.array([1,-1,0,0]), # -Q polarized  
					np.array([1,0,1,0]), # +U polarized  
					np.array([1,0,-1,0]), # -U polarized  
					np.array([1,0,0,1]), # +V polarized  
					np.array([1,0,0,-1])] # -V polarized  

	# angles of the optics that will be tested
	angles = [-45, -22.5, 0, 22.5, 45, 90] # degrees

	# testing QWPs, HWPS and polarizers
	for stokes_vector in stokes_vectors:

		# generating the test wavefront
		test_wf = Wavefront(test_field, stokes_vector=stokes_vector)

		# set the stokes vector to unpolarized such that it can be used for tests
		if stokes_vector is None:
			stokes_vector = np.array([1,0,0,0]) # unpolarized

		# testing the different optic angles  
		for angle in angles:
			#--------------------------------------------
			# testing QWP

			# QWP by hcipy 
			QWP_hcipy = QuarterWavePlate(np.radians(angle))

			# reference QWP
			QWP_ref = general_linear_retarder(np.radians(angle), -np.pi/2)

			# testing if the Mueller matrices are the same 
			assert np.allclose(QWP_hcipy.get_instance(grid,None,1).get_instance(grid,None,1).mueller_matrix, QWP_ref)

			# propagating the test stokes vector through the hcipy and reference optics 
			wf_forward_QWP = QWP_hcipy.forward(test_wf)
			reference_stokes_post_QWP = field_dot(QWP_ref, stokes_vector)

			# testing if the results are the same
			assert np.allclose(wf_forward_QWP.stokes_vector[:,0], reference_stokes_post_QWP)

			# testing if forward and backward propagation results in the initial state. 
			wf_forward_backward_QWP = QWP_hcipy.backward(wf_forward_QWP)

			# testing if the results are the same
			assert np.allclose(wf_forward_backward_QWP.stokes_vector[:,0], stokes_vector)

			#--------------------------------------------
			# testing HWP

			# HWP by hcipy 
			HWP_hcipy = HalfWavePlate(np.radians(angle))

			# reference QWP
			HWP_ref = general_linear_retarder(np.radians(angle), -np.pi)

			# testing if the Mueller matrices are the same 
			assert np.allclose(HWP_hcipy.get_instance(grid,None,1).get_instance(grid,None,1).mueller_matrix, HWP_ref)

			# propagating the test stokes vector through the hcipy and reference optics 
			wf_forward_HWP = HWP_hcipy.forward(test_wf)
			reference_stokes_post_HWP = field_dot(HWP_ref, stokes_vector)

			# testing if the results are the same
			assert np.allclose(wf_forward_HWP.stokes_vector[:,0], reference_stokes_post_HWP)

			# testing if forward and backward propagation results in the initial state. 
			wf_forward_backward_HWP = HWP_hcipy.backward(wf_forward_HWP)

			# testing if the results are the same
			assert np.allclose(wf_forward_backward_HWP.stokes_vector[:,0], stokes_vector)

			#--------------------------------------------
			# testing polarizer 

			# Linear polarizer by hcipy 
			polarizer_hcipy = LinearPolarizer(np.radians(angle))

			# reference polarizer
			polarizer_ref = general_linear_polarizer(np.radians(angle))

			# testing if the Mueller matrices are the same 
			assert np.allclose(polarizer_hcipy.get_instance(grid,None,1).get_instance(grid,None,1).mueller_matrix, polarizer_ref)     

			# propagating the test stokes vector through the hcipy and reference optics 
			wf_forward_polarizer = polarizer_hcipy.forward(test_wf)
			reference_stokes_post_polarizer = field_dot(polarizer_ref, stokes_vector)

			# testing if the results are the same
			assert np.allclose(wf_forward_polarizer.stokes_vector[:,0], reference_stokes_post_polarizer)

			# propagating the wavefront backward through the polarizer
			wf_backward_polarizer = polarizer_hcipy.backward(test_wf)

			# testing if the results are the same
			assert np.allclose(wf_backward_polarizer.stokes_vector[:,0], reference_stokes_post_polarizer)

			#--------------------------------------------
			# testing polarizing beamsplitter 

			# HWP by hcipy 
			PBS_hcipy = PolarizingBeamSplitter(np.radians(angle)) 

			# reference Polarizers 
			polarizer_1_ref = general_linear_polarizer(np.radians(angle))
			polarizer_2_ref = general_linear_polarizer(np.radians(angle + 90))

			# testing if the Mueller matrices are the same 
			assert np.allclose(PBS_hcipy.mueller_matrix[0], polarizer_1_ref)     
			assert np.allclose(PBS_hcipy.mueller_matrix[1], polarizer_2_ref)

			# propagating the test stokes vector through the hcipy and reference optics 
			wf_forward_polarizer_1, wf_forward_polarizer_2 = PBS_hcipy.forward(test_wf)
			reference_stokes_post_polarizer_1 = field_dot(polarizer_1_ref, stokes_vector)
			reference_stokes_post_polarizer_2 = field_dot(polarizer_2_ref, stokes_vector)

			# testing if the results are the same
			assert np.allclose(wf_forward_polarizer_1.stokes_vector[:,0], reference_stokes_post_polarizer_1)
			assert np.allclose(wf_forward_polarizer_2.stokes_vector[:,0], reference_stokes_post_polarizer_2)

			# testing if power is conserved
			assert np.allclose(test_wf.stokes_vector[0], wf_forward_polarizer_1.stokes_vector[0] + wf_forward_polarizer_2.stokes_vector[0])

	# testing rotated Jones matrix function 

	# HWP by hcipy 
	HWP_hcipy = HalfWavePlate(0)

	for angle in angles:

		# rotating the HWP 
		rotated_HWP_hcipy = RotatedJonesMatrixOpticalElement(HWP_hcipy.get_instance(grid,None,1).get_instance(grid,None,1).jones_matrix, np.radians(angle))

		# calculating a reference HWP at the same angle
		HWP_ref = general_linear_retarder(np.radians(angle), -np.pi)

		# testing if the Mueller matrices are the same 
		assert np.allclose(rotated_HWP_hcipy.get_instance(grid,None,1).get_instance(grid,None,1).get_instance(grid,None,1).mueller_matrix, HWP_ref)
