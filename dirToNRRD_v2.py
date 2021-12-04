import logging
import os
import pydicom as pdcm
import numpy as np
import nrrd
import xml.etree.ElementTree as ET
import humanize #utilità varie, eliminabile
from datetime import datetime #controllo su tempo di esecuzione


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

#variabile per comodità del type hinting
Dicom_Dataset = pdcm.dataset.FileDataset


def create_VolImg(list2D: list) -> np.ndarray:
    list3D = list2D[0]#.astype(np.float32) #serve int o float ??
    
    for layer in list2D[1:]:
        list3D = np.dstack((list3D, layer))
   
    list3D = np.swapaxes(list3D, 0, 1)
    list3D = list3D[:, :, ::-1]
    
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
    
def isValid(checked, to_Check)-> bool:
    """
    some checks to see if some parameters are the same in all files
    """
    # capire se effetivamente sono questi i controlli corretti da fare
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
    listCOO = []
    zCoord = 0
    tree = ET.parse(XMLfilename)
    
    root = tree.getroot()
    
    for item in root.findall('.//{http://www.nih.gov}unblindedReadNodule'):
        for child in item:
            if child.tag=='{http://www.nih.gov}roi':
                for roi in child:
                    if(roi.tag == '{http://www.nih.gov}imageZposition'):
                        zCoord = float(roi.text)
                    if roi.tag == '{http://www.nih.gov}edgeMap':
                        for coo in list(zip(roi,roi[1:]))[::2]:
                            listCOO.append((int(coo[0].text),int(coo[1].text)))
                listXML.append([zCoord, listCOO])
                listCOO = []
    
    return listXML


def scroll_dir(path_to_dir: str) -> (list,dict,list):
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

    run_once = True #trovare modo più efficiente per estrarre i dati del primo .dcm?
    
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
                logger.warning("something's wrong with "+ filename)
                
        elif (filename.endswith(".xml")):
            dirListXML = parseXML(path_to_dir+filename)
        else: 
            logger.info(filename + " is not .dcm or .xml")
    return dirListDCM, optionsDCM, dirListXML

def create_Mask(listXML: list, filename: str, options: dict, shape: tuple) -> (np.ndarray,dict):
    """
    Work in Progress
    
    """
    mask = []
    optionsMask = dict()
    base = np.zeros((shape[0],shape[1]),dtype=np.int16)
    layerList = []
    layer = base
    for nodule in listXML:
        for coo in nodule[1]:
            layer[coo] = 1
        layerList.append(layer)
        layer = base
    return mask, optionsMask

def create_nrrd(data3D: np.ndarray, nrrdFileName: str, options) -> None:
    nrrd.write(nrrdFileName, data3D, options)
    return

def directory_processing(path_to_dir: str, image_FileName: str, mask_FileName: str) -> None:
    listFromDCM, optionsDCM, listFromXML = scroll_dir(path_to_dir)
    VolImg = create_VolImg(listFromDCM)
    #VolMask, optionsMask = create_Mask(listFromXML, optionsDCM, VolImg.shape)
    create_nrrd(VolImg, image_FileName, optionsDCM)
    #create_nrrd(VolMask, mask_FileName, optionsMask)
    return 


if __name__ == "__main__":
    startTime = datetime.now()
    
    directory_processing("dir/", "miofile.nrrd", "miamask.nrrd")
    
    endTime = datetime.now()
    logger.info(f"Excecution time is: {humanize.precisedelta(endTime-startTime, suppress=['days'], format='%0.4f')}")
    