from dirToNRRD import directory_processing
import logging
import SimpleITK as sitk

import radiomics
from radiomics import featureextractor

import csv


series_to_Test = "001/"



target_dir = "processed/"+ series_to_Test
imageName = target_dir+"image.nrrd"
maskName = target_dir+"seg_1.nrrd"
directory_processing("examples/"+series_to_Test, target_dir)


logger = radiomics.logger
logger.setLevel(logging.INFO)

handler = logging.FileHandler(filename='testLog.txt', mode='w')
formatter = logging.Formatter("%(levelname)s:%(name)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

settings = {}
settings['binWidth'] = 25
settings['resampledPixelSpacing'] = None
settings['interpolator'] = sitk.sitkBSpline


extractor = featureextractor.RadiomicsFeatureExtractor(**settings)

featureVector = extractor.execute(imageName, maskName)

f = open("processed/"+ series_to_Test+"features.csv", 'w',newline='')
writer = csv.writer(f)

for featureName in featureVector.keys():
    writer.writerow([featureName, featureVector[featureName]])

f.close()