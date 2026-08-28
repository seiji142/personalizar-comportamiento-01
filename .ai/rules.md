# Reglas GLOBALES y OBLIGATORIAS del proyecto

## 1. Codigo y Estilo
- Usar espacios para indentacion (2 espacios por nivel)
- Maximo 120 caracteres por linea
- Comentarios explicativos para logica compleja
- Nombres descriptivos en ingles (variables, funciones, clases)

## 2. Control de Versiones
- Commits frecuentes y descriptivos
- Mensajes de commit en imperativo (ej: 'Add feature X', no 'Added feature X')
- Revisar codigo antes de merge (pull request)
- Nunca commitear directamente a main/master

## 3. Seguridad
- Nunca commitear credenciales, API keys o secrets
- Usar variables de entorno para configuracion sensible
- Validar todas las entradas de usuario
- Mantener dependencias actualizadas

## 4. Calidad
- Todas las funciones deben tener tests unitarios
- Cobertura minima de tests: 80%
- Ejecutar linter antes de cada commit
- No romper builds existentes

## 5. Documentacion
- Documentar APIs publicas
- Mantener README actualizado
- Comentar decisiones arquitectonicas importantes
- Documentar setup y despliegue
