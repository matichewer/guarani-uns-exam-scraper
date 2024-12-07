-- Eliminar tablas existentes si es que existen (en orden inverso a la creación para evitar errores de dependencia)
DROP TABLE IF EXISTS mesas CASCADE;
DROP TABLE IF EXISTS turnos CASCADE;
DROP TABLE IF EXISTS materias CASCADE;
DROP TABLE IF EXISTS departamentos CASCADE;

-- Crear tabla de departamentos con mejoras
CREATE TABLE departamentos (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    codigo VARCHAR(10) UNIQUE NOT NULL,
    nombre_completo VARCHAR(255) NOT NULL
);

-- Crear tabla de materias con mejoras
CREATE TABLE materias (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    codigo_materia VARCHAR(20) UNIQUE NOT NULL,
    nombre_completo VARCHAR(255) NOT NULL,
    codigo_departamento VARCHAR(10) NOT NULL,
    FOREIGN KEY (codigo_departamento) REFERENCES departamentos(codigo) ON DELETE RESTRICT
);

-- Crear tabla de turnos con mejoras
CREATE TABLE turnos (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    fecha DATE NOT NULL UNIQUE
);

-- Crear tabla de mesas con mejoras
CREATE TABLE mesas (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    id_materia INTEGER NOT NULL,
    id_turno INTEGER NOT NULL,
    fecha DATE NOT NULL,
    codigo VARCHAR(50) NOT NULL,
    profesor VARCHAR(255),
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    tipo VARCHAR(50),
    inscripcion_inicio TIMESTAMP WITH TIME ZONE,
    inscripcion_fin TIMESTAMP WITH TIME ZONE,
    cant_inscriptos INTEGER DEFAULT 0,
    carrera VARCHAR(100),
    plan VARCHAR(50),
    grupo_carrera VARCHAR(50),
    observaciones TEXT,
    capacidad VARCHAR(50),
    letra_desde VARCHAR(10),
    letra_hasta VARCHAR(10),
    sede VARCHAR(100),
    FOREIGN KEY (id_materia) REFERENCES materias(id) ON DELETE RESTRICT,
    FOREIGN KEY (id_turno) REFERENCES turnos(id) ON DELETE RESTRICT
);

-- Índices para mejorar el rendimiento
CREATE INDEX idx_materias_departamento ON materias(codigo_departamento);
CREATE INDEX idx_mesas_materia ON mesas(id_materia);
CREATE INDEX idx_mesas_turno ON mesas(id_turno);


-- VISTAS
CREATE VIEW materias_simple AS
SELECT
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS created_at,
    TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI:SS') AS updated_at,
    TO_CHAR(modified_at, 'YYYY-MM-DD HH24:MI:SS') AS modified_at,
    codigo_materia,
    nombre_completo,
    codigo_departamento
FROM materias
ORDER BY id;

CREATE VIEW dptos_simple AS
SELECT
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS created_at,
    TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI:SS') AS updated_at,
    TO_CHAR(modified_at, 'YYYY-MM-DD HH24:MI:SS') AS modified_at,
    codigo,
    nombre_completo
FROM departamentos
ORDER BY id;

CREATE VIEW turnos_simple AS
SELECT
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS created_at,
    TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI:SS') AS updated_at,
    fecha
FROM turnos
ORDER BY id;