"""
CSV Parser for student data.
Reads M1/M2 FI/FA student lists from CSV files.
"""
import csv
from typing import List, Dict, Optional, Tuple


def read_student_csv(file_path: str) -> Tuple[List[str], List[List[str]]]:
    """
    Read a student CSV file and return headers and data.
    
    Args:
        file_path: Path to CSV file
    
    Returns:
        Tuple of (headers, rows)
    """
    data = []
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader)  # First row is headers
        for row in reader:
            if row and row[0].strip():  # Skip empty rows
                data.append(row)
    return headers, data


def find_student_by_id(student_id: str, grade_level: str = 'M1') -> Optional[Dict[str, str]]:
    """
    Find a student by their student ID.
    Searches in both FI and FA lists for the given grade level.
    
    Args:
        student_id: Student number (e.g., "22107880")
        grade_level: Grade level ('M1' or 'M2')
    
    Returns:
        Dict with student info or None if not found.
        Contains: student_id, first_name, last_name, email, formation_type, grade_level
    """
    grade_lower = grade_level.lower()
    
    # Define file paths for each grade/formation combination
    files = {
        ('M1', 'FI'): 'assets/m1_fi.csv',
        ('M1', 'FA'): 'assets/m1_fa.csv',
        ('M2', 'FI'): 'assets/m2_fi.csv',
        ('M2', 'FA'): 'assets/m2_fa.csv',
    }
    
    # Search in both FI and FA for the given grade level
    for formation_type in ['FI', 'FA']:
        key = (grade_level.upper(), formation_type)
        if key not in files:
            continue
        
        try:
            headers, rows = read_student_csv(files[key])
            
            # Find the column indices
            id_idx = headers.index('N° étudiant')
            nom_idx = headers.index('Nom')
            prenom_idx = headers.index('Prénom')
            email_idx = headers.index('Email')
            
            # Search for the student
            for row in rows:
                if len(row) > id_idx and row[id_idx].strip() == student_id.strip():
                    return {
                        'student_id': row[id_idx],
                        'first_name': row[prenom_idx],
                        'last_name': row[nom_idx],
                        'email': f"{row[email_idx]}@etu.u-paris.fr",
                        'formation_type': formation_type,
                        'grade_level': grade_level.upper()
                    }
        except FileNotFoundError:
            # File doesn't exist, continue to next
            continue
        except (ValueError, IndexError):
            # CSV structure issue, continue to next
            continue
    
    return None


def get_all_students(grade_level: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Get all students, optionally filtered by grade level.
    
    Args:
        grade_level: Optional filter by 'M1' or 'M2'
    
    Returns:
        List of student dicts
    """
    students = []
    
    files = {
        ('M1', 'FI'): 'assets/m1_fi.csv',
        ('M1', 'FA'): 'assets/m1_fa.csv',
        ('M2', 'FI'): 'assets/m2_fi.csv',
        ('M2', 'FA'): 'assets/m2_fa.csv',
    }
    
    for (grade, formation), file_path in files.items():
        if grade_level and grade != grade_level.upper():
            continue
        
        try:
            headers, rows = read_student_csv(file_path)
            
            id_idx = headers.index('N° étudiant')
            nom_idx = headers.index('Nom')
            prenom_idx = headers.index('Prénom')
            email_idx = headers.index('Email')
            
            for row in rows:
                if len(row) > id_idx:
                    students.append({
                        'student_id': row[id_idx],
                        'first_name': row[prenom_idx],
                        'last_name': row[nom_idx],
                        'email': f"{row[email_idx]}@etu.u-paris.fr",
                        'formation_type': formation,
                        'grade_level': grade
                    })
        except (FileNotFoundError, ValueError, IndexError):
            continue
    
    return students

