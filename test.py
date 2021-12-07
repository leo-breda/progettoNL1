from dirToNRRD import directory_processing
import logging
import SimpleITK as sitk

import radiomics
from radiomics import featureextractor



series_to_Test = "002/"



target_dir = "processed/"+ series_to_Test
imageName = target_dir+"image.nrrd"
maskName = target_dir+"seg_1.nrrd"
directory_processing("examples/"+series_to_Test, target_dir)


logger = radiomics.logger
logger.setLevel(logging.DEBUG)

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

for featureName in featureVector.keys():
  print("Computed %s: %s" % (featureName, featureVector[featureName]))

