from pathlib import Path
import os
import pydicom as pdcm
import numpy as np
import nrrd
import xml.etree.ElementTree as ET
from skimage.segmentation import flood_fill

# import humanize 
# from datetime import datetime
import logging


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# type hinting utility
Dicom_Dataset = pdcm.dataset.FileDataset


def create_VolImg(list2D: list) -> np.ndarray:
    list3D = list2D[0]

    for layer in list2D[1:]:
        list3D = np.dstack((list3D, layer))

    list3D = np.swapaxes(list3D, 0, 1)

    return list3D


def dicom_options(image: Dicom_Dataset) -> dict:
    # options for pynrrd
    options = dict()
    options['type'] = 'int'
    options['dimension'] = 3
    options['space'] = 'left-posterior-superior'
    options['space directions'] = [[image.PixelSpacing[0], 0, 0],
                                   [0, image.PixelSpacing[1], 0],
                                   [0, 0, image.SliceThickness]]
    options['kinds'] = ['domain', 'domain', 'domain']
    options['space origin'] = image.ImagePositionPatient

    return options


def isValid(checked, to_Check) -> bool:
    """
    some checks to see if some parameters are the same in all files
    """
    
    if not (checked.PatientID == to_Check.PatientID):
        return False
    if not (checked.SeriesNumber == to_Check.SeriesNumber):
        return False
    if not (checked.BodyPartExamined == to_Check.BodyPartExamined):
        return False
    if not (checked.ImageOrientationPatient == to_Check.ImageOrientationPatient):
        return False

    return True


def parseXML(XMLfilename: str) -> list:

    listXML = []
    listNodule = []
    listCOO = []
    zCoord = 0
    tree = ET.parse(XMLfilename)
    root = tree.getroot()
    segID = 0

    for item in root.findall('.//{http://www.nih.gov}readingSession'):
        segID = segID + 1
        for child in item:
            if child.tag == '{http://www.nih.gov}unblindedReadNodule':
                for subchild in child:
                    if subchild.tag == '{http://www.nih.gov}roi':
                        for roi in subchild:
                            if roi.tag == '{http://www.nih.gov}imageZposition':
                                zCoord = float(roi.text)
                            if roi.tag == '{http://www.nih.gov}edgeMap':
                                for coo in list(zip(roi, roi[1:]))[::2]:
                                    listCOO.append(
                                        (int(coo[0].text), int(coo[1].text)))
                        listNodule.append([zCoord, listCOO])
                        listCOO = []
        listXML.append([str(segID), listNodule])
        listNodule = []

    return listXML


def scroll_dir(path_to_dir: str) -> (list, dict, list):
    """
    Returns:
    -list with data extracted from .dcm files in given directory
        and a dictionary for the creation of the .nrrd file.
    -list with data extracted from .xml segmentation file in given directory
        and a dictionary for the creation of the .nrrd file.
    """
    dirListDCM = []
    dirListXML = []
    fileList = os.listdir(path_to_dir)

    run_once = True

    for filename in fileList:
        if filename.endswith(".dcm"):

            currentImage = pdcm.dcmread(path_to_dir+filename)

            if run_once:
                firstImage = currentImage
                optionsDCM = dicom_options(firstImage)
                run_once = False

            if isValid(firstImage, currentImage):
                dirListDCM.append(currentImage.pixel_array)
            else:
                logger.warning("something's wrong with " + filename)

        elif (filename.endswith(".xml")):
            dirListXML = parseXML(path_to_dir+filename)
        else:
            logger.info(filename + " is not .dcm or .xml")
            
    return dirListDCM, optionsDCM, dirListXML


def fillRegion(layer: np.ndarray) -> np.ndarray:

    filled = flood_fill(layer, (1, 1), 2, connectivity=1)
    filled[filled == 0] = 1
    filled[filled == 2] = 0

    return filled


def create_Mask(listXML: list, options: dict, shape: tuple) -> (np.ndarray, dict):
    optionsMask = dict()
    maskList = []
    layer = np.zeros((shape[0], shape[1]), dtype=np.short)
    
    for readingSession in listXML:
        mask = np.zeros(shape, dtype=np.short)
        for Zlevel in readingSession[1]:
            for coo in Zlevel[1]:
                layer[coo] = 1
            layer = fillRegion(layer)
            level = (Zlevel[0] - options["space origin"]._list[2]
                     )/options["space directions"][2][2]
            mask[:, :, int(-level)] = layer
            layer = np.zeros((shape[0], shape[1]), dtype=np.short)
            
        maskList.append(mask)

    optionsMask = options
    optionsMask['type'] = 'short'
    return maskList, optionsMask


def create_nrrd(data3D: np.ndarray, nrrdFileName: str, options) -> None:
    
    nrrd.write(nrrdFileName, data3D, options)
    
    return


def directory_processing(path_to_dir: str, target_dir: str) -> None:
    
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    
    listFromDCM, optionsDCM, listFromXML = scroll_dir(path_to_dir)
    VolImg = create_VolImg(listFromDCM)
    create_nrrd(VolImg, target_dir+"image.nrrd", optionsDCM)
    
    MaskList, optionsMask = create_Mask(listFromXML, optionsDCM, VolImg.shape)
    i = 0
    for mask in MaskList:
        i = i + 1
        create_nrrd(mask, target_dir+"seg_"+str(i)+".nrrd", optionsMask)
        
    return


if __name__ == "__main__":
    
    #startTime = datetime.now()
    
    series_to_Test = "001/"
    target_dir = "processed/" + series_to_Test
    directory_processing(
        "examples/"+series_to_Test, target_dir)  
    
    # endTime = datetime.now()
    #logger.info(f"Excecution time is: {humanize.precisedelta(endTime-startTime, suppress=['days'], format='%0.4f')}")
