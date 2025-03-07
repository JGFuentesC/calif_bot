from flask import jsonify
from google.cloud import firestore
import functions_framework
from glom import glom 
import unicodedata

db = firestore.Client()

def read_from_firestore(collection, document_id):
    doc_ref = db.collection(collection).document(document_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        return None

@functions_framework.http
def query_grades(request):
    try:
        payload = glom(request.get_json(),'sessionInfo.parameters')
        if payload is None:
            return jsonify({"error": "Payload is empty"}), 400
        
        required_params = ['nombre_completo', 
                        'numero_estudiante', 
                        'universidad',
                        'materia'
                        ]
        
        for param in required_params:
            if param not in payload:
                return jsonify({"error": f"Missing parameter: {param}"}), 400
        
        payload['nombre_completo'] = glom(payload,'nombre_completo.original')
        if isinstance(payload['nombre_completo'], str):
            full_name = payload['nombre_completo']
            full_name = ''.join(c for c in unicodedata.normalize('NFKD', full_name) if not unicodedata.combining(c)).upper()
        else:
            return jsonify({"error": "Full name must be a string"}), 400
        
        university = glom(payload, 'universidad')
        if isinstance(university, str):
            university = university.upper()
        else:
            return jsonify({"error": "University must be a string"}), 400
        
        student_id = glom(payload, 'numero_estudiante')
        if isinstance(student_id, str):
            student_id = student_id
        else:
            return jsonify({"error": "Student ID must be a string"}), 400
        
        subject = glom(payload, 'materia')
        if isinstance(subject, str):
            subject = subject.lower()
        else:
            return jsonify({"error": "Subject must be a string"}), 400
        
        student_data = read_from_firestore(university, student_id)
        print(str(student_data))
        if student_data is None:
            response = {
                "fulfillment_response": {
                    "messages": [{"text":{"text": ["No pude encontrar tus datos, ¿Seguro que están correctos?"]}}]
                }
            }
            return jsonify(response), 200
        else:
            if glom(student_data, f"grades.{subject}.grade", default=None) and (full_name == glom(student_data, "student_name", default=None)):
                grade = glom(student_data, f"grades.{subject}.grade")
                response = {
                    "fulfillment_response": {
                        "messages": [{"text":{"text": [f"Estimado {full_name} de la {university}. Tu calificación de la materia {subject} es {grade}"]}}]
                    }
                }
                print(response)
                return jsonify(response), 200
            else:
                response = {
                    "fulfillment_response": {
                        "messages": [{"text":{"text": ["No pude encontrar tus datos, ¿Seguro que están correctos?"]}}]
                    }
                }
                return jsonify(response), 200
    except Exception as e:
        response = {
                "fulfillment_response": {
                    "messages": [{"text":{"text": ["Algo explotó, busca al profe, dile que pasó esto: "+str(e)]}}]
                }
            }
        print(e)
        return jsonify({"error": str(e)}), 200