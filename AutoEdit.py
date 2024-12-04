# Python 3 - 23.2.1
# pip install opencv-python
# pip install Pillow
# pip install prompt_toolkit

import os
import json
import copy
import cv2
import math

from prompt_toolkit import prompt
from datetime import datetime
from PIL import Image
from fractions import Fraction
from PIL.ExifTags import TAGS

# Por alguna razon Camtasia en la linea de tiempo de edicio divide cada segundo en 30 partes, 
# cada unidad equivale 23520000, que no se a que se refiera por que ya no es divisible,
# todo se calcula apartir de esa "unidad"
TREINTAVO_SEGUNDO_EQUIVALENTE  = 23520000

# Mapeo de dimensiones a los valores de escala para clip principal
scale_map = {
    (1920, 1080): 0.316,
    (1080, 1920): 0.5625,
    (2448, 3264): 0.24836,
    (3264, 2448): 0.18627,
    (1944, 2592): 0.31276,
    (2592, 1944): 0.23457,
    (1280, 720): 0.475,
    (720, 1280): 0.84375,
}

def main():
    
    # Capturar Nombre de proyecto
    nombreProyecto = input_con_sugerencia("Nombre de proyecto: ", "00000")
    
    #Extraer los archivos locales solo jpg y mp4
    archivos = os.listdir('./')
    filtrados = [f for f in archivos if f.endswith(('.mp4', '.jpg'))]

    # Ordenar por la parte del nombre deseada
    filtrados = sorted(
        filtrados,
        key=lambda f: f.split('_', 1)[1].split('.', 1)[0]  # Extraer la parte después del primer '_' y antes del '.'
    )

    #Extraer json ejemplo del guardado de camtasia
    with open('SampleProject.json', 'r') as sampleProjectFile:
        sampleProjectJson = json.load(sampleProjectFile)

    # Extraer ejemplo principal
    mainProject = sampleProjectJson['mainTemplate']

    # Iniciar array con archivos a importar al proyecto y id para cada uno de ellos
    mainProject['sourceBin']= []
    idCont = 0

    # Iteracion por cada archivo multimedia encontrado localmente
    for sourceI in filtrados:

        # Reiniciar fuente de multimedio y arreglo de dimensiones de multimedia
        sourceBin = 0
        rect = [0,0,0,0]

        # Si archivo presente es video
        if sourceI.endswith('.mp4'):
            # Extraer ejemplo de inclusion de archivo mp4 al proyecto
            sourceBin = sampleProjectJson['sourceBinMp4']

            # Establecer dimensiones para video
            video = cv2.VideoCapture(sourceI)
            rect[2] = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            rect[3] = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Calcular range (asumiendo editRate = 90000)
            edit_rate = 90000
            range_start = 0
            range_end = int(edit_rate * get_duration_in_seconds(sourceI))
            sourceBin['sourceTracks'][0]['range'] = [range_start, range_end]

            # Convertir FPS a una fracción para sample rate
            fps_fraction = Fraction(video.get(cv2.CAP_PROP_FPS)).limit_denominator()
            sourceBin['sourceTracks'][0]['sampleRate'] = f"{fps_fraction}"
        
        # Si archivo presente es imagen
        if sourceI.endswith('.jpg'):
            # Extraer ejemplo de inclusion de archivo jpg al proyecto
            sourceBin = sampleProjectJson['sourceBinJpg']

            # Establecer dimensiones para imagenes
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
            
        #Establecer otras propiedades comunes
        idCont= idCont +1
        sourceBin['id'] = idCont
        sourceBin['src'] = sourceI
        sourceBin['rect'] = rect
        sourceBin['sourceTracks'][0]['trackRect'] = rect
        sourceBin['sourceTracks'][0]['metaData'] = sourceI + ";"
        
        #Aniadir multimedia configurada a la fuentes del proyecto
        mainProject['sourceBin'].append(copy.deepcopy(sourceBin))

    #Iniciar el tiempo de Camtasia y el id para cada uno de los elementos de esa linea de tiempo
    currentCamtasiaTime = 0
    idCmsl = 0

    # Iteracion por cada archivo multimedia importado pues se reproducira en orden y solo una vez
    for sourceBin in mainProject['sourceBin']:
        print(sourceBin['src'])
        # Reiniciar elemento a añadir el linea de tiempo
        csml = 0

        # Si archivo multimedia presente es video
        if sourceBin['src'].endswith('.mp4'):
            # Extraer ejemplo de manipulaccion en linea de tiempo de video
            csml = sampleProjectJson['trackMediaVid']
            
            # Extraer duracion en segundos y en valor de tiempo de Camtasia
            durationSeconds = get_duration_in_seconds(sourceBin['src'])
            originalCamtasiaDuration = get_camtasia_duration(sourceBin['src'])
            
            # Aniadir velocidad dependiendo de su duracion 
            # Menor a 10 minutos sera una fraccion de segundo especifica
            # MAyor a 10 minutos la velocidad se aumentara x 250
            if(durationSeconds < 10):
                speedCamtasiaDuration = TREINTAVO_SEGUNDO_EQUIVALENTE * 10
            elif(durationSeconds < 120):
                speedCamtasiaDuration = TREINTAVO_SEGUNDO_EQUIVALENTE * 60
            elif(durationSeconds < 600):
                speedCamtasiaDuration = TREINTAVO_SEGUNDO_EQUIVALENTE * 250
            else:
                speedCamtasiaDuration = originalCamtasiaDuration/250
        
        # Si archivo multimedia presente es imagenx
        if sourceBin['src'].endswith('.jpg'):
            # Extraer ejemplo de manipulaccion en linea de tiempo de imagen
            csml = sampleProjectJson['trackMediaImg']

            # Toda imagen durara solo 2/3 de fraccion de segundo
            originalCamtasiaDuration = speedCamtasiaDuration = TREINTAVO_SEGUNDO_EQUIVALENTE * 20

        # Obtener las dimensiones actuales
        dimensions = (sourceBin['rect'][2], sourceBin['rect'][3])

        # Asignar el valor de escala correspondiente si existe en el mapa
        # Tamanio de imagen o video en clip principal dependiendo sus dimensiones
        if dimensions in scale_map:
            scale_value = scale_map[dimensions]
            csml['parameters']['scale0']['defaultValue'] = scale_value
            csml['parameters']['scale1']['defaultValue'] = scale_value

        # Asignar valores calculados y comunes a elemento en linea de tiempo
        idCmsl=idCmsl+1
        csml['id'] = idCmsl
        csml['src'] = sourceBin['id']
        csml['attributes']['ident'] = sourceBin['src'].split('.')[0]
        csml['start'] = currentCamtasiaTime
        csml['duration'] = speedCamtasiaDuration
        csml['mediaDuration'] = originalCamtasiaDuration
        currentCamtasiaTime = currentCamtasiaTime + speedCamtasiaDuration
        
        # Agregar finalmente el elemento modificado a la linea de tiempo
        mainProject['timeline']['sceneTrack']['scenes'][0]['csml']['tracks'][0]['medias'].append(copy.deepcopy(csml))

    with open(nombreProyecto + '.tscproj', 'w') as archivo:
        archivo.write(json.dumps(mainProject))
    print("Proyecto " + nombreProyecto + '.tscproj ' + "creado exitosamente!")


def input_con_sugerencia(prompt_text, sugerencia):
    return prompt(prompt_text, default=sugerencia)

def get_duration_in_seconds(video_path):

    video = cv2.VideoCapture(video_path)
    # Total de frames y FPS
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video.get(cv2.CAP_PROP_FPS)

    # Duración aproximada en segundos
    return total_frames / fps if fps > 0 else 0

def get_camtasia_duration(video_path):

    #Me la vole, pfff pura ingenieria reversa alv
    equivalente30avos = math.floor(get_duration_in_seconds(video_path) * 30)

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

#Para mi tok, que el codigo principal va hasta arriba
main()
