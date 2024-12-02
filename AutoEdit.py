# Python 3 - 23.2.1
# pip install opencv-python
# pip install Pillow

import os
import json
import copy
import cv2
import math

from datetime import datetime
from PIL import Image
from fractions import Fraction
from PIL.ExifTags import TAGS

TREINTAVO_SEGUNDO_EQUIVALENTE  = 23520000

def get_camtasia_duration(video_path):

    video = cv2.VideoCapture(video_path)
    # Total de frames y FPS
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video.get(cv2.CAP_PROP_FPS)

    # Duración aproximada en segundos
    duracion_segundos = total_frames / fps if fps > 0 else 0

    #print(f'Total de frames: {total_frames}')
    #print(f'FPS: {fps}')
    #print(f'Duración en segundos: {duracion_segundos}')
    
    #Me la vole, pfff pura ingenieria reversa alv
    equivalente30avos = math.floor(duracion_segundos * 30)
    
   # print(f'Equivalencia directa: {equivalente30avos * TREINTAVO_SEGUNDO_EQUIVALENTE}')

    return equivalente30avos * TREINTAVO_SEGUNDO_EQUIVALENTE


def get_orientation(image_path):
    try:
        # Abrir la imagen
        image = Image.open(image_path)

        # Obtener los datos EXIF
        exif_data = image._getexif()
        if not exif_data:
            print(f"No se encontraron datos EXIF en {image_path}")
            return None

        # Buscar la orientación (key = 274 es la etiqueta EXIF para orientación)
        orientation_tag = 274  # El tag de orientación en EXIF
        if orientation_tag in exif_data:
            orientation = exif_data[orientation_tag]
            return orientation
        else:
            print(f"No se encontró orientación en {image_path}")
            return None

    except Exception as e:
        print(f"Error al leer EXIF de {image_path}: {e}")
        return None


archivos = os.listdir('./')
filtrados = sorted([f for f in archivos if f.endswith(('.mp4', '.jpg'))])

with open('SampleProject.json', 'r') as sampleProjectFile:
    sampleProjectJson = json.load(sampleProjectFile)

mainProject = sampleProjectJson['mainTemplate']

mainProject['sourceBin']= []
idCont = 0
for sourceI in filtrados:
    #print(sourceI)
    idCont= idCont +1

    sourceBin = 0
    rect = [0,0,0,0]
    if sourceI.endswith('.mp4'):
        sourceBin = sampleProjectJson['sourceBinMp4']
        video = cv2.VideoCapture(sourceI)
        rect[2] = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        rect[3] = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Obtener propiedades
        fps = video.get(cv2.CAP_PROP_FPS)
        frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)

        # Calcular duración en segundos
        duration_seconds = frame_count / fps if fps > 0 else 0

        # Calcular range (asumiendo editRate = 90000)
        edit_rate = 90000
        range_start = 0
        range_end = int(duration_seconds * edit_rate)
        sourceBin['sourceTracks'][0]['range'] = [range_start, range_end]

        # Convertir FPS a una fracción
        fps_fraction = Fraction(fps).limit_denominator()
        sourceBin['sourceTracks'][0]['sampleRate'] = f"{fps_fraction}"
            
    if sourceI.endswith('.jpg'):
        sourceBin = sampleProjectJson['sourceBinJpg']
        imagen = Image.open(sourceI)
        ancho, alto = imagen.size
        # rect se mantiene para Orientation 1, 3
        # rect se invierte para Orientation 6, 8
        if(get_orientation(sourceI) <= 3):
            rect[2] = ancho
            rect[3] = alto
        else:
            rect[2] = alto
            rect[3] = ancho
        
        
    sourceBin['id'] = idCont
    sourceBin['src'] = sourceI
    sourceBin['rect'] = rect
    sourceBin['sourceTracks'][0]['trackRect'] = rect
    sourceBin['sourceTracks'][0]['metaData'] = sourceI + ";"
       
    mainProject['sourceBin'].append(copy.deepcopy(sourceBin))

currentCamtasiaTime = 0
idCmsl = 0
for sourceI in mainProject['sourceBin']:
    print(sourceI['src'])
    csml = 0
    if sourceI['src'].endswith('.mp4'):
        csml = sampleProjectJson['trackMediaVid']
        camtasiaDuration = get_camtasia_duration(sourceI['src'])

    if sourceI['src'].endswith('.jpg'):
        csml = sampleProjectJson['trackMediaImg']
        camtasiaDuration = TREINTAVO_SEGUNDO_EQUIVALENTE * 20

    idCmsl=idCmsl+1
    csml['id'] = idCmsl
    csml['src'] = sourceI['id']
    csml['attributes']['ident'] = sourceI['src'].split('.')[0]
    csml['start'] = currentCamtasiaTime
    csml['duration'] = camtasiaDuration
    csml['mediaDuration'] = camtasiaDuration
    currentCamtasiaTime = currentCamtasiaTime + camtasiaDuration

    print(csml)
    
    mainProject['timeline']['sceneTrack']['scenes'][0]['csml']['tracks'][0]['medias'].append(copy.deepcopy(csml))

#print(mainProject['sourceBin'])



fecha_hora = datetime.now().strftime('%y%m%d-%H%M')

with open(fecha_hora + '.tscproj', 'w') as archivo:
    archivo.write(json.dumps(mainProject))
