from PIL import Image
from scipy import optimize as ls
import numpy as np
from PythonLabVIEW import LabviewPasser as lv

p2m = 1.5866
wireRadius = 90/2/p2m
cropRadii = 1.5

def imageToArray(filename):
	im = Image.open(filename)
	(w, h) = im.size
	pixels = np.array(im)
	values = list(map(lambda x: (np.sum(pixels[x])/w), range(h)))
	mean = np.mean(values)
	return list(map(lambda x: (values[x]-mean)**2, range(0, len(values))))

def model(x, params):
	A, m, c = params
	cos2 = ((x - m)/wireRadius)**2
	if cos2 < 1:
		sin2 = 1-cos2
		return A*np.exp(-c*cos2/sin2)*sin2
	return 0

def initialGuesser(dataY, c, r):
	if int(c-0.5) == -1:
		c, r = np.argmax(dataY), 30
	return [dataY[int(c+0.5)], c, r]

[imageFilePath, [guessC, guessR]] = lv.getFromLabview()
dataY = imageToArray(imageFilePath)
B0 = initialGuesser(dataY, guessC, guessR)
xMin, xMax = int(B0[1] - cropRadii*wireRadius), int(B0[1] + cropRadii*wireRadius) + 1
def residuals(params):
	return list(map(lambda x: dataY[x]-model(x, params), range(xMin, xMax)))
fit = ls.least_squares(residuals, B0, method = "trf", xtol = 0.000001, diff_step = [0.0001, 0.00002, 0.01], max_nfev = 25)
if not fit.success or fit.x[2] < 0:
	lv.sendToLabview([fit.x, np.empty(3), fit.nfev, [np.array(range(xMin, xMax)), np.array(dataY[xMin: xMax]), np.array(list(map(lambda x: model(x, fit.x), range(xMin, xMax))))]])
	exit(3)
errors = np.sqrt(np.diagonal(np.linalg.inv(np.matmul(np.transpose(fit.jac), fit.jac))))
# lv.sendToLabview([fit.x, errors, fit.nfev, [np.empty((0,), dtype=np.float64), np.empty((0,), dtype=np.float64), np.empty((0,), dtype=np.float64)]])
lv.sendToLabview([fit.x, errors, fit.nfev, [np.array(range(xMin, xMax)), np.array(dataY[xMin: xMax]), np.array(list(map(lambda x: model(x, fit.x), range(xMin, xMax))))]])
