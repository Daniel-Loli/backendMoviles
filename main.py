from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

import logging
from fastapi import FastAPI, HTTPException

# Configuración de la base de datos
DATABASE_CONFIG = {
    "dbname": "sigcon",
    "user": "modulo4",
    "password": "modulo4",
    "host": "137.184.120.127",
    "port": 5432
}

app = FastAPI()

# Agregar CORS middleware
origins = [
    "http://localhost",  
    "http://127.0.0.1",  
    "http://10.0.2.2", 
    "http://*",
    "*",  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)



class CaracteristicasPredio(BaseModel):
    area_predio: int
    num_casas: int
    num_areas_comunes: int
    area_comunes: int
    num_administradores: int
    num_vigilantes: int
    num_personal_limpieza: int
    num_jardineros: int

class Solicitud(BaseModel):
    fecha_solicitud: str
    servicio: str
    dni: str
    predio: str
    caracteristicas: CaracteristicasPredio

class Solicitante(BaseModel):
    apellido_paterno: str
    apellido_materno: str
    nombres: str
    correo: str
    telefono:int
    predios: List[str]



def get_db_connection():
    """Establece una conexión segura a la base de datos."""
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        return conn
    except psycopg2.OperationalError as e:
        raise HTTPException(status_code=500, detail="Error al conectar con la base de datos")

@app.get("/test-connection")
async def test_connection():
    """Endpoint para verificar si la conexión a la base de datos es exitosa."""
    try:
        conn = get_db_connection()
        conn.close()
        return {"message": "Conexión a la base de datos exitosa"}
    except Exception as e:
        print(f"Error en test_connection: {str(e)}")
        raise HTTPException(status_code=500, detail="No se pudo conectar a la base de datos")
@app.get("/servicios", response_model=List[dict])
async def obtener_servicios():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        
        cursor.execute("""
            SELECT id_servicio, descripcion, precio
            FROM servicio
        """)
        servicios = cursor.fetchall()

        conn.close()

        
        if not servicios:
            raise HTTPException(status_code=404, detail="No se encontraron servicios")

        
        return [{"id_servicio": servicio["id_servicio"], "descripcion": servicio["descripcion"], "precio": servicio["precio"]} for servicio in servicios]
    except Exception as e:
        print(f"Error en obtener_servicios: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/solicitante/{dni}", response_model=Solicitante)
async def obtener_solicitante(dni: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        
        cursor.execute("""
            SELECT p.apellido_paterno, p.apellido_materno, p.nombres, p.id_persona, s.telefono, s.correo
            FROM persona p
            JOIN solicitante s ON p.id_persona = s.id_persona
            WHERE p.ndocumento = %s
        """, (dni,))
        solicitante = cursor.fetchone()

        if not solicitante:
            raise HTTPException(status_code=404, detail="DNI no encontrado")

        
        cursor.execute("""
            SELECT descripcion FROM predio WHERE id_persona = %s
        """, (solicitante["id_persona"],))
        predios = cursor.fetchall()

        conn.close()

       
        predios_list = [predio["descripcion"] for predio in predios]

        
        return Solicitante(
            apellido_paterno=solicitante["apellido_paterno"],
            apellido_materno=solicitante["apellido_materno"],
            nombres=solicitante["nombres"],
            telefono=solicitante["telefono"],
            correo=solicitante["correo"],
            predios=predios_list
        )
    except Exception as e:
        print(f"Error en obtener_solicitante: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
@app.post("/registrar")
async def registrar_solicitud(solicitud: Solicitud):
    try:
        
        if not solicitud.fecha_solicitud:
            solicitud.fecha_solicitud = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = get_db_connection()
        cursor = conn.cursor()

       
        cursor.execute("SELECT id_predio FROM predio WHERE descripcion = %s", (solicitud.predio,))
        predio_result = cursor.fetchone()
        if not predio_result:
            raise HTTPException(status_code=404, detail="Predio no encontrado")
        id_predio = predio_result[0]

        
        cursor.execute("SELECT id_persona, nombres, apellido_paterno, apellido_materno FROM persona WHERE ndocumento = %s", (solicitud.dni,))
        persona_result = cursor.fetchone()
        if not persona_result:
            raise HTTPException(status_code=404, detail="Persona no encontrada")
        id_persona = persona_result[0]
        nombre_completo = f"{persona_result[1]} {persona_result[2]} {persona_result[3]}"  

        cursor.execute("SELECT id_solicitante FROM solicitante WHERE id_persona = %s", (id_persona,))
        solicitante_result = cursor.fetchone()
        if not solicitante_result:
            raise HTTPException(status_code=404, detail="Solicitante no encontrado")
        id_solicitante = solicitante_result[0]

        
        cursor.execute("SELECT id_servicio FROM servicio WHERE descripcion = %s", (solicitud.servicio,))
        servicio_result = cursor.fetchone()
        if not servicio_result:
            raise HTTPException(status_code=404, detail="Servicio no encontrado")
        id_servicio = servicio_result[0]

        
        cursor.execute("""
            INSERT INTO solicitud 
            (fecha_solicitud, id_servicio, id_solicitante, id_predio, cant_acomunes, num_casas, area_acomunes, area_predio, cant_vigilantes, cant_plimpieza, cant_administracion, cant_jardineria, nombre_solicitante)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            solicitud.fecha_solicitud,
            id_servicio,
            id_solicitante,
            id_predio,
            solicitud.caracteristicas.num_areas_comunes,
            solicitud.caracteristicas.num_casas,
            solicitud.caracteristicas.area_comunes,
            solicitud.caracteristicas.area_predio,
            solicitud.caracteristicas.num_vigilantes,
            solicitud.caracteristicas.num_personal_limpieza,
            solicitud.caracteristicas.num_administradores,
            solicitud.caracteristicas.num_jardineros,
            nombre_completo  
        ))

        conn.commit()
        conn.close()
        return {"message": "Solicitud registrada exitosamente"}
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="Error de integridad en los datos enviados")
    except Exception as e:
        print(f"Error en registrar_solicitud: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
